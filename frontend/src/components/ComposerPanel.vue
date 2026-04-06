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
const voiceModeLabel = computed(() => {
  if (props.voiceMode === 'recording') {
    return '录音中'
  }
  if (props.voiceMode === 'stopping') {
    return '结束中'
  }
  if (props.voiceMode === 'standby') {
    return '待命中'
  }
  if (props.voiceMode === 'wakeup-checking') {
    return '唤醒检测'
  }
  if (props.voiceMode === 'starting') {
    return '准备中'
  }
  return '语音输入'
})
const voiceActionLabel = computed(() =>
  props.voiceMode === 'recording' || props.voiceMode === 'stopping' ? '停止' : '语音',
)
const standbyActionLabel = computed(() =>
  props.voiceMode === 'standby' || props.voiceMode === 'wakeup-checking' ? '结束待命' : '待命',
)
const voiceBlockedByAttachment = computed(() => attachment.value !== null)
const voiceDisabled = computed(
  () => props.disabled || voiceBlockedByAttachment.value || props.voiceSupported === false,
)
const standbyDisabled = computed(
  () =>
    voiceDisabled.value ||
    props.voiceMode === 'recording' ||
    props.voiceMode === 'starting' ||
    props.voiceMode === 'stopping',
)
const showVoiceFeedback = computed(
  () => Boolean(props.voiceStatusText || props.voiceTranscript || props.voiceErrorText),
)

function submit() {
  const content = draft.value.trim()
  if (
    props.disabled ||
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
  if (props.disabled) {
    return
  }

  draft.value = suggestion
}

function onKeydown(event: KeyboardEvent) {
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
  if (props.disabled) {
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
  if (!file || props.disabled) {
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
        @click="useSuggestion(suggestion)"
      >
        {{ suggestion }}
      </button>
    </div>

    <div class="composer-card">
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

      <div v-if="showVoiceFeedback" class="voice-feedback" :class="voiceMode || 'idle'">
        <div class="voice-feedback-header">
          <div>
            <strong>{{ voiceModeLabel }}</strong>
            <p>{{ voiceStatusText || '语音结果会实时显示在这里' }}</p>
          </div>
        </div>

        <p v-if="voiceTranscript" class="voice-transcript">{{ voiceTranscript }}</p>
        <p v-if="voiceErrorText" class="voice-error">{{ voiceErrorText }}</p>
      </div>

      <textarea
        v-model="draft"
        class="composer-input"
        :disabled="disabled"
        placeholder="尽管说出你的需求吧！"
        rows="1"
        @keydown="onKeydown"
      />

      <div class="composer-actions">
        <div class="action-buttons">
          <button class="upload-button" type="button" :disabled="disabled" @click="triggerFilePicker">+</button>
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
          <button
            class="send-button"
            type="button"
            :disabled="disabled || attachment?.status === 'uploading' || attachment?.status === 'error'"
            @click="submit"
          >
            发送
          </button>
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
  display: flex;
  flex-direction: column;
  gap: 0.85rem;
  width: min(100%, 56rem);
  margin: 0 auto;
  padding: 1rem 1rem 0.9rem;
  border: 1px solid rgba(47, 93, 80, 0.14);
  border-radius: 1.4rem;
  background: rgba(255, 252, 247, 0.88);
  backdrop-filter: blur(16px);
  box-shadow: 0 18px 36px rgba(33, 47, 43, 0.1);
  pointer-events: auto;
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

.voice-feedback {
  padding: 0.9rem 1rem;
  border: 1px solid rgba(47, 93, 80, 0.14);
  border-radius: 1rem;
  background: rgba(250, 247, 240, 0.88);
}

.voice-feedback.recording,
.voice-feedback.standby,
.voice-feedback.wakeup-checking,
.voice-feedback.starting,
.voice-feedback.stopping {
  border-color: rgba(47, 93, 80, 0.24);
  background: rgba(239, 247, 242, 0.94);
}

.voice-feedback-header {
  display: flex;
  align-items: flex-start;
  justify-content: flex-start;
  gap: 1rem;
}

.voice-feedback-header strong {
  display: block;
  margin-bottom: 0.2rem;
}

.voice-feedback-header p {
  margin: 0;
  color: var(--color-text-soft);
  font-size: 0.86rem;
}

.voice-transcript,
.voice-error {
  margin: 0.75rem 0 0;
  line-height: 1.7;
  white-space: pre-wrap;
}

.voice-transcript {
  color: var(--color-text);
}

.voice-error {
  color: #b34b39;
}

.composer-input {
  width: 100%;
  min-height: 4.75rem;
  resize: vertical;
  border: 0;
  outline: none;
  color: var(--color-text);
  background: transparent;
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

  .voice-feedback-header {
    flex-direction: column;
  }
}

@keyframes composer-spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
