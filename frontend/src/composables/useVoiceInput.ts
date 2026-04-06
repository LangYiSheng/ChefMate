import { computed, onBeforeUnmount, ref } from 'vue'

import { checkVoiceWakeup, getApiOrigin } from '../lib/api'

type VoiceMode = 'idle' | 'starting' | 'recording' | 'stopping' | 'standby' | 'wakeup-checking'
type StopReason = 'manual_stop' | 'silence_timeout'

interface UseVoiceInputOptions {
  getToken: () => string | null
  onFinalText: (text: string) => Promise<void> | void
  silenceTimeoutMs?: number
  wakeupClipMs?: number
  chunkMs?: number
}

interface VoiceSocketEvent {
  event: 'ready' | 'status' | 'partial' | 'final' | 'error'
  data: Record<string, any>
}

const TARGET_SAMPLE_RATE = 16000
const PCM_WORKLET_PATH = '/audio/pcm-capture-worklet.js'
const RMS_THRESHOLD = 0.015
const WAKEUP_MIN_CAPTURE_MS = 350
const WAKEUP_SILENCE_FLUSH_MS = 450
const TRANSCRIPT_SEPARATOR_PATTERN = /[\s,，。.!！？?、；;：:“”"'‘’()（）\-]+/g

class VoiceInputCancelledError extends Error {
  constructor() {
    super('语音输入已取消。')
    this.name = 'VoiceInputCancelledError'
  }
}

function stopMediaTracks(stream: MediaStream | null) {
  stream?.getTracks().forEach((track) => track.stop())
}

class PcmResampler {
  private readonly ratio: number
  private tail = new Float32Array(0)

  constructor(
    private readonly sourceSampleRate: number,
    private readonly targetSampleRate: number,
  ) {
    this.ratio = sourceSampleRate / targetSampleRate
  }

  process(input: Float32Array) {
    if (!input.length) {
      return new Int16Array(0)
    }

    const merged = new Float32Array(this.tail.length + input.length)
    merged.set(this.tail)
    merged.set(input, this.tail.length)

    const outputLength = Math.floor(merged.length / this.ratio)
    if (outputLength <= 0) {
      this.tail = merged
      return new Int16Array(0)
    }

    const output = new Int16Array(outputLength)
    for (let index = 0; index < outputLength; index += 1) {
      const start = Math.floor(index * this.ratio)
      const end = Math.min(Math.floor((index + 1) * this.ratio), merged.length)
      let sum = 0
      let count = 0
      for (let offset = start; offset < end; offset += 1) {
        sum += merged[offset]
        count += 1
      }
      const sample = count > 0 ? sum / count : merged[start] || 0
      const clamped = Math.max(-1, Math.min(1, sample))
      output[index] = clamped < 0 ? clamped * 0x8000 : clamped * 0x7fff
    }

    const consumed = Math.floor(outputLength * this.ratio)
    this.tail = merged.slice(consumed)
    return output
  }
}

class Int16ChunkAccumulator {
  private chunks: Int16Array[] = []
  private sampleCount = 0

  constructor(private readonly samplesPerChunk: number) {}

  push(chunk: Int16Array, onChunk: (payload: Int16Array) => void) {
    if (!chunk.length) {
      return
    }

    this.chunks.push(chunk)
    this.sampleCount += chunk.length

    while (this.sampleCount >= this.samplesPerChunk) {
      const payload = new Int16Array(this.samplesPerChunk)
      let offset = 0

      while (offset < this.samplesPerChunk) {
        const head = this.chunks[0]
        const remaining = this.samplesPerChunk - offset
        if (head.length <= remaining) {
          payload.set(head, offset)
          offset += head.length
          this.chunks.shift()
        } else {
          payload.set(head.slice(0, remaining), offset)
          this.chunks[0] = head.slice(remaining)
          offset += remaining
        }
      }

      this.sampleCount -= this.samplesPerChunk
      onChunk(payload)
    }
  }

  flush() {
    if (!this.sampleCount) {
      return new Int16Array(0)
    }

    const payload = new Int16Array(this.sampleCount)
    let offset = 0
    this.chunks.forEach((chunk) => {
      payload.set(chunk, offset)
      offset += chunk.length
    })
    this.chunks = []
    this.sampleCount = 0
    return payload
  }
}

function concatChunks(chunks: Int16Array[]) {
  const totalLength = chunks.reduce((sum, chunk) => sum + chunk.length, 0)
  const merged = new Int16Array(totalLength)
  let offset = 0
  chunks.forEach((chunk) => {
    merged.set(chunk, offset)
    offset += chunk.length
  })
  return merged
}

function pcmToArrayBuffer(chunk: Int16Array) {
  return chunk.buffer.slice(chunk.byteOffset, chunk.byteOffset + chunk.byteLength)
}

function pcmToBase64(chunk: Int16Array) {
  const bytes = new Uint8Array(pcmToArrayBuffer(chunk))
  let binary = ''
  const partSize = 0x8000
  for (let index = 0; index < bytes.length; index += partSize) {
    const section = bytes.subarray(index, index + partSize)
    binary += String.fromCharCode(...section)
  }
  return window.btoa(binary)
}

function computeRms(chunk: Float32Array) {
  if (!chunk.length) {
    return 0
  }
  let sum = 0
  for (let index = 0; index < chunk.length; index += 1) {
    sum += chunk[index] * chunk[index]
  }
  return Math.sqrt(sum / chunk.length)
}

function buildVoiceSocketUrl() {
  const origin = getApiOrigin()
  const protocol = origin.startsWith('https://') ? 'wss://' : 'ws://'
  return `${origin.replace(/^https?:\/\//, protocol)}/api/voice/stream`
}

function needsBoundarySpace(left: string, right: string) {
  const lastChar = left[left.length - 1] || ''
  const firstChar = right[0] || ''
  return /[A-Za-z0-9]/.test(lastChar) && /[A-Za-z0-9]/.test(firstChar)
}

function isTranscriptSeparator(char: string) {
  return /[\s,，。.!！？?、；;：:“”"'‘’()（）\-]/.test(char)
}

function normalizeTranscriptForComparison(text: string) {
  return text.replace(TRANSCRIPT_SEPARATOR_PATTERN, '').toLowerCase()
}

function sliceRawByNormalizedPrefix(text: string, normalizedPrefixLength: number) {
  if (normalizedPrefixLength <= 0) {
    return text
  }

  let normalizedCount = 0
  for (let index = 0; index < text.length; index += 1) {
    if (isTranscriptSeparator(text[index] || '')) {
      continue
    }
    normalizedCount += 1
    if (normalizedCount >= normalizedPrefixLength) {
      return text.slice(index + 1)
    }
  }

  return ''
}

function findOverlapSuffixPrefix(left: string, right: string) {
  const maxLength = Math.min(left.length, right.length)
  for (let size = maxLength; size > 0; size -= 1) {
    if (left.slice(-size) === right.slice(0, size)) {
      return size
    }
  }
  return 0
}

function collapseRepeatedTranscript(text: string) {
  const trimmed = text.trim()
  if (trimmed.length < 4) {
    return trimmed
  }

  for (let unitLength = Math.floor(trimmed.length / 2); unitLength >= 2; unitLength -= 1) {
    const unit = trimmed.slice(0, unitLength).trim()
    if (!unit) {
      continue
    }

    let cursor = 0
    let matchedCount = 0

    while (cursor < trimmed.length) {
      while (cursor < trimmed.length && isTranscriptSeparator(trimmed[cursor] || '')) {
        cursor += 1
      }
      if (cursor >= trimmed.length) {
        break
      }
      if (!trimmed.startsWith(unit, cursor)) {
        matchedCount = 0
        break
      }
      cursor += unit.length
      matchedCount += 1
    }

    if (matchedCount >= 2 && cursor >= trimmed.length) {
      return unit
    }
  }

  return trimmed
}

function mergeTranscript(baseText: string, incomingText: string) {
  const base = collapseRepeatedTranscript(baseText)
  const incoming = collapseRepeatedTranscript(incomingText)
  const normalizedBase = normalizeTranscriptForComparison(base)
  const normalizedIncoming = normalizeTranscriptForComparison(incoming)

  if (!normalizedBase) {
    return incoming
  }
  if (!normalizedIncoming) {
    return base
  }
  if (normalizedIncoming === normalizedBase) {
    return incoming.length >= base.length ? incoming : base
  }
  if (incoming.startsWith(base) || normalizedIncoming.startsWith(normalizedBase)) {
    return incoming
  }
  if (base.startsWith(incoming) || base.includes(incoming) || normalizedBase.startsWith(normalizedIncoming) || normalizedBase.includes(normalizedIncoming)) {
    return base
  }
  if (incoming.includes(base) || normalizedIncoming.includes(normalizedBase)) {
    return incoming
  }

  const rawOverlap = findOverlapSuffixPrefix(base, incoming)
  if (rawOverlap > 0) {
    return collapseRepeatedTranscript(`${base}${incoming.slice(rawOverlap)}`.trim())
  }

  const normalizedOverlap = findOverlapSuffixPrefix(normalizedBase, normalizedIncoming)
  if (normalizedOverlap > 0) {
    const suffix = sliceRawByNormalizedPrefix(incoming, normalizedOverlap)
    return collapseRepeatedTranscript(`${base}${suffix}`.trim())
  }

  if (normalizedIncoming.length >= Math.max(4, Math.floor(normalizedBase.length * 0.75))) {
    return incoming.length >= base.length ? incoming : base
  }

  return collapseRepeatedTranscript(
    needsBoundarySpace(base, incoming) ? `${base} ${incoming}` : `${base}${incoming}`,
  )
}

export function useVoiceInput(options: UseVoiceInputOptions) {
  const mode = ref<VoiceMode>('idle')
  const statusText = ref('')
  const transcript = ref('')
  const errorText = ref('')

  const isSupported = computed(
    () =>
      typeof window !== 'undefined' &&
      typeof AudioContext !== 'undefined' &&
      typeof AudioWorkletNode !== 'undefined' &&
      Boolean(navigator.mediaDevices?.getUserMedia),
  )
  const isBusy = computed(() => mode.value !== 'idle')

  const silenceTimeoutMs = options.silenceTimeoutMs ?? 2000
  const wakeupClipMs = options.wakeupClipMs ?? 1500
  const chunkMs = options.chunkMs ?? 200

  let audioContext: AudioContext | null = null
  let mediaStream: MediaStream | null = null
  let sourceNode: MediaStreamAudioSourceNode | null = null
  let workletNode: AudioWorkletNode | null = null
  let sinkNode: GainNode | null = null
  let resampler: PcmResampler | null = null
  let dictationChunker: Int16ChunkAccumulator | null = null
  let recognitionSocket: WebSocket | null = null
  let recognitionSocketReady = false
  let recognitionStopSent = false
  let recognitionPrefix = ''
  let lastSpeechAt = 0
  let lastTranscriptChangeAt = 0
  let hasDetectedSpeech = false
  let hasTranscriptStarted = false
  let wakeupChecking = false
  let wakeupChunks: Int16Array[] = []
  let wakeupSampleCount = 0
  let wakeupSpeechStartedAt = 0
  let wakeupLastSpeechAt = 0
  let recordingWatchdog: number | null = null
  let standbyRequested = false
  let operationToken = 0
  let finalizeInFlight = false

  function createOperationToken() {
    operationToken += 1
    return operationToken
  }

  function invalidatePendingOperations() {
    operationToken += 1
  }

  function isOperationCurrent(token: number) {
    return token === operationToken
  }

  async function ensureAudioPipeline(token = operationToken) {
    if (!isSupported.value) {
      throw new Error('当前浏览器不支持语音输入。')
    }

    if (audioContext && mediaStream && workletNode) {
      return
    }

    let nextMediaStream: MediaStream | null = null
    let nextAudioContext: AudioContext | null = null
    let nextSourceNode: MediaStreamAudioSourceNode | null = null
    let nextWorkletNode: AudioWorkletNode | null = null
    let nextSinkNode: GainNode | null = null

    const ensureCurrent = async () => {
      if (isOperationCurrent(token)) {
        return
      }

      nextWorkletNode?.disconnect()
      nextSourceNode?.disconnect()
      nextSinkNode?.disconnect()
      stopMediaTracks(nextMediaStream)
      if (nextAudioContext && nextAudioContext.state !== 'closed') {
        await nextAudioContext.close()
      }
      throw new VoiceInputCancelledError()
    }

    try {
      nextMediaStream = await navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
      })
      await ensureCurrent()

      nextAudioContext = new AudioContext()
      await nextAudioContext.audioWorklet.addModule(PCM_WORKLET_PATH)
      await ensureCurrent()

      nextSourceNode = nextAudioContext.createMediaStreamSource(nextMediaStream)
      nextWorkletNode = new AudioWorkletNode(nextAudioContext, 'pcm-capture-worklet')
      nextSinkNode = nextAudioContext.createGain()
      nextSinkNode.gain.value = 0

      nextSourceNode.connect(nextWorkletNode)
      nextWorkletNode.connect(nextSinkNode)
      nextSinkNode.connect(nextAudioContext.destination)

      audioContext = nextAudioContext
      mediaStream = nextMediaStream
      sourceNode = nextSourceNode
      workletNode = nextWorkletNode
      sinkNode = nextSinkNode
      resampler = new PcmResampler(nextAudioContext.sampleRate, TARGET_SAMPLE_RATE)
      dictationChunker = new Int16ChunkAccumulator((TARGET_SAMPLE_RATE * chunkMs) / 1000)

      nextWorkletNode.port.onmessage = (event: MessageEvent<ArrayBuffer>) => {
        handleAudioChunk(event.data)
      }
    } catch (error) {
      nextWorkletNode?.disconnect()
      nextSourceNode?.disconnect()
      nextSinkNode?.disconnect()
      stopMediaTracks(nextMediaStream)
      if (nextAudioContext && nextAudioContext.state !== 'closed') {
        await nextAudioContext.close()
      }
      throw error
    }
  }

  async function resumeAudioPipeline(token = operationToken) {
    if (!audioContext) {
      return
    }
    if (audioContext.state === 'suspended') {
      await audioContext.resume()
      if (!isOperationCurrent(token)) {
        throw new VoiceInputCancelledError()
      }
    }
  }

  async function releaseAudioPipeline() {
    const currentAudioContext = audioContext
    const currentMediaStream = mediaStream
    const currentSourceNode = sourceNode
    const currentWorkletNode = workletNode
    const currentSinkNode = sinkNode

    audioContext = null
    mediaStream = null
    sourceNode = null
    workletNode = null
    sinkNode = null
    resampler = null
    dictationChunker = null
    resetWakeupBuffers()

    currentWorkletNode?.disconnect()
    currentSourceNode?.disconnect()
    currentSinkNode?.disconnect()
    stopMediaTracks(currentMediaStream)
    if (currentAudioContext && currentAudioContext.state !== 'closed') {
      await currentAudioContext.close()
    }
  }

  function resetWakeupBuffers() {
    wakeupChunks = []
    wakeupSampleCount = 0
    wakeupSpeechStartedAt = 0
    wakeupLastSpeechAt = 0
  }

  function resetRecognitionTracking() {
    recognitionSocketReady = false
    recognitionStopSent = false
    recognitionPrefix = ''
    lastSpeechAt = 0
    lastTranscriptChangeAt = 0
    hasDetectedSpeech = false
    hasTranscriptStarted = false
  }

  async function closeRecognitionSocket() {
    if (recognitionSocket) {
      try {
        recognitionSocket.close()
      } catch {
        // ignore close failures
      }
    }
    recognitionSocket = null
    resetRecognitionTracking()
  }

  async function fullyReset() {
    stopRecordingWatchdog()
    await closeRecognitionSocket()
    await releaseAudioPipeline()
    wakeupChecking = false
    finalizeInFlight = false
    mode.value = 'idle'
    statusText.value = ''
  }

  function stopRecordingWatchdog() {
    if (recordingWatchdog !== null) {
      window.clearInterval(recordingWatchdog)
      recordingWatchdog = null
    }
  }

  function startRecordingWatchdog() {
    stopRecordingWatchdog()
    recordingWatchdog = window.setInterval(() => {
      if (mode.value !== 'recording' || recognitionStopSent) {
        return
      }

      const now = Date.now()
      if (hasTranscriptStarted && lastTranscriptChangeAt > 0 && now - lastTranscriptChangeAt >= silenceTimeoutMs) {
        void stopRecording('silence_timeout')
      }
    }, 250)
  }

  function setError(message: string) {
    errorText.value = message
  }

  function clearError() {
    errorText.value = ''
  }

  function handleAudioChunk(buffer: ArrayBuffer) {
    if (!resampler) {
      return
    }

    const floatChunk = new Float32Array(buffer)
    const rms = computeRms(floatChunk)
    const pcmChunk = resampler.process(floatChunk)
    if (!pcmChunk.length) {
      return
    }

    if (mode.value === 'recording' || mode.value === 'stopping') {
      handleDictationChunk(pcmChunk, rms)
    } else if (mode.value === 'standby' || mode.value === 'wakeup-checking') {
      handleWakeupChunk(pcmChunk, rms)
    }
  }

  function handleDictationChunk(chunk: Int16Array, rms: number) {
    if (!dictationChunker || !recognitionSocket || !recognitionSocketReady || recognitionStopSent) {
      return
    }

    if (rms >= RMS_THRESHOLD) {
      hasDetectedSpeech = true
      lastSpeechAt = Date.now()
    } else if (
      mode.value === 'recording' &&
      hasDetectedSpeech &&
      lastSpeechAt > 0 &&
      Date.now() - lastSpeechAt >= silenceTimeoutMs
    ) {
      void stopRecording('silence_timeout')
      return
    }

    dictationChunker.push(chunk, (payload) => {
      recognitionSocket?.send(pcmToArrayBuffer(payload))
    })
  }

  function handleWakeupChunk(chunk: Int16Array, rms: number) {
    if (wakeupChecking) {
      return
    }

    const isSpeech = rms >= RMS_THRESHOLD
    const now = Date.now()
    if (isSpeech && wakeupSpeechStartedAt === 0) {
      wakeupSpeechStartedAt = now
    }
    if (isSpeech) {
      wakeupLastSpeechAt = now
      wakeupChunks.push(chunk)
      wakeupSampleCount += chunk.length
    } else if (wakeupSpeechStartedAt > 0 && wakeupSampleCount > 0) {
      wakeupChunks.push(chunk)
      wakeupSampleCount += chunk.length
    }

    if (!wakeupSpeechStartedAt) {
      return
    }

    const captureMs = (wakeupSampleCount / TARGET_SAMPLE_RATE) * 1000
    const silenceMs = wakeupLastSpeechAt > 0 ? now - wakeupLastSpeechAt : 0
    const shouldCheck =
      captureMs >= wakeupClipMs ||
      (captureMs >= WAKEUP_MIN_CAPTURE_MS && silenceMs >= WAKEUP_SILENCE_FLUSH_MS)

    if (shouldCheck) {
      const clip = concatChunks(wakeupChunks)
      resetWakeupBuffers()
      void runWakeupCheck(clip, operationToken)
    }
  }

  async function runWakeupCheck(chunk: Int16Array, operationSnapshot: number) {
    const authToken = options.getToken()
    if (!authToken) {
      standbyRequested = false
      invalidatePendingOperations()
      await fullyReset()
      setError('登录态已失效，请重新登录后再试。')
      return
    }

    wakeupChecking = true
    mode.value = 'wakeup-checking'
    statusText.value = '正在识别唤醒词...'

    try {
      const result = await checkVoiceWakeup(authToken, pcmToBase64(chunk), TARGET_SAMPLE_RATE)
      if (!isOperationCurrent(operationSnapshot) || !standbyRequested) {
        return
      }

      if (result.matched) {
        wakeupChecking = false
        statusText.value = '唤醒成功，开始录音...'
        await startDirectRecording(result.remainderText)
        return
      }

      transcript.value = result.text || ''
      mode.value = 'standby'
      statusText.value = '待命中，说“小厨小厨”即可唤醒'
    } catch (error) {
      if (error instanceof VoiceInputCancelledError || !isOperationCurrent(operationSnapshot)) {
        return
      }

      standbyRequested = false
      invalidatePendingOperations()
      await fullyReset()
      setError(error instanceof Error ? error.message : '唤醒检测失败，请稍后再试。')
    } finally {
      if (isOperationCurrent(operationSnapshot)) {
        wakeupChecking = false
      }
    }
  }

  async function openRecognitionSocket(operationSnapshot: number) {
    const authToken = options.getToken()
    if (!authToken) {
      throw new Error('登录态已失效，请重新登录后再试。')
    }

    await closeRecognitionSocket()

    await new Promise<void>((resolve, reject) => {
      const socket = new WebSocket(buildVoiceSocketUrl())
      socket.binaryType = 'arraybuffer'
      recognitionSocket = socket
      let handshakeDone = false

      socket.onopen = () => {
        if (!isOperationCurrent(operationSnapshot)) {
          socket.close()
          return
        }
        socket.send(
          JSON.stringify({
            type: 'start',
            token: authToken,
            mode: 'dictation',
            sample_rate: TARGET_SAMPLE_RATE,
            chunk_ms: chunkMs,
          }),
        )
      }

      socket.onerror = () => {
        if (!isOperationCurrent(operationSnapshot)) {
          return
        }
        reject(new Error('语音连接建立失败。'))
      }

      socket.onmessage = (event) => {
        if (!isOperationCurrent(operationSnapshot)) {
          return
        }

        const payload = JSON.parse(String(event.data)) as VoiceSocketEvent
        if (payload.event === 'ready') {
          handshakeDone = true
          recognitionSocketReady = true
          resolve()
          return
        }

        if (payload.event === 'status') {
          statusText.value = String(payload.data?.text || '正在处理语音...')
          return
        }

        if (payload.event === 'partial') {
          const nextTranscript = mergeTranscript(
            transcript.value || recognitionPrefix,
            String(payload.data?.text || ''),
          )
          if (nextTranscript && nextTranscript !== transcript.value) {
            hasTranscriptStarted = true
            lastTranscriptChangeAt = Date.now()
          }
          transcript.value = nextTranscript
          return
        }

        if (payload.event === 'final') {
          const finalText = mergeTranscript(transcript.value || recognitionPrefix, String(payload.data?.text || ''))
          void finalizeRecognition(finalText)
          return
        }

        if (payload.event === 'error') {
          const message = String(payload.data?.detail || '语音识别失败，请稍后重试。')
          if (!handshakeDone) {
            reject(new Error(message))
            return
          }
          void abortRecognition(message)
        }
      }

      socket.onclose = () => {
        if (!isOperationCurrent(operationSnapshot)) {
          return
        }

        if (!handshakeDone && !recognitionStopSent) {
          reject(new Error('语音连接已关闭，请稍后重试。'))
          return
        }
        if (mode.value === 'recording' || mode.value === 'starting' || mode.value === 'stopping') {
          if (recognitionStopSent) {
            void finalizeRecognition(transcript.value)
            return
          }

          if (!recognitionStopSent) {
            void abortRecognition('语音连接已断开，请稍后重试。')
          }
        }
      }
    })
  }

  async function startDirectRecording(initialText = '') {
    const nextToken = createOperationToken()
    finalizeInFlight = false
    wakeupChecking = false
    clearError()
    transcript.value = initialText.trim()
    recognitionPrefix = initialText.trim()
    mode.value = 'starting'
    statusText.value = '正在准备录音...'

    try {
      await ensureAudioPipeline(nextToken)
      await openRecognitionSocket(nextToken)
      await resumeAudioPipeline(nextToken)
      if (!isOperationCurrent(nextToken)) {
        return
      }

      hasDetectedSpeech = false
      lastSpeechAt = 0
      lastTranscriptChangeAt = initialText.trim() ? Date.now() : 0
      hasTranscriptStarted = Boolean(initialText.trim())
      mode.value = 'recording'
      statusText.value = '正在聆听，点击可停止'
      startRecordingWatchdog()
    } catch (error) {
      if (error instanceof VoiceInputCancelledError || !isOperationCurrent(nextToken)) {
        return
      }

      invalidatePendingOperations()
      await fullyReset()
      setError(error instanceof Error ? error.message : '麦克风启动失败，请稍后重试。')
    }
  }

  async function startStandby() {
    standbyRequested = true
    const nextToken = createOperationToken()
    finalizeInFlight = false
    wakeupChecking = false
    clearError()
    transcript.value = ''
    mode.value = 'standby'
    statusText.value = '待命中，说“小厨小厨”即可唤醒'

    try {
      await ensureAudioPipeline(nextToken)
      await resumeAudioPipeline(nextToken)
    } catch (error) {
      if (error instanceof VoiceInputCancelledError || !isOperationCurrent(nextToken)) {
        return
      }

      standbyRequested = false
      invalidatePendingOperations()
      await fullyReset()
      setError(error instanceof Error ? error.message : '待命启动失败，请稍后重试。')
    }
  }

  async function stopRecording(reason: StopReason) {
    if (!recognitionSocket || recognitionStopSent) {
      await fullyReset()
      return
    }

    stopRecordingWatchdog()
    mode.value = 'stopping'
    statusText.value = reason === 'silence_timeout' ? '检测到静音，正在结束录音...' : '正在结束录音...'
    recognitionStopSent = true

    const remainder = dictationChunker?.flush()
    if (remainder?.length) {
      recognitionSocket.send(pcmToArrayBuffer(remainder))
    }
    recognitionSocket.send(JSON.stringify({ type: 'stop', reason }))
  }

  async function finalizeRecognition(finalText: string) {
    if (finalizeInFlight) {
      return
    }

    finalizeInFlight = true
    const text = collapseRepeatedTranscript(finalText)
    const shouldResumeStandby = standbyRequested

    try {
      stopRecordingWatchdog()
      invalidatePendingOperations()
      await closeRecognitionSocket()
      await releaseAudioPipeline()
      mode.value = 'idle'
      statusText.value = ''

      if (!text) {
        transcript.value = ''
        if (!shouldResumeStandby) {
          setError('这次没有识别到清晰的语音，可以再试一次。')
          return
        }

        void startStandby()
        return
      }

      clearError()
      transcript.value = ''
      const standbyTask = shouldResumeStandby ? startStandby() : Promise.resolve()
      await options.onFinalText(text)
      await standbyTask
    } finally {
      finalizeInFlight = false
    }
  }

  async function abortRecognition(message: string) {
    invalidatePendingOperations()
    await fullyReset()
    setError(message)
  }

  async function stopActive(
    reason: StopReason = 'manual_stop',
    options: {
      disableStandby?: boolean
    } = {},
  ) {
    if (options.disableStandby) {
      standbyRequested = false
    }

    if (mode.value === 'recording' || mode.value === 'starting' || mode.value === 'stopping') {
      if (recognitionSocket && !recognitionStopSent) {
        await stopRecording(reason)
        return
      }

      invalidatePendingOperations()
      transcript.value = ''
      await fullyReset()
      if (standbyRequested) {
        await startStandby()
      }
      return
    }

    if (mode.value === 'standby' || mode.value === 'wakeup-checking' || mode.value === 'idle') {
      standbyRequested = false
    }

    invalidatePendingOperations()
    transcript.value = ''
    await fullyReset()
  }

  async function stopAll(reason: StopReason = 'manual_stop') {
    standbyRequested = false
    await stopActive(reason, { disableStandby: true })
  }

  function isStandbyActive() {
    return standbyRequested
  }

  function clearVoiceFeedback() {
    clearError()
    if (mode.value === 'idle') {
      transcript.value = ''
    }
  }

  function setExternalError(message: string) {
    setError(message)
  }

  function handleVisibilityChange() {
    if (document.hidden && mode.value !== 'idle') {
      void stopAll('manual_stop')
    }
  }

  document.addEventListener('visibilitychange', handleVisibilityChange)

  onBeforeUnmount(() => {
    document.removeEventListener('visibilitychange', handleVisibilityChange)
    stopRecordingWatchdog()
    void stopAll('manual_stop')
  })

  return {
    mode,
    statusText,
    transcript,
    errorText,
    isSupported,
    isBusy,
    isStandbyActive,
    startDirectRecording,
    startStandby,
    stopActive,
    stopAll,
    clearVoiceFeedback,
    setExternalError,
  }
}
