<script setup lang="ts">
import { computed } from 'vue'

import type {
  ConversationRecord,
  ConversationTimerSlot,
} from '../types/chat'

const props = defineProps<{
  conversation: ConversationRecord
  stageLabel: string
  timerSlot: ConversationTimerSlot | null
  timerNoticeText: string
  timerNoticeTone: 'info' | 'alert' | null
  timerNoticeNeedsConfirm: boolean
}>()

const emit = defineEmits<{
  toggleSidebar: []
  pauseTimer: []
  resumeTimer: []
  resetTimer: []
  cancelTimer: []
  dismissTimerNotice: []
}>()

const eyebrowText = computed(() => {
  if (props.conversation.currentRecipe) {
    return `${props.stageLabel} · ${props.conversation.currentRecipe}`
  }

  return props.stageLabel
})

function formatSeconds(seconds: number) {
  const minutes = Math.floor(seconds / 60)
  const restSeconds = seconds % 60
  return `${String(minutes).padStart(2, '0')}:${String(restSeconds).padStart(2, '0')}`
}
</script>

<template>
  <header class="chat-header">
    <div class="header-main">
      <button class="menu-button" type="button" aria-label="打开侧边栏" @click="emit('toggleSidebar')">
        <span></span>
        <span></span>
        <span></span>
      </button>

      <div class="title-group">
        <p class="eyebrow">{{ eyebrowText }}</p>
        <h2>{{ conversation.title }}</h2>
      </div>
    </div>

    <Transition name="timer-slide" mode="out-in">
      <div
        v-if="timerNoticeText"
        key="notice"
        class="timer-notice"
        :class="{ alert: timerNoticeTone === 'alert' }"
      >
        <strong>{{ timerNoticeText }}</strong>
        <button
          v-if="timerNoticeNeedsConfirm"
          type="button"
          @click="emit('dismissTimerNotice')"
        >
          确认
        </button>
      </div>

      <div v-else-if="timerSlot" key="slot" class="timer-slot">
        <div class="timer-readout">
          <span class="timer-icon">⏱</span>
          <strong>{{ formatSeconds(timerSlot.remainingSeconds) }}</strong>
        </div>

        <div class="timer-actions">
          <button
            v-if="timerSlot.status === 'running'"
            type="button"
            @click="emit('pauseTimer')"
          >
            暂停
          </button>
          <button
            v-else-if="timerSlot.remainingSeconds > 0"
            type="button"
            @click="emit('resumeTimer')"
          >
            继续
          </button>
          <button type="button" @click="emit('resetTimer')">重置</button>
          <button type="button" @click="emit('cancelTimer')">取消</button>
        </div>
      </div>
    </Transition>
  </header>
</template>

<style scoped>
.chat-header {
  position: sticky;
  top: 0;
  z-index: 10;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1.5rem;
  padding: 1.1rem 2rem 1rem;
  border-bottom: 1px solid rgba(47, 93, 80, 0.1);
  background: rgba(244, 239, 230, 0.76);
  backdrop-filter: blur(12px);
}

.header-main {
  display: flex;
  gap: 0.95rem;
  align-items: flex-start;
  min-width: 0;
}

.menu-button {
  display: none;
  flex-direction: column;
  gap: 0.24rem;
  align-items: center;
  justify-content: center;
  width: 2.6rem;
  height: 2.6rem;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.6);
  box-shadow: 0 12px 22px rgba(29, 43, 39, 0.07);
  cursor: pointer;
}

.menu-button span {
  width: 1rem;
  height: 2px;
  border-radius: 999px;
  background: var(--color-accent);
}

.eyebrow {
  margin: 0 0 0.18rem;
  color: var(--color-text-soft);
  font-size: 0.82rem;
}

.title-group h2 {
  margin: 0;
  font-size: 1.35rem;
}

.timer-slot {
  display: flex;
  gap: 0.6rem;
  align-items: center;
  padding-top: 0.15rem;
}

.timer-notice {
  display: inline-flex;
  gap: 0.65rem;
  align-items: center;
  padding-top: 0.15rem;
  color: var(--color-accent);
}

.timer-notice strong {
  font-size: 0.92rem;
  font-weight: 600;
}

.timer-notice.alert {
  animation: shake 420ms ease-in-out 2;
}

.timer-notice.alert strong {
  font-size: 1rem;
  font-weight: 700;
}

.timer-notice button {
  min-height: 2rem;
  padding: 0 0.85rem;
  border: 1px solid rgba(47, 93, 80, 0.14);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.74);
  color: var(--color-accent);
  font-size: 0.82rem;
  cursor: pointer;
}

.timer-readout {
  display: inline-flex;
  gap: 0.35rem;
  align-items: center;
  color: var(--color-accent);
}

.timer-icon {
  font-size: 0.92rem;
}

.timer-readout strong {
  font-size: 1rem;
  line-height: 1;
}

.timer-actions {
  display: flex;
  gap: 0.4rem;
}

.timer-actions button {
  min-height: 2rem;
  padding: 0 0.75rem;
  border: 1px solid rgba(47, 93, 80, 0.14);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.72);
  color: var(--color-accent);
  font-size: 0.82rem;
  cursor: pointer;
}

.timer-slide-enter-active,
.timer-slide-leave-active {
  transition:
    opacity 180ms ease,
    transform 220ms ease;
}

.timer-slide-enter-from,
.timer-slide-leave-to {
  opacity: 0;
  transform: translateX(0.75rem);
}

@keyframes shake {
  0%,
  100% {
    transform: translateX(0);
  }

  25% {
    transform: translateX(-0.18rem);
  }

  75% {
    transform: translateX(0.18rem);
  }
}

@media (max-width: 960px) {
  .chat-header {
    flex-direction: column;
    align-items: stretch;
    gap: 0.85rem;
    padding: 1rem 1rem 0.85rem;
  }

  .menu-button {
    display: inline-flex;
  }

  .title-group h2 {
    font-size: 1.15rem;
  }

  .timer-slot {
    flex-wrap: wrap;
    padding-top: 0;
  }
}
</style>
