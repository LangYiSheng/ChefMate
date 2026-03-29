<script setup lang="ts">
import type { ConversationRecord } from '../types/chat'

defineProps<{
  conversation: ConversationRecord
  stageLabel: string
}>()

const emit = defineEmits<{
  toggleSidebar: []
}>()
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
        <p class="eyebrow">当前任务</p>
        <h2>{{ conversation.title }}</h2>
      </div>
    </div>

    <div class="header-summary">
      <span class="stage-pill">{{ stageLabel }}</span>
      <p>{{ conversation.taskSummary }}</p>
    </div>
  </header>
</template>

<style scoped>
.chat-header {
  position: sticky;
  top: 0;
  z-index: 10;
  display: flex;
  align-items: center;
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
  align-items: center;
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
  font-size: 0.72rem;
  letter-spacing: 0.16em;
  text-transform: uppercase;
}

.title-group h2 {
  margin: 0;
  font-size: 1.35rem;
}

.header-summary {
  display: flex;
  gap: 0.85rem;
  align-items: center;
  justify-content: flex-end;
  max-width: 34rem;
  color: var(--color-text-soft);
}

.header-summary p {
  margin: 0;
  font-size: 0.92rem;
}

.stage-pill {
  flex: 0 0 auto;
  padding: 0.35rem 0.72rem;
  border-radius: 999px;
  background: rgba(47, 93, 80, 0.12);
  color: var(--color-accent);
  font-size: 0.78rem;
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

  .header-summary {
    flex-wrap: wrap;
    justify-content: flex-start;
  }
}
</style>
