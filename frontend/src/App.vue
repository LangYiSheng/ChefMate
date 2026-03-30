<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, ref, useTemplateRef, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import AppSidebar from './components/AppSidebar.vue'
import ActionModal from './components/ActionModal.vue'
import AuthPage from './components/AuthPage.vue'
import ChatHeader from './components/ChatHeader.vue'
import ComposerPanel from './components/ComposerPanel.vue'
import MessageBubble from './components/MessageBubble.vue'
import OverlayDialog from './components/OverlayDialog.vue'
import ProfileSettingsPanel from './components/ProfileSettingsPanel.vue'
import RecipeLibraryPanel from './components/RecipeLibraryPanel.vue'
import WorkspaceOnboardingModal from './components/WorkspaceOnboardingModal.vue'
import { buildMockConversations, sidebarShortcuts, userProfile } from './data/mockChat'
import { mockRecipes } from './data/mockRecipes'
import { tagCatalog } from './data/tagCatalog'
import { clearAuthSession, getAuthSession, updateAuthSession } from './state/auth'
import type {
  ChatAttachment,
  ChatMessage,
  ConversationRecord,
  ConversationStage,
  ConversationTimerSlot,
  MessageCard,
  RecipeRecord,
  TimerRequest,
  UserProfileSummary,
} from './types/chat'

const stageLabelMap: Record<ConversationStage, string> = {
  idea: '闲聊',
  planning: '推荐中',
  shopping: '备料中',
  cooking: '烹饪中',
}

const draftConversationId = 'new'
const draftQuickPrompts = ['今晚想吃点热乎的', '冰箱里有鸡蛋和番茄', '想做一道 20 分钟内的菜']
const draftGreetingTemplates = {
  morning: ['早上好，{name}。', '新的一天开始啦，{name}。'],
  noon: ['中午好，{name}。', '午安，{name}。'],
  afternoon: ['下午好，{name}。', '嗨，{name}。'],
  evening: ['晚上好，{name}。', '欢迎回来，{name}。'],
} as const

const route = useRoute()
const router = useRouter()
const conversations = ref<ConversationRecord[]>(normalizeConversationCards(buildMockConversations()))
const profile = ref<UserProfileSummary>(structuredClone(userProfile))
const activeConversationId = ref(conversations.value[0]?.id ?? '')
const sidebarOpen = ref(false)
const profilePanelOpen = ref(false)
const workspaceOnboardingOpen = ref(false)
const typingConversationId = ref<string | null>(null)
const draftGreeting = ref('')
const pendingResponseTimer = ref<number | null>(null)
const conversationTimers = ref<Record<string, ConversationTimerSlot>>({})
const pendingTimerReplacement = ref<TimerRequest | null>(null)
const timerNotice = ref<{
  conversationId: string
  text: string
  tone: 'info' | 'alert'
  needsConfirm: boolean
} | null>(null)
const messageViewport = useTemplateRef<HTMLDivElement>('messageViewport')
let newConversationIndex = 1
let countdownTicker: number | null = null
let timerNoticeTimeout: number | null = null

function syncProfileFromAuthSession() {
  const authSession = getAuthSession()
  if (!authSession) {
    workspaceOnboardingOpen.value = false
    return
  }

  profile.value.name = authSession.username
  profile.value.account = authSession.username
  profile.value.email = authSession.email ?? profile.value.email
  refreshDraftGreeting()

  if (
    route.name &&
    route.name !== 'auth-login' &&
    route.name !== 'auth-register' &&
    !authSession.hasCompletedWorkspaceOnboarding
  ) {
    workspaceOnboardingOpen.value = true
  }
}

function refreshDraftGreeting() {
  const displayName = profile.value.name?.trim() || '朋友'
  const hour = new Date().getHours()
  const period =
    hour < 11 ? 'morning' : hour < 14 ? 'noon' : hour < 18 ? 'afternoon' : 'evening'
  const templates = draftGreetingTemplates[period]
  const randomTemplate =
    templates[Math.floor(Math.random() * templates.length)] ?? '欢迎回来，{name}。'

  draftGreeting.value = randomTemplate.replace('{name}', displayName)
}

const activeConversation = computed(
  () => conversations.value.find((conversation) => conversation.id === activeConversationId.value) ?? null,
)

const routeConversationId = computed(() => {
  if (route.name !== 'chat') {
    return null
  }

  const conversationIdParam = route.params.conversationId
  return Array.isArray(conversationIdParam) ? conversationIdParam[0] ?? null : conversationIdParam ?? null
})

const isDraftConversationRoute = computed(
  () => route.name === 'chat' && routeConversationId.value === draftConversationId,
)

