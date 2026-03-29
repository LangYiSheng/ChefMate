<script setup lang="ts">
import { computed, nextTick, ref, useTemplateRef, watch } from 'vue'

import AppSidebar from './components/AppSidebar.vue'
import ChatHeader from './components/ChatHeader.vue'
import ComposerPanel from './components/ComposerPanel.vue'
import MessageBubble from './components/MessageBubble.vue'
import {
  buildMockConversations,
  recipeOverview,
  sidebarShortcuts,
  userProfile,
} from './data/mockChat'
import type { ChatMessage, ConversationRecord, ConversationStage, MessageCard } from './types/chat'

const stageLabelMap: Record<ConversationStage, string> = {
  idea: '想法确认',
  planning: '菜品决策',
  shopping: '备料检查',
  cooking: '烹饪进行中',
}

const conversations = ref<ConversationRecord[]>(buildMockConversations())
const activeConversationId = ref(conversations.value[0]?.id ?? '')
const sidebarOpen = ref(false)
const typingConversationId = ref<string | null>(null)
const pendingResponseTimer = ref<number | null>(null)
const messageViewport = useTemplateRef<HTMLDivElement>('messageViewport')
let newConversationIndex = 1

const activeConversation = computed(
  () => conversations.value.find((conversation) => conversation.id === activeConversationId.value) ?? null,
)

const activeStageLabel = computed(() => {
  if (!activeConversation.value) {
    return ''
  }

  return stageLabelMap[activeConversation.value.stage]
})

const activeSuggestions = computed(() => activeConversation.value?.quickPrompts ?? [])

const isTyping = computed(
  () => activeConversation.value !== null && typingConversationId.value === activeConversation.value.id,
)

const isComposerDisabled = computed(() => isTyping.value)

watch(
  activeConversationId,
  async () => {
    await nextTick()
    scrollToBottom('smooth')
  },
  { immediate: true },
)

watch(
  () => activeConversation.value?.messages.length ?? 0,
  async () => {
    await nextTick()
    scrollToBottom('smooth')
  },
)

function scrollToBottom(behavior: ScrollBehavior) {
  if (!messageViewport.value) {
    return
  }

  messageViewport.value.scrollTo({
    top: messageViewport.value.scrollHeight,
    behavior,
  })
}

function formatNow() {
  const now = new Date()
  return now.toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit',
  })
}

function openSidebar() {
  sidebarOpen.value = true
}

function closeSidebar() {
  sidebarOpen.value = false
}

function selectConversation(conversationId: string) {
  activeConversationId.value = conversationId
  closeSidebar()
}

function selectShortcut(shortcutId: string) {
  if (shortcutId === 'recipes') {
    const planningConversation = conversations.value.find(
      (conversation) => conversation.stage === 'planning',
    )

    if (planningConversation) {
      activeConversationId.value = planningConversation.id
    }
  }

  if (shortcutId === 'history') {
    activeConversationId.value = conversations.value[0]?.id ?? activeConversationId.value
  }

  closeSidebar()
}

function startNewConversation() {
  const conversation: ConversationRecord = {
    id: `conversation-new-${newConversationIndex}`,
    title: `新的做饭任务 ${newConversationIndex}`,
    preview: '想吃点什么？我可以先帮你做一轮定向推荐。',
    updatedAt: '刚刚',
    stage: 'idea',
    intentLabel: '新会话',
    taskSummary: '等待确认今晚做什么，以及可接受的时长和口味偏好。',
    quickPrompts: ['20 分钟内搞定晚饭', '冰箱里有鸡蛋和番茄', '想吃清淡一点'],
    messages: [
      {
        id: `conversation-new-${newConversationIndex}-assistant-1`,
        role: 'assistant',
        content:
          '我们可以直接从需求开始。我已经把页面按“推荐菜品、检查食材、进入烹饪”这条主线留好了，后面接 API 时只需要替换数据源。',
        createdAt: formatNow(),
      },
    ],
  }

  newConversationIndex += 1
  conversations.value.unshift(conversation)
  activeConversationId.value = conversation.id
  closeSidebar()
}

