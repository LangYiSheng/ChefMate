<script setup lang="ts">
import type {
  ConversationRecord,
  NavShortcut,
  UserProfileSummary,
} from '../types/chat'

defineProps<{
  activeConversationId: string
  conversations: ConversationRecord[]
  isOpen: boolean
  shortcuts: NavShortcut[]
  userProfile: UserProfileSummary
}>()

const emit = defineEmits<{
  close: []
  newConversation: []
  openProfile: []
  selectConversation: [conversationId: string]
  selectShortcut: [shortcutId: string]
}>()

function conversationStageLabel(conversation: ConversationRecord) {
  if (conversation.currentRecipe) {
    return `${conversation.intentLabel} · ${conversation.currentRecipe}`
  }

  return conversation.intentLabel
}
</script>

<template>
  <div class="sidebar-shell" :class="{ 'is-open': isOpen }">
    <button class="sidebar-backdrop" type="button" aria-label="关闭侧边栏" @click="emit('close')" />

    <aside class="sidebar">
      <div class="sidebar-brand">
        <div>
          <h1>ChefMate</h1>
          <p class="subtitle">你的智能烹饪伙伴</p>
        </div>

        <button class="mobile-close" type="button" aria-label="关闭侧边栏" @click="emit('close')">
          ×
        </button>
      </div>

      <button class="new-chat-button" type="button" @click="emit('newConversation')">
        <span class="new-chat-icon">+</span>
        <span>
          <strong>开启一个新对话</strong>
          <small>一起做一道菜，或者聊聊天</small>
        </span>
      </button>

      <section class="shortcut-section">
        <button
          v-for="shortcut in shortcuts"
          :key="shortcut.id"
          class="shortcut-item"
          type="button"
          @click="emit('selectShortcut', shortcut.id)"
        >
          <span>
            <strong>{{ shortcut.label }}</strong>
            <small>{{ shortcut.caption }}</small>
          </span>
        </button>
      </section>

      <section class="conversation-section">
        <div class="section-header">
          <h2>对话列表</h2>
        </div>

        <div class="conversation-list">
          <button
            v-for="conversation in conversations"
            :key="conversation.id"
            class="conversation-item"
            :class="{ active: conversation.id === activeConversationId }"
            type="button"
            @click="emit('selectConversation', conversation.id)"
          >
            <strong>{{ conversation.statusText }}</strong>
            <small>{{ conversationStageLabel(conversation) }}</small>
          </button>
        </div>
      </section>

      <button class="profile-card" type="button" @click="emit('openProfile')">
        <div class="profile-main">
          <div class="profile-avatar">{{ userProfile.name.slice(0, 1) }}</div>
          <div>
            <strong>{{ userProfile.name }}</strong>
            <p>{{ userProfile.level }}</p>
          </div>
        </div>
      </button>
    </aside>
  </div>
</template>

<style scoped>
.sidebar-shell {
  position: relative;
}

.sidebar-backdrop {
  position: fixed;
  inset: 0;
  z-index: 20;
  display: none;
  background: rgba(25, 33, 31, 0.42);
}

.sidebar {
  position: relative;
  z-index: 21;
  display: flex;
  overflow: hidden;
  flex-direction: column;
  width: 21rem;
  height: 100vh;
  min-height: 100vh;
  padding: 1.25rem;
  border-right: 1px solid rgba(47, 93, 80, 0.1);
  background:
    linear-gradient(180deg, rgba(255, 251, 245, 0.96), rgba(247, 241, 232, 0.96)),
    var(--color-surface);
  backdrop-filter: blur(18px);
}

.sidebar-brand {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
  margin-bottom: 1.25rem;
}

.sidebar-brand h1 {
  margin: 0;
  font-size: 1.72rem;
  line-height: 1.1;
}

.subtitle {
  margin: 0.35rem 0 0;
  color: var(--color-text-soft);
  font-size: 0.92rem;
}

.mobile-close {
  display: none;
  width: 2.25rem;
  height: 2.25rem;
  border-radius: 999px;
  font-size: 1.25rem;
  background: rgba(47, 93, 80, 0.08);
}