const visibleConversation = computed<ConversationRecord | null>(() => {
  if (activeConversation.value) {
    return activeConversation.value
  }

  if (!isDraftConversationRoute.value) {
    return null
  }

  return {
    id: draftConversationId,
    title: '新的对话',
    statusText: '等你说一句想吃什么',
    preview: '',
    updatedAt: '刚刚',
    stage: 'idea',
    intentLabel: '闲聊',
    taskSummary: '',
    quickPrompts: draftQuickPrompts,
    messages: [],
  }
})

const activeStageLabel = computed(() => {
  if (!visibleConversation.value) {
    return ''
  }

  if (isDraftConversationRoute.value && !activeConversation.value) {
    return '新对话'
  }

  return stageLabelMap[visibleConversation.value.stage]
})

const activeSuggestions = computed(
  () => activeConversation.value?.quickPrompts ?? (isDraftConversationRoute.value ? draftQuickPrompts : []),
)
const isAuthRoute = computed(
  () => route.name === 'auth-login' || route.name === 'auth-register',
)
const authMode = computed<'login' | 'register'>(() => (route.name === 'auth-register' ? 'register' : 'login'))
const isRecipeRoute = computed(
  () => route.name === 'recipes' || route.name === 'recipe-detail',
)
const activeRecipeId = computed(() => {
  if (route.name !== 'recipe-detail') {
    return null
  }

  const recipeIdParam = route.params.recipeId
  const recipeId = Number(Array.isArray(recipeIdParam) ? recipeIdParam[0] : recipeIdParam)

  return Number.isFinite(recipeId) ? recipeId : null
})

const isTyping = computed(
  () => activeConversation.value !== null && typingConversationId.value === activeConversation.value.id,
)

const isComposerDisabled = computed(() => isTyping.value)
const activeTimerSlot = computed(() => {
  if (!activeConversationId.value) {
    return null
  }

  return conversationTimers.value[activeConversationId.value] ?? null
})
const activeTimerNotice = computed(() => {
  if (!activeConversationId.value || timerNotice.value?.conversationId !== activeConversationId.value) {
    return null
  }

  return timerNotice.value
})

watch(
  () => route.name,
  () => {
    syncProfileFromAuthSession()
  },
  { immediate: true },
)

watch(
  activeConversationId,
  async () => {
    if (route.name === 'chat' && !isDraftConversationRoute.value) {
      if (activeConversationId.value && routeConversationId.value !== activeConversationId.value) {
        await router.replace({
          name: 'chat',
          params: { conversationId: activeConversationId.value },
        })
      }
    }

    await nextTick()
    scrollToBottom('smooth')
  },
  { immediate: true },
)