function createAssistantMessage(
  content: string,
  cards: MessageCard[],
  createdAt: string,
): ChatMessage {
  return {
    id: `assistant-${Date.now()}`,
    role: 'assistant',
    content,
    createdAt,
    cards,
  }
}

function buildRecommendationCard(): MessageCard {
  return {
    type: 'recipe-recommendations',
    title: '今晚更适合你的三个方向',
    summary: '按“省时间、家常稳妥、低负担”三个维度给你一个首轮候选集。',
    recipes: [
      {
        id: 'dry-pot-cauliflower',
        name: '干锅花菜鸡腿肉',
        duration: '25 分钟',
        difficulty: '轻松上手',
        calories: '520 kcal / 2 人份',
        fitReason: '鸡腿肉更稳，锅里只需要一次爆香就能出层次。',
        highlights: ['下饭感强', '一锅完成', '适合工作日晚餐'],
      },
      {
        id: 'tomato-egg-noodles',
        name: '番茄滑蛋汤面',
        duration: '15 分钟',
        difficulty: '零失败',
        calories: '430 kcal / 1 人份',
        fitReason: '如果你想要更快上桌，这道最适合直接推进到烹饪阶段。',
        highlights: ['食材门槛低', '可按口味增减酸度', '适合夜宵'],
      },
      {
        id: 'lemon-shrimp',
        name: '柠檬黑胡椒虾仁',
        duration: '18 分钟',
        difficulty: '需要一点火候控制',
        calories: '360 kcal / 2 人份',
        fitReason: '更偏清爽路线，适合想吃轻一点但还要保留香气的时候。',
        highlights: ['高蛋白', '锅气短平快', '卖相好'],
      },
    ],
  }
}

function buildPantryCard(): MessageCard {
  return {
    type: 'pantry-status',
    title: '备料检查进度',
    summary: '系统会优先判断是否能直接开做，缺的部分再转成补买建议。',
    completion: 0.72,
    checklist: [
      {
        ingredient: '鸡腿肉',
        amount: '300g',
        status: 'ready',
        note: '冷藏可直接处理，建议切小块更容易入味。',
      },
      {
        ingredient: '花菜',
        amount: '1 颗',
        status: 'ready',
        note: '先掰小朵再泡盐水，后续翻炒更省时。',
      },
      {
        ingredient: '青椒',
        amount: '2 个',
        status: 'missing',
        note: '可以补买，也可以用洋葱替代一部分香味层次。',
      },
      {
        ingredient: '豆瓣酱',
        amount: '1 勺',
        status: 'low',
        note: '家里还有少量时建议减少盐量，避免过咸。',
      },
    ],
    actions: ['先按现有食材做简化版', '生成补买清单', '换一道更省料的菜'],
  }
}

function buildCookingGuideCard(): MessageCard {
  return {
    type: 'cooking-guide',
    title: '当前烹饪步骤',
    summary: '前端已经预留计时和步骤高亮区域，后面可以直接对接流式指导。',
    currentStep: 2,
    totalSteps: 5,
    timers: [
      {
        label: '腌制提醒',
        duration: '08:00',
      },
      {
        label: '焖煮提醒',
        duration: '03:30',
      },
    ],
    steps: [
      {
        title: '处理鸡腿肉并腌制',
        detail: '加入少量料酒、生抽和黑胡椒，抓匀后静置 8 分钟。',
        duration: '8 分钟',
        status: 'done',
      },
      {
        title: '爆香蒜末与豆瓣酱',
        detail: '油热后先下蒜末，再下豆瓣酱，小火把香味和红油慢慢炒出来。',
        duration: '1 分钟',
        status: 'current',
      },
      {
        title: '下鸡腿肉翻炒上色',
        detail: '转中火快速翻炒，表面微焦时把花菜一起下锅。',
        duration: '3 分钟',
        status: 'upcoming',
      },
      {
        title: '加少量清水焖煮',
        detail: '保持锅中有薄薄一层汤汁，让花菜更快熟透。',
        duration: '3 分钟',
        status: 'upcoming',
      },
      {
        title: '收汁并加入青椒',
        detail: '最后 30 秒再下青椒，口感会更脆，颜色也更亮。',
        duration: '1 分钟',
        status: 'upcoming',
      },
    ],
  }
}

