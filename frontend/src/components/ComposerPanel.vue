<script setup lang="ts">
import { computed, ref } from 'vue'

import { uploadImage } from '../lib/api'
import { getAuthToken } from '../state/auth'
import type { ChatAttachment } from '../types/chat'

const props = defineProps<{
  disabled?: boolean
  suggestions: string[]
  voiceSupported?: boolean
  voiceMode?: 'idle' | 'starting' | 'recording' | 'stopping' | 'standby' | 'wakeup-checking'
  voiceStatusText?: string
  voiceTranscript?: string
  voiceErrorText?: string
  voiceStandbyPaused?: boolean
  wakeWordEnabled?: boolean
}>()

const emit = defineEmits<{
  send: [payload: { prompt: string; attachments: ChatAttachment[] }]
  requestVoiceRecord: []
  toggleWakeStandby: []
}>()

const draft = ref('')
const attachment = ref<(ChatAttachment & { status: 'uploading' | 'ready' | 'error' }) | null>(null)
const fileInput = ref<HTMLInputElement | null>(null)

const isVoicePresentationMode = computed(() => (props.voiceMode ?? 'idle') !== 'idle')
const isVoiceStandbyState = computed(
  () => props.voiceMode === 'standby' || props.voiceMode === 'wakeup-checking',
)
const isVoiceInputState = computed(
  () =>
    props.voiceMode === 'starting' ||
    props.voiceMode === 'recording' ||
    props.voiceMode === 'stopping',
)

const voiceActionLabel = computed(() =>
  props.voiceMode === 'starting' || props.voiceMode === 'recording' || props.voiceMode === 'stopping'
    ? '停止'
    : '语音',
)
const standbyActionLabel = computed(() =>
  props.voiceMode === 'standby' || props.voiceMode === 'wakeup-checking' ? '结束待命' : '待命',
)
const voiceBlockedByAttachment = computed(() => attachment.value !== null)
const voiceDisabled = computed(
  () => props.disabled || voiceBlockedByAttachment.value || props.voiceSupported === false,
)
const uploadDisabled = computed(() => props.disabled || isVoicePresentationMode.value)
const standbyDisabled = computed(
  () =>
    voiceDisabled.value ||
    props.voiceMode === 'recording' ||
    props.voiceMode === 'starting' ||
    props.voiceMode === 'stopping',
)
const sendDisabled = computed(
  () =>
    props.disabled ||
    isVoicePresentationMode.value ||
    attachment.value?.status === 'uploading' ||
    attachment.value?.status === 'error',
)
const displayedInputValue = computed({
  get: () => (isVoicePresentationMode.value ? props.voiceTranscript || '' : draft.value),
  set: (value: string) => {
    if (!isVoicePresentationMode.value) {
      draft.value = value
    }
  },
})
const composerPlaceholder = computed(() => {
  if (props.voiceErrorText && !props.voiceTranscript) {
    return props.voiceErrorText
  }
  if (props.voiceStandbyPaused) {
    return '待命已暂停，等这轮回答结束后会自动继续'
  }
  if (props.voiceMode === 'standby') {
    return '待命中，说“小厨小厨”开始语音输入'
  }
  if (props.voiceMode === 'wakeup-checking') {
    return '正在识别唤醒词，请继续说“小厨小厨”'
  }
  if (props.voiceMode === 'starting') {
    return '正在打开麦克风，马上就能开始说'
  }
  if (props.voiceMode === 'recording') {
    return '正在听你说，直接说想吃什么就好'
  }
  if (props.voiceMode === 'stopping') {
    return '正在整理这段语音，请稍等一下'
  }
  return '尽管说出你的需求吧！'
})
const composerCardClass = computed(() => ({
  'voice-presenting': isVoicePresentationMode.value,
  'voice-standby': isVoiceStandbyState.value && !props.voiceStandbyPaused,
  'voice-standby-paused': isVoiceStandbyState.value && props.voiceStandbyPaused,
  'voice-active': isVoiceInputState.value,
  'voice-checking': props.voiceMode === 'wakeup-checking',
}))
const composerInputClass = computed(() => ({
  'voice-mode': isVoicePresentationMode.value,
  'voice-standby-input': isVoiceStandbyState.value,
  'voice-active-input': isVoiceInputState.value,
  paused: props.voiceStandbyPaused,
}))

function submit() {
  const content = draft.value.trim()
  if (
    sendDisabled.value ||
    (!content && !attachment.value) ||
    attachment.value?.status === 'uploading' ||
    attachment.value?.status === 'error'
  ) {
    return
  }

  emit('send', {
    prompt: content,
    attachments: attachment.value ? [normalizeAttachment(attachment.value)] : [],
  })
  draft.value = ''
  attachment.value = null
}