watch(
  () => [route.name, route.params.conversationId] as const,
  async ([routeName, routeConversationId]) => {
    if (routeName !== 'chat') {
      return
    }

    const normalizedConversationId = Array.isArray(routeConversationId)
      ? routeConversationId[0]
      : routeConversationId

    if (normalizedConversationId === draftConversationId) {
      activeConversationId.value = ''
      await nextTick()
      if (messageViewport.value) {
        messageViewport.value.scrollTo({ top: 0, behavior: 'auto' })
      }
      return
    }

    if (normalizedConversationId) {
      const matchedConversation = conversations.value.find(
        (conversation) => conversation.id === normalizedConversationId,
      )

      if (matchedConversation) {
        activeConversationId.value = matchedConversation.id
        return
      }
    }

    const fallbackConversationId = conversations.value[0]?.id
    if (fallbackConversationId) {
      activeConversationId.value = fallbackConversationId
      await router.replace({
        name: 'chat',
        params: { conversationId: fallbackConversationId },
      })
    }
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

watch(
  isDraftConversationRoute,
  async (isDraftRoute) => {
    if (!isDraftRoute) {
      return
    }

    refreshDraftGreeting()
    await nextTick()
    if (messageViewport.value) {
      messageViewport.value.scrollTo({ top: 0, behavior: 'auto' })
    }
  },
)

onBeforeUnmount(() => {
  if (pendingResponseTimer.value !== null) {
    window.clearTimeout(pendingResponseTimer.value)
  }

  if (countdownTicker !== null) {
    window.clearInterval(countdownTicker)
  }

  if (timerNoticeTimeout !== null) {
    window.clearTimeout(timerNoticeTimeout)
  }
})

function scrollToBottom(behavior: ScrollBehavior) {
  if (!messageViewport.value) {
    return
  }

  messageViewport.value.scrollTo({
    top: messageViewport.value.scrollHeight,
    behavior,
  })
}

function clearTimerNoticeTimeout() {
  if (timerNoticeTimeout !== null) {
    window.clearTimeout(timerNoticeTimeout)
    timerNoticeTimeout = null
  }
}

function showTimerNotice(
  conversationId: string,
  text: string,
  tone: 'info' | 'alert',
  needsConfirm = false,
) {
  clearTimerNoticeTimeout()

  timerNotice.value = {
    conversationId,
    text,
    tone,
    needsConfirm,
  }

  if (!needsConfirm) {
    timerNoticeTimeout = window.setTimeout(() => {
      if (timerNotice.value?.conversationId === conversationId && timerNotice.value.text === text) {
        timerNotice.value = null
      }
      timerNoticeTimeout = null
    }, 1100)
  }
}

function dismissTimerNotice() {
  clearTimerNoticeTimeout()
  timerNotice.value = null
}

function focusCookingGuideCard() {
  if (!messageViewport.value) {
    return
  }

  const cookingCards = messageViewport.value.querySelectorAll('.cooking-guide-card')
  const cookingCard = cookingCards[cookingCards.length - 1] as HTMLElement | undefined
  if (!cookingCard) {
    return
  }

  cookingCard.scrollIntoView({
    behavior: 'smooth',
    block: 'center',
  })

  cookingCard.classList.add('is-focused')
  window.setTimeout(() => {
    cookingCard.classList.remove('is-focused')
  }, 1400)
}

async function activateTimerConversation(conversationId: string) {
  if (activeConversationId.value !== conversationId || route.name !== 'chat') {
    activeConversationId.value = conversationId
    await router.push({ name: 'chat', params: { conversationId } })
  }

  await nextTick()
  focusCookingGuideCard()
}

function ensureCountdownTicker() {
  if (countdownTicker !== null) {
    return
  }

  countdownTicker = window.setInterval(() => {
    let hasRunningTimer = false

    Object.entries(conversationTimers.value).forEach(([conversationId, timerSlot]) => {
      if (timerSlot.status !== 'running') {
        return
      }

      hasRunningTimer = true

      if (timerSlot.remainingSeconds <= 1) {
        timerSlot.remainingSeconds = 0
        timerSlot.status = 'finished'
        showTimerNotice(conversationId, '时间到啦！', 'alert', true)
        void activateTimerConversation(conversationId)
        return
      }

      timerSlot.remainingSeconds -= 1
    })

    if (!hasRunningTimer && countdownTicker !== null) {
      window.clearInterval(countdownTicker)
      countdownTicker = null
    }
  }, 1000)
}

function stopCountdownTickerIfIdle() {
  const hasRunningTimer = Object.values(conversationTimers.value).some(
    (timerSlot) => timerSlot.status === 'running',
  )

  if (!hasRunningTimer && countdownTicker !== null) {
    window.clearInterval(countdownTicker)
    countdownTicker = null
  }
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

function openProfilePanel() {
  profilePanelOpen.value = true
  closeSidebar()
}

function closeProfilePanel() {
  profilePanelOpen.value = false
}

function completeWorkspaceOnboarding(payload: {
  name: string
  cookingPreferenceText: string
  tagSelections: UserProfileSummary['tagSelections']
  allowAutoUpdate: boolean
  autoStartStepTimer: boolean
}) {
  profile.value.name = payload.name
  profile.value.cookingPreferenceText = payload.cookingPreferenceText
  profile.value.tagSelections = payload.tagSelections
  profile.value.allowAutoUpdate = payload.allowAutoUpdate
  profile.value.autoStartStepTimer = payload.autoStartStepTimer
  workspaceOnboardingOpen.value = false
  updateAuthSession({
    hasCompletedWorkspaceOnboarding: true,
    profileCompletedAt: new Date().toISOString(),
  })
  startNewConversation()
}

function logout() {
  clearAuthSession()
  closeProfilePanel()
  workspaceOnboardingOpen.value = false
  activeConversationId.value = ''
  conversationTimers.value = {}
  pendingTimerReplacement.value = null
  timerNotice.value = null
  typingConversationId.value = null
  stopCountdownTickerIfIdle()
  void router.push({ name: 'auth-login' })
}

function selectConversation(conversationId: string) {
  activeConversationId.value = conversationId
  router.push({ name: 'chat', params: { conversationId } })
  closeSidebar()
}

function selectShortcut(shortcutId: string) {
  if (shortcutId === 'recipes') {
    router.push({ name: 'recipes' })
  }

  closeSidebar()
}

function startNewConversation() {
  activeConversationId.value = ''
  router.push({ name: 'chat', params: { conversationId: draftConversationId } })
  closeSidebar()
}

function createDraftConversation(prompt: string) {
  const conversationId = `conversation-new-${newConversationIndex}`
  const trimmedPrompt = prompt.trim()
  const promptPreview = trimmedPrompt.length > 18 ? `${trimmedPrompt.slice(0, 18)}...` : trimmedPrompt

  const conversation: ConversationRecord = {
    id: conversationId,
    title: promptPreview || `新的做饭任务 ${newConversationIndex}`,
    statusText: '正在理解你的需求',
    preview: trimmedPrompt,
    updatedAt: '刚刚',
    stage: 'idea',
    intentLabel: '闲聊',
    taskSummary: '',
    quickPrompts: draftQuickPrompts,
    messages: [],
  }

  newConversationIndex += 1
  conversations.value.unshift(conversation)
  activeConversationId.value = conversation.id
  router.replace({ name: 'chat', params: { conversationId: conversation.id } })

  return conversation
}

function normalizeConversationCards(conversationList: ConversationRecord[]) {
  conversationList.forEach((conversation) => {
    const latestCardTypes = new Set<MessageCard['type']>()

    for (let index = conversation.messages.length - 1; index >= 0; index -= 1) {
      const message = conversation.messages[index]
      if (!message.cards?.length) {
        continue
      }

      const nextCards = [...message.cards]
        .reverse()
        .filter((card) => {
          if (latestCardTypes.has(card.type)) {
            return false
          }

          latestCardTypes.add(card.type)
          return true
        })
        .reverse()

      message.cards = nextCards.length ? nextCards : undefined
    }
  })

  return conversationList
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

function formatStepDuration(seconds?: number | null) {
  if (!seconds) {
    return '跟着感觉推进'
  }

  if (seconds < 60) {
    return `${seconds} 秒`
  }

  return `${Math.round(seconds / 60)} 分钟`
}

function findRecipeByPrompt(prompt: string, currentRecipeName?: string) {
  const recipeIdMatch = prompt.match(/recipe:(\d+)/i)
  if (recipeIdMatch) {
    const recipeId = Number(recipeIdMatch[1])
    return mockRecipes.find((recipe) => recipe.id === recipeId) ?? null
  }

  if (currentRecipeName) {
    const currentRecipe = mockRecipes.find((recipe) => recipe.name === currentRecipeName)
    if (currentRecipe) {
      return currentRecipe
    }
  }

  return mockRecipes.find((recipe) => prompt.includes(recipe.name)) ?? null
}

function buildRecommendationCard(): MessageCard {
  return {
    type: 'recipe-recommendations',
    title: '今晚更适合你的三个方向',
    summary: '',
    recipes: mockRecipes.slice(0, 3).map((recipe) => ({
      recipeId: recipe.id,
      name: recipe.name,
      description: recipe.description,
      tags: recipe.tags.slice(0, 4),
      difficulty: recipe.difficulty,
      estimatedMinutes: recipe.estimatedMinutes,
      servings: recipe.servings,
      detailAction: {
        id: `detail-${recipe.id}`,
        label: '查看详情',
        message: `查看菜谱详情 recipe:${recipe.id} ${recipe.name}`,
        tone: 'ghost',
      },
      tryAction: {
        id: `try-${recipe.id}`,
        label: '想尝试',
        message: `我想尝试 recipe:${recipe.id} ${recipe.name}`,
        tone: 'primary',
      },
    })),
  }
}

function buildRecipeDetailCard(recipe: RecipeRecord): MessageCard {
  return {
    type: 'recipe-detail',
    title: `${recipe.name} 的详细做法`,
    summary: '',
    recipe,
    actions: [
      {
        id: `detail-try-${recipe.id}`,
        label: '想尝试',
        message: `我想尝试 recipe:${recipe.id} ${recipe.name}`,
        tone: 'primary',
      },
    ],
  }
}

function buildPantryCard(recipe: RecipeRecord): MessageCard {
  return {
    type: 'pantry-status',
    title: `${recipe.name} 备料检查`,
    summary: '',
    checklist: recipe.ingredients.slice(0, 6).map((ingredient, index) => ({
      id: String(ingredient.id ?? `${recipe.id}-${index + 1}`),
      ingredient: ingredient.ingredientName,
      amount: ingredient.amountText,
      status: index < 2 ? 'ready' : 'pending',
      note:
        ingredient.purpose ||
        (ingredient.isOptional ? '可选项，没有也能先开始。' : '建议先确认这一项是否备齐。'),
      isOptional: ingredient.isOptional,
    })),
    actions: [
      {
        id: `pantry-ready-${recipe.id}`,
        label: '这些都备齐了',
        message: `开始烹饪 recipe:${recipe.id} ${recipe.name}`,
        tone: 'primary',
      },
    ],
  }
}

function buildCookingGuideCard(recipe: RecipeRecord): MessageCard {
  return {
    type: 'cooking-guide',
    title: `${recipe.name} 烹饪步骤`,
    summary: '',
    currentStep: Math.min(2, recipe.steps.length),
    totalSteps: recipe.steps.length,
    steps: recipe.steps.map((step, index) => ({
      id: String(step.id ?? `${recipe.id}-step-${step.stepNo}`),
      title: step.title || `步骤 ${step.stepNo}`,
      detail: step.instruction,
      duration: formatStepDuration(step.timerSeconds),
      timerSeconds: step.timerSeconds,
      notes: step.notes,
      status: index + 1 < 2 ? 'done' : index + 1 === 2 ? 'current' : 'upcoming',
    })),
  }
}

function buildAssistantResponse(
  prompt: string,
  conversation: ConversationRecord,
): {
  content: string
  cards: MessageCard[]
  nextStage: ConversationStage
  nextIntentLabel: string
  statusText: string
  quickPrompts: string[]
  currentRecipe?: string
} {
  const normalizedPrompt = prompt.toLowerCase()
  const referencedRecipe = findRecipeByPrompt(prompt, conversation.currentRecipe)
  const includesRecommendationIntent =
    /推荐|吃什么|晚饭|菜谱|鸡翅|鸡腿|想吃/.test(prompt) || conversation.stage === 'idea'
  const includesPantryIntent =
    /食材|冰箱|备料|缺什么|有啥|买菜/.test(prompt) || conversation.stage === 'planning'
  const includesCookingIntent =
    /开始做|步骤|下锅|烹饪|开火|怎么做/.test(prompt) || conversation.stage === 'shopping'

  if (/查看菜谱详情|看看详情|详情/.test(prompt) && referencedRecipe) {
    return {
      content: `这是 ${referencedRecipe.name} 的详细做法。`,
      cards: [buildRecipeDetailCard(referencedRecipe)],
      nextStage: 'planning',
      nextIntentLabel: '推荐中',
      statusText: `正在查看 ${referencedRecipe.name} 的菜谱详情`,
      quickPrompts: ['我想试试这道', '先看备料', '换一道类似的'],
      currentRecipe: referencedRecipe.name,
    }
  }

  if ((/想尝试|查看备料|差几样|材料/.test(prompt) || includesPantryIntent) && referencedRecipe) {
    return {
      content: `先检查一下 ${referencedRecipe.name} 需要准备的材料。`,
      cards: [buildPantryCard(referencedRecipe)],
      nextStage: 'shopping',
      nextIntentLabel: '备料中',
      statusText: `${referencedRecipe.name} 的备料检查已经展开`,
      quickPrompts: ['这些都备齐了', '再看看菜谱详情', '换一道类似的'],
      currentRecipe: referencedRecipe.name,
    }
  }

  if ((/开始烹饪|继续做|下一步|开火/.test(prompt) || includesCookingIntent) && referencedRecipe) {
    return {
      content: `已经切到 ${referencedRecipe.name} 的烹饪步骤。`,
      cards: [buildCookingGuideCard(referencedRecipe)],
      nextStage: 'cooking',
      nextIntentLabel: '烹饪中',
      statusText: `${referencedRecipe.name} 正在烹饪中`,
      quickPrompts: ['下一步做什么', '这一步火候要多大', '需要计时多久'],
      currentRecipe: referencedRecipe.name,
    }
  }

  if (includesRecommendationIntent && !includesCookingIntent && !includesPantryIntent) {
    return {
      content: '给你整理了几道更适合现在做的菜。',
      cards: [buildRecommendationCard()],
      nextStage: 'planning',
      nextIntentLabel: '推荐中',
      statusText: '候选菜已经整理好了，等你拍板',
      quickPrompts: ['就做第一个', '按清淡一点再改一版', '告诉我需要准备什么'],
    }
  }

  if (includesPantryIntent && !includesCookingIntent && referencedRecipe) {
    return {
      content: '我把需要准备的材料重新整理好了。',
      cards: [buildPantryCard(referencedRecipe)],
      nextStage: 'shopping',
      nextIntentLabel: '备料中',
      statusText: `${referencedRecipe.name} 的备料检查已经展开`,
      quickPrompts: ['生成补买清单', '按现有食材简化一下', '我想直接开始做'],
      currentRecipe: referencedRecipe.name,
    }
  }

  if ((includesCookingIntent || normalizedPrompt.includes('start')) && referencedRecipe) {
    return {
      content: '已经切到烹饪步骤了。',
      cards: [buildCookingGuideCard(referencedRecipe)],
      nextStage: 'cooking',
      nextIntentLabel: '烹饪中',
      statusText: `${referencedRecipe.name} 正在烹饪中`,
      quickPrompts: ['下一步做什么', '帮我提醒焖 3 分钟', '这一步火候要多大'],
      currentRecipe: referencedRecipe.name,
    }
  }

  return {
    content: '我先把你的意思记下来了，我们可以继续往下细化要做什么。',
    cards: [],
    nextStage: conversation.stage,
    nextIntentLabel: conversation.intentLabel,
    statusText: conversation.statusText,
    quickPrompts: conversation.quickPrompts,
  }
}

function sendMessage(payload: string | { prompt: string; attachments: ChatAttachment[] }) {
  const prompt = typeof payload === 'string' ? payload.trim() : payload.prompt.trim()
  const attachments = typeof payload === 'string' ? [] : payload.attachments
  const hasAttachments = attachments.length > 0

  if (!prompt && !hasAttachments) {
    return
  }

  const previewText = prompt || '发送了一张图片'
  const conversation =
    activeConversation.value ?? (isDraftConversationRoute.value ? createDraftConversation(previewText) : null)
  if (!conversation) {
    return
  }

  conversation.messages.push({
    id: `user-${Date.now()}`,
    role: 'user',
    content: prompt,
    attachments: hasAttachments ? attachments : undefined,
    createdAt: formatNow(),
  })
  conversation.updatedAt = '刚刚'
  conversation.preview = previewText
  typingConversationId.value = conversation.id

  if (pendingResponseTimer.value !== null) {
    window.clearTimeout(pendingResponseTimer.value)
  }

  const responseConversationId = conversation.id
  const responsePrompt = prompt || '我发来了一张图片，请帮我看看。'
  const response = buildAssistantResponse(responsePrompt, conversation)

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
    normalizeConversationCards([targetConversation])
    targetConversation.updatedAt = '刚刚'
    targetConversation.preview = response.content
    targetConversation.stage = response.nextStage
    targetConversation.intentLabel = response.nextIntentLabel
    targetConversation.statusText = response.statusText
    targetConversation.taskSummary = ''
    targetConversation.quickPrompts = response.quickPrompts
    targetConversation.currentRecipe = response.currentRecipe ?? targetConversation.currentRecipe

    if (typingConversationId.value === responseConversationId) {
      typingConversationId.value = null
    }

    pendingResponseTimer.value = null
  }, 650)
}

function requestTimer(payload: TimerRequest) {
  const conversationId = activeConversationId.value
  if (!conversationId) {
    return
  }

  const currentTimer = conversationTimers.value[conversationId]
  if (
    currentTimer &&
    currentTimer.stepId === payload.stepId &&
    currentTimer.status !== 'finished'
  ) {
    return
  }

  const shouldReplace =
    currentTimer &&
    currentTimer.remainingSeconds > 0 &&
    currentTimer.stepId !== payload.stepId &&
    currentTimer.status !== 'finished'

  if (shouldReplace) {
    pendingTimerReplacement.value = payload
    return
  }

  applyTimerRequest(payload)
}

function applyTimerRequest(payload: TimerRequest) {
  const conversationId = activeConversationId.value
  if (!conversationId) {
    return
  }

  conversationTimers.value[conversationId] = {
    stepId: payload.stepId,
    label: payload.label,
    totalSeconds: payload.seconds,
    remainingSeconds: payload.seconds,
    status: 'running',
  }

  showTimerNotice(conversationId, '计时器已启动', 'info')
  ensureCountdownTicker()
}

function confirmTimerReplacement() {
  if (!pendingTimerReplacement.value) {
    return
  }

  applyTimerRequest(pendingTimerReplacement.value)
  pendingTimerReplacement.value = null
}

function cancelTimerReplacement() {
  pendingTimerReplacement.value = null
}

function pauseTimer() {
  if (!activeConversationId.value || !activeTimerSlot.value) {
    return
  }

  activeTimerSlot.value.status = 'paused'
  stopCountdownTickerIfIdle()
}

function resumeTimer() {
  if (!activeConversationId.value || !activeTimerSlot.value) {
    return
  }

  if (activeTimerSlot.value.remainingSeconds <= 0) {
    activeTimerSlot.value.remainingSeconds = activeTimerSlot.value.totalSeconds
  }

  activeTimerSlot.value.status = 'running'
  ensureCountdownTicker()
}

function resetTimer() {
  if (!activeConversationId.value || !activeTimerSlot.value) {
    return
  }

  activeTimerSlot.value.remainingSeconds = activeTimerSlot.value.totalSeconds
  activeTimerSlot.value.status = 'paused'
  stopCountdownTickerIfIdle()
}

function cancelTimer() {
  if (!activeConversationId.value) {
    return
  }

  delete conversationTimers.value[activeConversationId.value]
  stopCountdownTickerIfIdle()
}

function startConversationFromRecipe(recipe: RecipeRecord) {
  const conversation: ConversationRecord = {
    id: `conversation-new-${newConversationIndex}`,
    title: `${recipe.name} 备料对话`,
    statusText: `已选中 ${recipe.name}，开始确认备料`,
    preview: `已从菜谱详情进入 ${recipe.name} 的备料阶段。`,
    updatedAt: '刚刚',
    stage: 'shopping',
    intentLabel: '备料中',
    currentRecipe: recipe.name,
    taskSummary: '',
    quickPrompts: ['这些都备齐了', '再看看菜谱详情', '按 1 人份调整一下'],
    messages: [
      {
        id: `conversation-new-${newConversationIndex}-assistant-1`,
        role: 'assistant',
        content: `已经为你打开 ${recipe.name} 的专属对话，我们直接从备料开始，不再重复走推荐步骤。`,
        createdAt: formatNow(),
        cards: [buildPantryCard(recipe)],
      },
    ],
  }

  newConversationIndex += 1
  conversations.value.unshift(conversation)
  activeConversationId.value = conversation.id
  router.push({ name: 'chat', params: { conversationId: conversation.id } })
}

function selectRecipe(recipeId: number) {
  router.push({ name: 'recipe-detail', params: { recipeId } })
}

function showRecipeLibrary() {
  router.push({ name: 'recipes' })
}
</script>

<template>
  <Transition name="screen-fade" mode="out-in">
    <AuthPage v-if="isAuthRoute" key="auth" :mode="authMode" />

    <div v-else key="workspace" class="app-shell">
      <AppSidebar
        :conversations="conversations"
        :conversation-timers="conversationTimers"
        :active-conversation-id="activeConversationId"
        :is-open="sidebarOpen"
        :shortcuts="sidebarShortcuts"
        :user-profile="profile"
        @close="closeSidebar"
        @new-conversation="startNewConversation"
        @open-profile="openProfilePanel"
        @select-conversation="selectConversation"
        @select-shortcut="selectShortcut"
      />

      <main class="workspace">
        <template v-if="isRecipeRoute">
          <section class="recipe-workspace">
            <RecipeLibraryPanel
              :recipes="mockRecipes"
              :selected-recipe-id="activeRecipeId"
              @select-recipe="selectRecipe"
              @show-library="showRecipeLibrary"
              @start-conversation="startConversationFromRecipe"
              @toggle-sidebar="openSidebar"
            />
          </section>
        </template>

        <template v-else-if="visibleConversation">
          <ChatHeader
            :conversation="visibleConversation"
            :stage-label="activeStageLabel"
            :timer-notice-needs-confirm="activeTimerNotice?.needsConfirm ?? false"
            :timer-notice-text="activeTimerNotice?.text ?? ''"
            :timer-notice-tone="activeTimerNotice?.tone ?? null"
            :timer-slot="activeTimerSlot"
            @cancel-timer="cancelTimer"
            @dismiss-timer-notice="dismissTimerNotice"
            @pause-timer="pauseTimer"
            @reset-timer="resetTimer"
            @resume-timer="resumeTimer"
            @toggle-sidebar="openSidebar"
          />

          <section class="chat-stage">
            <section ref="messageViewport" class="message-viewport hover-scroll">
              <div class="message-stream">
                <div v-if="isDraftConversationRoute && !activeConversation" class="blank-chat-state">
                  <p class="blank-chat-eyebrow">ChefMate</p>
                  <h3>{{ draftGreeting }}</h3>
                  <p>
                    先随手说说你的口味、时间、现有食材，或者去左侧菜谱里挑一道菜。当然，随便聊聊家常也行。
                  </p>
                </div>

                <template v-else>
                  <MessageBubble
                    v-for="message in activeConversation?.messages ?? []"
                    :key="message.id"
                    :message="message"
                    :auto-start-step-timer="profile.autoStartStepTimer"
                    @card-action="sendMessage"
                    @timer-request="requestTimer"
                  />
                </template>

                <div v-if="isTyping" class="typing-row">
                  <div class="typing-bubble">
                    <span></span>
                    <span></span>
                    <span></span>
                  </div>
                </div>

                <div class="message-bottom-spacer" aria-hidden="true"></div>
              </div>
            </section>

            <ComposerPanel
              :disabled="isComposerDisabled"
              :suggestions="activeSuggestions"
              @send="sendMessage"
            />
          </section>
        </template>
      </main>

      <OverlayDialog :is-open="profilePanelOpen" @close="closeProfilePanel">
        <ProfileSettingsPanel
          :tag-catalog="tagCatalog"
          :user-profile="profile"
          @logout="logout"
          @update-allow-auto-update="profile.allowAutoUpdate = $event"
          @update-auto-start-step-timer="profile.autoStartStepTimer = $event"
        />
      </OverlayDialog>

      <ActionModal
        :is-open="pendingTimerReplacement !== null"
        title="替换当前计时器？"
        message="当前已经有一个计时器在运行，确认后会用新的计时器替换它。"
        confirm-label="替换"
        cancel-label="再想想"
        @cancel="cancelTimerReplacement"
        @confirm="confirmTimerReplacement"
      />

      <WorkspaceOnboardingModal
        :is-open="workspaceOnboardingOpen"
        :tag-catalog="tagCatalog"
        :user-profile="profile"
        @complete="completeWorkspaceOnboarding"
      />
    </div>
  </Transition>
</template>

<style scoped>
.app-shell {
  display: flex;
  height: 100vh;
  min-height: 100vh;
  overflow: hidden;
  background:
    radial-gradient(circle at top left, rgba(229, 143, 91, 0.18), transparent 24rem),
    radial-gradient(circle at right, rgba(54, 106, 94, 0.12), transparent 26rem),
    var(--color-bg);
  animation: workspace-enter 220ms ease both;
}

.workspace {
  display: grid;
  flex: 1;
  height: 100vh;
  min-width: 0;
  min-height: 100vh;
  overflow: hidden;
  grid-template-rows: auto minmax(0, 1fr);
}


.recipe-workspace {
  display: grid;
  grid-row: 1 / -1;
  min-width: 0;
  min-height: 0;
  padding: 1.35rem 2rem 1.4rem;
}

.chat-stage {
  position: relative;
  display: grid;
  min-width: 0;
  min-height: 0;
  grid-template-rows: minmax(0, 1fr);
}

.message-viewport {
  height: 100%;
  min-height: 0;
  padding: 0 2rem;
  overflow-y: auto;
  overflow-x: hidden;
}

.message-stream {
  width: min(100%, 56rem);
  margin: 0 auto;
  padding: 1.5rem 0 0;
  animation: content-enter 200ms ease both;
}

.message-bottom-spacer {
  height: 13.5rem;
}

.screen-fade-enter-active,
.screen-fade-leave-active {
  transition:
    opacity 180ms ease,
    transform 220ms ease;
}

.screen-fade-enter-from,
.screen-fade-leave-to {
  opacity: 0;
  transform: translateY(0.75rem);
}

@keyframes workspace-enter {
  from {
    opacity: 0;
    transform: translateY(0.6rem);
  }

  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes content-enter {
  from {
    opacity: 0;
    transform: translateY(0.45rem);
  }

  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.blank-chat-state {
  display: grid;
  place-items: center;
  align-content: center;
  min-height: calc(100vh - 18rem);
  padding: 2rem 0 3rem;
  text-align: center;
}

.blank-chat-eyebrow {
  margin: 0 0 0.5rem;
  color: var(--color-text-soft);
  font-size: 0.78rem;
  letter-spacing: 0.16em;
  text-transform: uppercase;
}

.blank-chat-state h3 {
  margin: 0;
  font-size: clamp(1.7rem, 3vw, 2.45rem);
  line-height: 1.08;
}

.blank-chat-state p:last-child {
  width: min(100%, 32rem);
  margin: 0.9rem auto 0;
  color: var(--color-text-soft);
  font-size: 0.96rem;
  line-height: 1.7;
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

:deep(.cooking-guide-card.is-focused) {
  box-shadow: 0 0 0 2px rgba(229, 143, 91, 0.22);
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
  .recipe-workspace,
  .message-viewport {
    padding: 0 1rem;
  }

  .recipe-workspace {
    padding-top: 1rem;
  }

  .message-stream {
    padding-top: 1rem;
  }

  .blank-chat-state {
    min-height: calc(100vh - 15rem);
    padding: 1rem 0 2rem;
  }

  .message-bottom-spacer {
    height: 14.5rem;
  }
}
</style>