function buildAssistantResponse(
  prompt: string,
  conversation: ConversationRecord,
): {
  content: string
  cards: MessageCard[]
  nextStage: ConversationStage
  taskSummary: string
  quickPrompts: string[]
} {
  const normalizedPrompt = prompt.toLowerCase()
  const includesRecommendationIntent =
    /推荐|吃什么|晚饭|菜谱|鸡翅|鸡腿|想吃/.test(prompt) || conversation.stage === 'idea'
  const includesPantryIntent =
    /食材|冰箱|备料|缺什么|有啥|买菜/.test(prompt) || conversation.stage === 'planning'
  const includesCookingIntent =
    /开始做|步骤|下锅|烹饪|开火|怎么做/.test(prompt) || conversation.stage === 'shopping'

  if (includesRecommendationIntent && !includesCookingIntent && !includesPantryIntent) {
    return {
      content:
        '我先把候选菜缩成三个方向，右侧卡片里每个方案都带了时长、热量和匹配理由，后续接接口后也可以直接复用这套展示结构。',
      cards: [buildRecommendationCard()],
      nextStage: 'planning',
      taskSummary: '已进入候选菜筛选阶段，等待用户在推荐集合里确认目标菜品。',
      quickPrompts: ['就做第一个', '按清淡一点再改一版', '告诉我需要准备什么'],
    }
  }

  if (includesPantryIntent && !includesCookingIntent) {
    return {
      content:
        '我按“齐备、缺失、库存不足”三个状态整理了一遍，后端以后只要返回结构化字段，这里就能直接驱动缺料判断和补买建议。',
      cards: [buildPantryCard()],
      nextStage: 'shopping',
      taskSummary: '正在比对现有食材和目标菜谱要求，并生成补买或换菜建议。',
      quickPrompts: ['生成补买清单', '按现有食材简化一下', '我想直接开始做'],
    }
  }

  if (includesCookingIntent || normalizedPrompt.includes('start')) {
    return {
      content:
        '已经把步骤流切成当前、下一步和待执行三种状态，后面接流式响应时可以边返回文本边推进这张卡片，不需要改页面结构。',
      cards: [buildCookingGuideCard()],
      nextStage: 'cooking',
      taskSummary: '已进入烹饪指导阶段，支持继续追问、计时提醒和步骤推进。',
      quickPrompts: ['下一步做什么', '帮我提醒焖 3 分钟', '这一步火候要多大'],
    }
  }

  return {
    content:
      '我先把这条需求记进当前任务里了。这个页面现在已经按“会话元数据 + 消息流 + 结构化卡片”分层，后面无论走普通问答还是任务型消息都能接住。',
    cards: [],
    nextStage: conversation.stage,
    taskSummary: conversation.taskSummary,
    quickPrompts: conversation.quickPrompts,
  }
}

