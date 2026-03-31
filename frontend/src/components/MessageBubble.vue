<script setup lang="ts">
import MessageCardRenderer from './cards/MessageCardRenderer.vue'
import type { CardActionEvent, ChatMessage, TimerRequest } from '../types/chat'

defineProps<{
  message: ChatMessage
  autoStartStepTimer: boolean
}>()

const emit = defineEmits<{
  cardAction: [action: CardActionEvent]
  timerRequest: [payload: TimerRequest]
}>()

function avatarText(role: ChatMessage['role']) {
  if (role === 'assistant') {
    return 'CM'
  }

  if (role === 'system') {
    return 'SYS'
  }

  return '我'
}

function cardKey(messageId: string, card: NonNullable<ChatMessage['cards']>[number], index: number) {
  return `${messageId}-${card.type}-${index}`
}
</script>

<template>
  <article class="message-row" :class="message.role">
    <div class="avatar">{{ avatarText(message.role) }}</div>

    <div class="message-body">
      <div v-if="message.content" class="message-bubble">
        <p>{{ message.content }}</p>
      </div>

      <div v-if="message.attachments?.length" class="attachment-stack">
        <figure
          v-for="attachment in message.attachments"
          :key="attachment.id"
          class="message-attachment"
        >
          <img :src="attachment.previewUrl" :alt="attachment.name" />
          <figcaption>{{ attachment.name }}</figcaption>
        </figure>
      </div>

      <div v-if="message.cards?.length" class="card-stack">
        <MessageCardRenderer
          v-for="(card, index) in message.cards"
          :key="cardKey(message.id, card, index)"
          :card="card"
          :auto-start-step-timer="autoStartStepTimer"
          @action="emit('cardAction', $event)"
          @start-timer="emit('timerRequest', $event)"
        />
      </div>

      <time class="message-time">{{ message.createdAt }}</time>
    </div>
  </article>
</template>

<style scoped>
.message-row {
  display: flex;
  gap: 0.9rem;
  align-items: flex-start;
  margin-bottom: 1.35rem;
}

.message-row.user {
  flex-direction: row-reverse;
}

.avatar {
  display: inline-flex;
  flex: 0 0 auto;
  align-items: center;
  justify-content: center;
  width: 2.4rem;
  height: 2.4rem;
  border-radius: 1rem;
  background: rgba(47, 93, 80, 0.12);
  color: var(--color-accent);
  font-size: 0.8rem;
  font-weight: 700;
}

.message-row.user .avatar {
  background: rgba(229, 143, 91, 0.16);
  color: #a05522;
}

.message-body {
  max-width: min(100%, 48rem);
}

.message-row.assistant .message-body,
.message-row.system .message-body {
  width: min(100%, 48rem);
}

.message-bubble {
  padding: 1rem 1.1rem;
  border: 1px solid var(--color-border);
  border-radius: 1.25rem;
  background: rgba(255, 252, 247, 0.88);
  box-shadow: 0 16px 28px rgba(30, 42, 39, 0.07);
}

.message-row.user .message-bubble {
  background: linear-gradient(135deg, rgba(253, 237, 223, 0.96), rgba(255, 247, 239, 0.96));
}

.message-bubble p {
  margin: 0;
  white-space: pre-wrap;
}

.card-stack {
  display: grid;
  gap: 0.85rem;
  margin-top: 0.85rem;
}

.attachment-stack {
  display: grid;
  gap: 0.65rem;
  margin-top: 0.85rem;
}

.message-attachment {
  width: min(100%, 20rem);
  margin: 0;
  padding: 0.55rem;
  border: 1px solid rgba(47, 93, 80, 0.12);
  border-radius: 1rem;
  background: rgba(255, 252, 247, 0.92);
  box-shadow: 0 14px 26px rgba(30, 42, 39, 0.07);
}

.message-row.user .message-attachment {
  margin-left: auto;
}

.message-attachment img {
  display: block;
  width: 100%;
  border-radius: 0.75rem;
}

.message-attachment figcaption {
  margin-top: 0.45rem;
  color: var(--color-text-soft);
  font-size: 0.78rem;
}

.message-time {
  display: inline-block;
  margin-top: 0.45rem;
  color: var(--color-text-soft);
  font-size: 0.76rem;
}

.message-row.user .message-time {
  width: 100%;
  text-align: right;
}

@media (max-width: 640px) {
  .message-row {
    gap: 0.7rem;
  }

  .avatar {
    width: 2rem;
    height: 2rem;
    border-radius: 0.85rem;
    font-size: 0.72rem;
  }

  .message-bubble {
    padding: 0.92rem 0.95rem;
  }
}
</style>