function useSuggestion(suggestion: string) {
  if (props.disabled || isVoicePresentationMode.value) {
    return
  }

  draft.value = suggestion
}

function onKeydown(event: KeyboardEvent) {
  if (isVoicePresentationMode.value) {
    return
  }

  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault()
    submit()
  }
}

function normalizeAttachment(item: ChatAttachment & { status: 'uploading' | 'ready' }): ChatAttachment {
  return {
    id: item.id,
    kind: item.kind,
    name: item.name,
    previewUrl: item.previewUrl,
    fileId: item.fileId,
    fileUrl: item.fileUrl,
  }
}

function triggerFilePicker() {
  if (uploadDisabled.value) {
    return
  }

  fileInput.value?.click()
}

function clearAttachment() {
  attachment.value = null
  if (fileInput.value) {
    fileInput.value.value = ''
  }
}

function readFileAsDataUrl(file: File) {
  return new Promise<string>((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(String(reader.result ?? ''))
    reader.onerror = () => reject(reader.error)
    reader.readAsDataURL(file)
  })
}

async function onFileChange(event: Event) {
  const input = event.target as HTMLInputElement | null
  const file = input?.files?.[0]
  if (!file || props.disabled || isVoicePresentationMode.value) {
    return
  }

  const token = getAuthToken()
  if (!token) {
    clearAttachment()
    return
  }

  attachment.value = {
    id: `attachment-${Date.now()}`,
    kind: 'image',
    name: file.name,
    previewUrl: '',
    status: 'uploading',
  }

  try {
    const previewUrl = await readFileAsDataUrl(file)
    attachment.value = {
      id: `attachment-${Date.now()}`,
      kind: 'image',
      name: file.name,
      previewUrl,
      status: 'uploading',
    }
    const uploaded = await uploadImage(token, file)
    window.setTimeout(() => {
      attachment.value = {
        ...uploaded,
        previewUrl,
        status: 'ready',
      }
    }, 220)
  } catch {
    attachment.value = {
      id: `attachment-${Date.now()}`,
      kind: 'image',
      name: file.name,
      previewUrl: '',
      status: 'error',
    }
  }
}

function requestVoiceRecord() {
  if (voiceDisabled.value) {
    return
  }
  emit('requestVoiceRecord')
}

function toggleWakeStandby() {
  if (standbyDisabled.value) {
    return
  }
  emit('toggleWakeStandby')
}
</script>

<template>
  <section class="composer-shell">
    <div class="suggestion-row">
      <button
        v-for="suggestion in suggestions"
        :key="suggestion"
        type="button"
        class="suggestion-chip"
        :disabled="disabled || isVoicePresentationMode"
        @click="useSuggestion(suggestion)"
      >
        {{ suggestion }}
      </button>
    </div>

    <div class="composer-card" :class="composerCardClass">
      <input
        ref="fileInput"
        class="file-input"
        type="file"
        accept="image/*"
        @change="onFileChange"
      />

      <div v-if="attachment" class="attachment-preview" :class="attachment.status">
        <div class="attachment-thumb-shell">
          <img
            v-if="attachment.previewUrl"
            :src="attachment.previewUrl"
            :alt="attachment.name"
            class="attachment-thumb"
          />
          <div v-else class="attachment-thumb loading"></div>
        </div>

        <div class="attachment-meta">
          <strong>{{ attachment.name }}</strong>
          <span class="attachment-status" :class="attachment.status">
            {{
              attachment.status === 'ready'
                ? '图片已就绪'
                : attachment.status === 'error'
                  ? '上传失败，请重试'
                  : '图片上传中…'
            }}
          </span>
        </div>

        <button type="button" class="attachment-remove" @click="clearAttachment">取消</button>
      </div>

      <textarea
        v-model="displayedInputValue"
        class="composer-input"
        :class="composerInputClass"
        :disabled="disabled && !isVoicePresentationMode"
        :readonly="disabled || isVoicePresentationMode"
        :placeholder="composerPlaceholder"
        rows="1"
        @keydown="onKeydown"
      />

      <div class="composer-actions">
        <div class="action-buttons">
          <button class="upload-button" type="button" :disabled="uploadDisabled" @click="triggerFilePicker">+</button>
          <button
            class="voice-button"
            type="button"
            :disabled="voiceDisabled"
            :title="
              voiceBlockedByAttachment
                ? '当前有未发送的图片附件，请先发送或取消后再使用语音。'
                : voiceSupported === false
                  ? '当前浏览器不支持语音输入。'
                  : ''
            "
            @click="requestVoiceRecord"
          >
            {{ voiceActionLabel }}
          </button>
          <button
            v-if="wakeWordEnabled"
            class="voice-button standby-button"
            type="button"
            :disabled="standbyDisabled"
            @click="toggleWakeStandby"
          >
            {{ standbyActionLabel }}
          </button>
          <button class="send-button" type="button" :disabled="sendDisabled" @click="submit">发送</button>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.composer-shell {
  position: absolute;
  right: 0;
  bottom: 0;
  left: 0;
  z-index: 6;
  padding: 0 2rem 1.2rem;
  background: transparent;
  pointer-events: none;
}