function sendMessage(prompt: string) {
  const conversation = activeConversation.value
  if (!conversation) {
    return
  }

  conversation.messages.push({
    id: `user-${Date.now()}`,
    role: 'user',
    content: prompt,
    createdAt: formatNow(),
  })
  conversation.updatedAt = '刚刚'
  conversation.preview = prompt
  typingConversationId.value = conversation.id

  if (pendingResponseTimer.value !== null) {
    window.clearTimeout(pendingResponseTimer.value)
  }

  const responseConversationId = conversation.id
  const response = buildAssistantResponse(prompt, conversation)

  pendingResponseTimer.value = window.setTimeout(() => {
    const targetConversation = conversations.value.find(
      (currentConversation) => currentConversation.id === responseConversationId,
    )

    if (!targetConversation) {
      return
    }

    targetConversation.messages.push(
      createAssistantMessage(response.content, response.cards, formatNow()),
    )
    targetConversation.updatedAt = '刚刚'
    targetConversation.preview = response.content
    targetConversation.stage = response.nextStage
    targetConversation.taskSummary = response.taskSummary
    targetConversation.quickPrompts = response.quickPrompts

    if (typingConversationId.value === responseConversationId) {
      typingConversationId.value = null
    }

    pendingResponseTimer.value = null
  }, 650)
}
</script>

<template>
  <div class="app-shell">
    <AppSidebar
      :conversations="conversations"
      :active-conversation-id="activeConversationId"
      :is-open="sidebarOpen"
      :recipe-overview="recipeOverview"
      :shortcuts="sidebarShortcuts"
      :user-profile="userProfile"
      @close="closeSidebar"
      @new-conversation="startNewConversation"
      @select-conversation="selectConversation"
      @select-shortcut="selectShortcut"
    />

    <main v-if="activeConversation" class="workspace">
      <ChatHeader
        :conversation="activeConversation"
        :stage-label="activeStageLabel"
        @toggle-sidebar="openSidebar"
      />

      <section ref="messageViewport" class="message-viewport">
        <div class="message-stream">
          <MessageBubble
            v-for="message in activeConversation.messages"
            :key="message.id"
            :message="message"
          />

          <div v-if="isTyping" class="typing-row">
            <div class="typing-bubble">
              <span></span>
              <span></span>
              <span></span>
            </div>
          </div>
        </div>
      </section>

      <ComposerPanel
        :disabled="isComposerDisabled"
        :suggestions="activeSuggestions"
        @send="sendMessage"
      />
    </main>
  </div>
</template>

<style scoped>
.app-shell {
  display: flex;
  min-height: 100vh;
  background:
    radial-gradient(circle at top left, rgba(229, 143, 91, 0.18), transparent 24rem),
    radial-gradient(circle at right, rgba(54, 106, 94, 0.12), transparent 26rem),
    var(--color-bg);
}

.workspace {
  display: grid;
  flex: 1;
  min-width: 0;
  min-height: 100vh;
  grid-template-rows: auto minmax(0, 1fr) auto;
}

.message-viewport {
  min-height: 0;
  padding: 0 2rem 1.4rem;
  overflow-y: auto;
}

.message-stream {
  width: min(100%, 56rem);
  margin: 0 auto;
  padding: 1.5rem 0 2rem;
}

.typing-row {
  display: flex;
  justify-content: flex-start;
}

.typing-bubble {
  display: inline-flex;
  gap: 0.35rem;
  align-items: center;
  padding: 0.8rem 1rem;
  border: 1px solid rgba(47, 93, 80, 0.14);
  border-radius: 1rem;
  background: rgba(255, 252, 247, 0.92);
  box-shadow: 0 18px 30px rgba(33, 47, 43, 0.08);
}

.typing-bubble span {
  width: 0.45rem;
  height: 0.45rem;
  border-radius: 999px;
  background: var(--color-accent);
  animation: pulse 1.1s infinite ease-in-out;
}

.typing-bubble span:nth-child(2) {
  animation-delay: 0.15s;
}

.typing-bubble span:nth-child(3) {
  animation-delay: 0.3s;
}

@keyframes pulse {
  0%,
  80%,
  100% {
    transform: translateY(0);
    opacity: 0.38;
  }

  40% {
    transform: translateY(-0.2rem);
    opacity: 1;
  }
}

@media (max-width: 960px) {
  .message-viewport {
    padding: 0 1rem 1rem;
  }

  .message-stream {
    padding-top: 1rem;
  }
}
</style>
