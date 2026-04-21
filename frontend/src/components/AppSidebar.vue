<script setup lang="ts">
import type {
  ConversationRecord,
  ConversationTimerSlot,
  NavShortcut,
  UserProfileSummary,
} from '../types/chat'

const props = defineProps<{
  activeConversationId: string
  bulkDeleteDisabled: boolean
  conversations: ConversationRecord[]
  conversationTimers: Record<string, ConversationTimerSlot>
  isManagingConversations: boolean
  isOpen: boolean
  selectedConversationIds: string[]
  shortcuts: NavShortcut[]
  userProfile: UserProfileSummary
}>()

const emit = defineEmits<{
  requestBulkDelete: []
  close: []
  newConversation: []
  openProfile: []
  selectConversation: [conversationId: string]
  selectShortcut: [shortcutId: string]
  toggleConversationManageMode: []
  toggleConversationSelection: [conversationId: string]
}>()

const stageLabelMap: Record<ConversationRecord['stage'], string> = {
  idea: '闲聊',
  planning: '推荐中',
  shopping: '备料中',
  cooking: '烹饪中',
}

function conversationStageLabel(conversation: ConversationRecord) {
  const stageLabel = stageLabelMap[conversation.stage]

  if (conversation.currentRecipe) {
    return `${stageLabel} · ${conversation.currentRecipe}`
  }

  return stageLabel
}

function conversationHeadline(conversation: ConversationRecord) {
  return conversation.title
}

function conversationMeta(conversation: ConversationRecord) {
  const timerSlot = props.conversationTimers[conversation.id]
  const stageLabel = conversationStageLabel(conversation)

  if (timerSlot?.status === 'running' && timerSlot.remainingSeconds > 0) {
    return `${stageLabel} · 正在倒计时`
  }

  return stageLabel
}

function isConversationSelected(conversationId: string) {
  return props.selectedConversationIds.includes(conversationId)
}

function handleConversationClick(conversationId: string) {
  if (props.isManagingConversations) {
    emit('toggleConversationSelection', conversationId)
    return
  }

  emit('selectConversation', conversationId)
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
          <button
            v-if="conversations.length"
            class="section-action"
            type="button"
            @click="emit('toggleConversationManageMode')"
          >
            {{ isManagingConversations ? '完成' : '管理' }}
          </button>
        </div>

        <div class="conversation-list hover-scroll">
          <button
            v-for="conversation in conversations"
            :key="conversation.id"
            class="conversation-item"
            :class="{
              active: conversation.id === activeConversationId,
              selected: isConversationSelected(conversation.id),
              'is-managing': isManagingConversations,
            }"
            type="button"
            @click="handleConversationClick(conversation.id)"
          >
            <span
              v-if="isManagingConversations"
              class="conversation-checkbox"
              :class="{ checked: isConversationSelected(conversation.id) }"
              aria-hidden="true"
            >
              <span></span>
            </span>
            <span class="conversation-copy">
              <strong>{{ conversationHeadline(conversation) }}</strong>
              <small>{{ conversationMeta(conversation) }}</small>
            </span>
          </button>
        </div>

        <div v-if="isManagingConversations" class="bulk-delete-bar">
          <span>已选 {{ selectedConversationIds.length }} 个</span>
          <button
            type="button"
            :disabled="!selectedConversationIds.length || bulkDeleteDisabled"
            @click="emit('requestBulkDelete')"
          >
            删除
          </button>
        </div>
      </section>

      <button class="profile-card" type="button" @click="emit('openProfile')">
        <div class="profile-main">
          <div class="profile-avatar">{{ userProfile.name.slice(0, 1) }}</div>
          <div>
            <strong>{{ userProfile.name }}</strong>
            <p>@{{ userProfile.account }}</p>
          </div>
        </div>
        <span class="profile-overlay">点击设置个人信息</span>
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
  line-height: 1.4;
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

.section-action {
  padding: 0.35rem 0.6rem;
  border-radius: 999px;
  background: rgba(47, 93, 80, 0.08);
  color: var(--color-accent);
  font-size: 0.82rem;
  font-weight: 700;
  cursor: pointer;
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
  display: flex;
  gap: 0.7rem;
  align-items: center;
  background: rgba(255, 255, 255, 0.42);
}

.conversation-item.is-managing {
  padding-left: 0.8rem;
}

.conversation-item.active {
  border-color: rgba(47, 93, 80, 0.22);
  background:
    linear-gradient(135deg, rgba(255, 255, 255, 0.88), rgba(241, 246, 243, 0.78)),
    rgba(255, 255, 255, 0.42);
}

.conversation-item.selected {
  border-color: rgba(229, 143, 91, 0.34);
  background: rgba(255, 247, 235, 0.86);
}

.conversation-item:hover,
.shortcut-item:hover {
  transform: translateY(-1px);
  border-color: rgba(47, 93, 80, 0.18);
}

.conversation-checkbox {
  display: inline-flex;
  flex: 0 0 auto;
  align-items: center;
  justify-content: center;
  width: 1.15rem;
  height: 1.15rem;
  border: 1px solid rgba(47, 93, 80, 0.28);
  border-radius: 0.35rem;
  background: rgba(255, 255, 255, 0.76);
}

.conversation-checkbox span {
  width: 0.52rem;
  height: 0.52rem;
  border-radius: 0.18rem;
  background: transparent;
  transition: background 160ms ease;
}

.conversation-checkbox.checked {
  border-color: rgba(47, 93, 80, 0.68);
}

.conversation-checkbox.checked span {
  background: var(--color-accent);
}

.conversation-copy {
  min-width: 0;
}

.conversation-item small {
  display: block;
  margin-top: 0.32rem;
  color: var(--color-accent);
  font-size: 0.8rem;
  line-height: 1.45;
}

.bulk-delete-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  margin-top: 0.8rem;
  padding-top: 0.8rem;
  border-top: 1px solid rgba(47, 93, 80, 0.1);
  color: var(--color-text-soft);
  font-size: 0.86rem;
}

.bulk-delete-bar button {
  min-width: 4.5rem;
  padding: 0.55rem 0.8rem;
  border-radius: 999px;
  background: rgba(166, 61, 49, 0.1);
  color: #a63d31;
  font-weight: 700;
  cursor: pointer;
}

.bulk-delete-bar button:disabled {
  cursor: not-allowed;
  opacity: 0.48;
}

.profile-card {
  position: relative;
  overflow: hidden;
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

.profile-overlay {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: flex-start;
  padding: 1rem 1.1rem;
  background: rgba(17, 17, 17, 0.7);
  color: #fffaf3;
  font-size: 1.02rem;
  font-weight: 700;
  text-align: left;
  line-height: 1.4;
  opacity: 0;
  transition: opacity 180ms ease;
  backdrop-filter: blur(6px);
}

.profile-card:hover .profile-overlay,
.profile-card:focus-visible .profile-overlay {
  opacity: 1;
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
