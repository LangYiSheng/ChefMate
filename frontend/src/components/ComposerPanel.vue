<script setup lang="ts">
import { ref } from 'vue'

const props = defineProps<{
  disabled?: boolean
  suggestions: string[]
}>()

const emit = defineEmits<{
  send: [prompt: string]
}>()

const draft = ref('')

function submit() {
  const content = draft.value.trim()
  if (!content || props.disabled) {
    return
  }

  emit('send', content)
  draft.value = ''
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
      <textarea
        v-model="draft"
        class="composer-input"
        :disabled="disabled"
        placeholder="输入你想做什么、手头有什么食材，或者直接问当前步骤该怎么推进。"
        rows="1"
        @keydown="onKeydown"
      />

      <div class="composer-actions">
        <p>Mock 模式，当前主要演示布局和卡片逻辑。</p>
        <button class="send-button" type="button" :disabled="disabled" @click="submit">发送</button>
      </div>
    </div>
  </section>
</template>

<style scoped>
.composer-shell {
  position: sticky;
  bottom: 0;
  padding: 0 2rem 1.2rem;
  background:
    linear-gradient(180deg, rgba(244, 239, 230, 0), rgba(244, 239, 230, 0.88) 24%, rgba(244, 239, 230, 0.96));
}

.suggestion-row {
  display: flex;
  flex-wrap: wrap;
  gap: 0.55rem;
  width: min(100%, 56rem);
  margin: 0 auto 0.75rem;
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
  background: rgba(255, 252, 247, 0.94);
  box-shadow: var(--shadow-soft);
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
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
}

.composer-actions p {
  margin: 0;
  color: var(--color-text-soft);
  font-size: 0.85rem;
}

.send-button {
  padding: 0.65rem 1.1rem;
  border-radius: 999px;
  background: linear-gradient(135deg, rgba(47, 93, 80, 0.96), rgba(32, 57, 49, 0.96));
  color: #fef7ef;
  cursor: pointer;
}

.send-button:disabled,
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
  .composer-actions {
    flex-direction: column;
    align-items: stretch;
  }

  .send-button {
    width: 100%;
  }
}
</style>