.new-chat-button {
  display: flex;
  gap: 0.9rem;
  align-items: center;
  padding: 1rem 1.05rem;
  border: 1px solid rgba(47, 93, 80, 0.18);
  border-radius: 1.25rem;
  background: linear-gradient(135deg, rgba(47, 93, 80, 0.96), rgba(32, 57, 49, 0.96));
  color: #fef7ef;
  text-align: left;
  box-shadow: 0 20px 36px rgba(28, 54, 47, 0.22);
  cursor: pointer;
}

.new-chat-button strong,
.shortcut-item strong,
.conversation-item strong,
.profile-card strong {
  display: block;
}

.new-chat-button small,
.shortcut-item small,
.conversation-item small,
.profile-card p {
  color: inherit;
  opacity: 0.78;
}

.new-chat-icon {
  display: inline-flex;
  flex: 0 0 auto;
  align-items: center;
  justify-content: center;
  width: 2.1rem;
  height: 2.1rem;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.14);
  font-size: 1.25rem;
}

.shortcut-section,
.conversation-section {
  margin-top: 1.15rem;
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 0.85rem;
}

.section-header h2 {
  margin: 0;
  font-size: 0.98rem;
}

.shortcut-item,
.conversation-item {
  width: 100%;
  padding: 0.9rem 0.95rem;
  border: 1px solid transparent;
  border-radius: 1rem;
  color: var(--color-text);
  text-align: left;
  cursor: pointer;
  transition:
    transform 180ms ease,
    border-color 180ms ease,
    background 180ms ease;
}

.shortcut-item {
  display: flex;
  justify-content: space-between;
  margin-bottom: 0.35rem;
  background: rgba(255, 255, 255, 0.44);
}

.conversation-section {
  display: flex;
  min-height: 0;
  flex: 1;
  flex-direction: column;
}

.conversation-list {
  display: grid;
  gap: 0.65rem;
  min-height: 0;
  overflow-y: auto;
  padding-right: 0.2rem;
}

.conversation-item {
  background: rgba(255, 255, 255, 0.42);
}

.conversation-item.active {
  border-color: rgba(47, 93, 80, 0.22);
  background:
    linear-gradient(135deg, rgba(255, 255, 255, 0.88), rgba(241, 246, 243, 0.78)),
    rgba(255, 255, 255, 0.42);
  box-shadow: 0 18px 30px rgba(29, 43, 39, 0.08);
}

.conversation-item:hover,
.shortcut-item:hover {
  transform: translateY(-1px);
  border-color: rgba(47, 93, 80, 0.18);
}

.conversation-item small {
  display: block;
  margin-top: 0.32rem;
  color: var(--color-accent);
  font-size: 0.8rem;
}

.profile-card {
  margin-top: 1rem;
  padding: 1rem;
  border: 1px solid var(--color-border);
  border-radius: 1.15rem;
  background: rgba(255, 251, 245, 0.86);
  text-align: left;
  cursor: pointer;
}

.profile-main {
  display: flex;
  gap: 0.85rem;
  align-items: center;
}

.profile-avatar {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 2.5rem;
  height: 2.5rem;
  border-radius: 999px;
  background: rgba(47, 93, 80, 0.12);
  color: var(--color-accent);
  font-weight: 700;
}

.profile-main p,
.profile-card p {
  margin: 0.18rem 0 0;
  color: var(--color-text-soft);
  font-size: 0.88rem;
}

@media (max-width: 960px) {
  .sidebar-shell {
    position: static;
  }

  .sidebar-backdrop {
    display: block;
    opacity: 0;
    pointer-events: none;
    transition: opacity 220ms ease;
  }

  .sidebar {
    position: fixed;
    top: 0;
    left: 0;
    width: min(88vw, 22rem);
    transform: translateX(-102%);
    transition: transform 260ms ease;
  }

  .mobile-close {
    display: inline-flex;
    align-items: center;
    justify-content: center;
  }

  .sidebar-shell.is-open .sidebar-backdrop {
    opacity: 1;
    pointer-events: auto;
  }

  .sidebar-shell.is-open .sidebar {
    transform: translateX(0);
  }
}
</style>