.suggestion-row {
  display: flex;
  flex-wrap: wrap;
  gap: 0.55rem;
  width: min(100%, 56rem);
  margin: 0 auto 0.75rem;
  pointer-events: auto;
}

.suggestion-chip {
  padding: 0.45rem 0.8rem;
  border: 1px solid rgba(47, 93, 80, 0.12);
  border-radius: 999px;
  background: rgba(255, 251, 245, 0.8);
  color: var(--color-accent);
  cursor: pointer;
}

.composer-card {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 0.85rem;
  width: min(100%, 56rem);
  margin: 0 auto;
  padding: 1rem 1rem 0.9rem;
  overflow: hidden;
  border: 1px solid rgba(47, 93, 80, 0.14);
  border-radius: 1.4rem;
  background: rgba(255, 252, 247, 0.88);
  backdrop-filter: blur(16px);
  box-shadow: 0 18px 36px rgba(33, 47, 43, 0.1);
  isolation: isolate;
  pointer-events: auto;
  transition:
    box-shadow 180ms ease,
    background 180ms ease,
    transform 180ms ease;
}

.composer-card::before,
.composer-card::after {
  content: '';
  position: absolute;
  pointer-events: none;
}

.composer-card::before {
  inset: 0;
  padding: 1.3px;
  border-radius: inherit;
  background: transparent;
  opacity: 0;
  transition:
    opacity 180ms ease,
    filter 180ms ease;
  -webkit-mask:
    linear-gradient(#fff 0 0) content-box,
    linear-gradient(#fff 0 0);
  -webkit-mask-composite: xor;
  mask:
    linear-gradient(#fff 0 0) content-box,
    linear-gradient(#fff 0 0);
  mask-composite: exclude;
}

.composer-card::after {
  inset: -42% -12%;
  border-radius: 50%;
  opacity: 0;
  filter: blur(20px);
  transition: opacity 180ms ease;
}

.composer-card > * {
  position: relative;
  z-index: 1;
}

.composer-card.voice-presenting {
  background: rgba(255, 253, 248, 0.95);
}

.composer-card.voice-standby::before {
  opacity: 0.92;
  background: linear-gradient(
    135deg,
    rgba(248, 181, 102, 0.92),
    rgba(107, 183, 157, 0.78),
    rgba(255, 225, 186, 0.82)
  );
  filter: saturate(1.08);
}

.composer-card.voice-standby::after {
  opacity: 0.24;
  background:
    radial-gradient(circle at 18% 28%, rgba(255, 198, 129, 0.18), transparent 24%),
    radial-gradient(circle at 80% 68%, rgba(102, 180, 154, 0.14), transparent 28%);
  animation: composer-aura-breathe 4.2s ease-in-out infinite;
}

.composer-card.voice-standby-paused::before {
  opacity: 0.78;
  background: linear-gradient(
    135deg,
    rgba(221, 171, 112, 0.72),
    rgba(123, 170, 154, 0.58),
    rgba(244, 225, 197, 0.68)
  );
}

.composer-card.voice-standby-paused::after {
  opacity: 0.14;
  background: radial-gradient(circle at 50% 50%, rgba(255, 207, 148, 0.12), transparent 40%);
}

.composer-card.voice-active::before {
  opacity: 1;
  background: conic-gradient(
    from 0deg,
    rgba(255, 220, 151, 0.2),
    rgba(244, 146, 94, 0.98),
    rgba(82, 186, 158, 0.96),
    rgba(255, 217, 135, 0.96),
    rgba(255, 220, 151, 0.2)
  );
  filter: saturate(1.22);
}

.composer-card.voice-active::after {
  opacity: 0.28;
  background: conic-gradient(
    from 90deg,
    transparent 0deg,
    rgba(255, 189, 115, 0.05) 84deg,
    rgba(255, 189, 115, 0.24) 126deg,
    rgba(98, 194, 166, 0.22) 188deg,
    rgba(98, 194, 166, 0.04) 240deg,
    transparent 360deg
  );
  animation: composer-aura-flow 2.4s linear infinite;
}

.composer-card.voice-checking::after {
  opacity: 0.18;
}

.file-input {
  display: none;
}

.attachment-preview {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  gap: 0.8rem;
  align-items: center;
  padding: 0.8rem;
  border: 1px solid rgba(47, 93, 80, 0.12);
  border-radius: 1rem;
  background: rgba(255, 255, 255, 0.82);
}

.attachment-preview.ready {
  border-color: rgba(47, 93, 80, 0.2);
}

.attachment-thumb-shell {
  width: 3.4rem;
  height: 3.4rem;
  border-radius: 0.85rem;
  overflow: hidden;
  background: rgba(47, 93, 80, 0.08);
}

.attachment-thumb {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.attachment-thumb.loading {
  position: relative;
}

.attachment-thumb.loading::after {
  content: '';
  position: absolute;
  inset: 0.9rem;
  border: 2px solid rgba(47, 93, 80, 0.14);
  border-top-color: var(--color-accent);
  border-radius: 999px;
  animation: composer-spin 0.8s linear infinite;
}

.attachment-meta strong,
.attachment-meta span {
  display: block;
}

.attachment-meta span {
  margin-top: 0.2rem;
}

.attachment-status {
  color: var(--color-text-soft);
  font-size: 0.8rem;
}

.attachment-status.ready {
  color: var(--color-accent);
}

.attachment-remove {
  color: var(--color-text-soft);
  cursor: pointer;
}

.composer-input {
  width: 100%;
  min-height: 5.1rem;
  resize: vertical;
  border: 0;
  outline: none;
  color: var(--color-text);
  background: transparent;
  line-height: 1.7;
}

.composer-input::placeholder {
  color: rgba(92, 107, 101, 0.74);
}

.composer-input.voice-mode {
  resize: none;
}

.composer-input.voice-standby-input::placeholder {
  color: rgba(63, 109, 95, 0.86);
}

.composer-input.voice-active-input {
  color: rgba(30, 47, 42, 0.94);
}

.composer-input.voice-active-input::placeholder {
  color: rgba(47, 93, 80, 0.9);
}

.composer-input.paused::placeholder {
  color: rgba(96, 113, 106, 0.82);
}

.composer-actions {
  display: flex;
  justify-content: flex-end;
}

.action-buttons {
  display: flex;
  gap: 0.55rem;
}

.upload-button,
.voice-button,
.send-button {
  min-height: 2.7rem;
  padding: 0 1rem;
  border-radius: 999px;
  cursor: pointer;
}

.upload-button {
  min-width: 2.7rem;
  background: rgba(255, 255, 255, 0.86);
  color: var(--color-accent);
  border: 1px solid rgba(47, 93, 80, 0.12);
  font-size: 1.2rem;
}

.voice-button {
  background: rgba(255, 255, 255, 0.86);
  color: var(--color-accent);
  border: 1px solid rgba(47, 93, 80, 0.12);
}

.standby-button {
  background: rgba(242, 247, 244, 0.96);
}

.send-button {
  background: linear-gradient(135deg, rgba(47, 93, 80, 0.96), rgba(32, 57, 49, 0.96));
  color: #fef7ef;
}

.send-button:disabled,
.upload-button:disabled,
.voice-button:disabled,
.composer-input:disabled,
.suggestion-chip:disabled {
  cursor: not-allowed;
  opacity: 0.58;
}

@media (max-width: 960px) {
  .composer-shell {
    padding: 0 1rem 1rem;
  }
}

@media (max-width: 640px) {
  .attachment-preview {
    grid-template-columns: auto minmax(0, 1fr);
  }

  .attachment-remove {
    grid-column: 1 / -1;
    justify-self: flex-end;
  }

  .composer-card.voice-active::after {
    opacity: 0.22;
  }
}

@keyframes composer-spin {
  to {
    transform: rotate(360deg);
  }
}

@keyframes composer-aura-breathe {
  0%,
  100% {
    transform: scale(0.98);
    opacity: 0.28;
  }

  50% {
    transform: scale(1.03);
    opacity: 0.32;
  }
}

@keyframes composer-aura-flow {
  to {
    transform: rotate(360deg);
  }
}
</style>
