<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, useTemplateRef, watch } from 'vue'
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
import {
  createConversation,
  fetchConversation,
  fetchConversations,
  fetchProfile,
  fetchRecipe,
  fetchTagCatalog,
  logout as requestLogout,
  streamConversationMessage,
  toBackendActionPayload,
  updateProfile,
} from './lib/api'
import { clearAuthSession, getAuthSession, getAuthToken, updateAuthSession } from './state/auth'
import type {
  CardActionEvent,
  ChatAttachment,
  ChatMessage,
  ClientCardStateUpdate,
  ConversationClientCardState,
  ConversationRecord,
  ConversationTimerSlot,
  MessageCard,
  RecipeRecord,
  TagCatalog,
  TimerRequest,
  UserProfileSummary,
} from './types/chat'

const draftConversationId = 'new'
const draftSuggestions = ['今晚想吃点热乎的', '冰箱里有鸡蛋和番茄', '帮我推荐一道快手菜']
const sidebarShortcuts = [
  {
    id: 'recipes',
    label: '菜谱',
    caption: '手动浏览全部菜谱',
  },
]
const stageLabelMap: Record<ConversationRecord['stage'], string> = {
  idea: '闲聊',
  planning: '推荐中',
  shopping: '备料中',
  cooking: '烹饪中',
}
const draftGreetingTemplates = {
  morning: ['早上好，{name}。', '新的一天开始啦，{name}。'],
  noon: ['中午好，{name}。', '午安，{name}。'],
  afternoon: ['下午好，{name}。', '嗨，{name}。'],
  evening: ['晚上好，{name}。', '欢迎回来，{name}。'],
} as const

const route = useRoute()
const router = useRouter()
const conversations = ref<ConversationRecord[]>([])
const recipes = ref<RecipeRecord[]>([])
const profile = ref<UserProfileSummary>({
  name: '朋友',
  level: 'ChefMate 用户',
  account: '',
  email: '',
  allowAutoUpdate: true,
  autoStartStepTimer: false,
  cookingPreferenceText: '',
  tagSelections: {
    flavor: [],
    method: [],
    scene: [],
    health: [],
    time: [],
    tool: [],
  },
})
const tagCatalog = ref<TagCatalog>({
  flavor: [],
  method: [],
  scene: [],
  health: [],
  time: [],
  tool: [],
})
const loadedConversationIds = ref<Record<string, boolean>>({})
const loadedRecipeIds = ref<Record<number, boolean>>({})
const activeConversationId = ref('')
const sidebarOpen = ref(false)
const profilePanelOpen = ref(false)
const workspaceOnboardingOpen = ref(false)
const typingConversationId = ref<string | null>(null)
const conversationClientCardState = ref<Record<string, ConversationClientCardState>>({})
const streamingStatusText = ref('')
const draftGreeting = ref('')
const loadingWorkspace = ref(false)
const workspaceInitialized = ref(false)
const conversationTimers = ref<Record<string, ConversationTimerSlot>>({})
const pendingTimerReplacement = ref<TimerRequest | null>(null)
const timerNotice = ref<{
  conversationId: string
  text: string
  tone: 'info' | 'alert'
  needsConfirm: boolean
} | null>(null)
const messageViewport = useTemplateRef<HTMLDivElement>('messageViewport')
let countdownTicker: number | null = null
let timerNoticeTimeout: number | null = null

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

async function loadWorkspaceData() {
  const token = getAuthToken()
  if (!token || isAuthRoute.value) {
    return
  }

  loadingWorkspace.value = true
  try {
    const [nextProfile, nextTagCatalog, nextConversations] = await Promise.all([
      fetchProfile(token),
      fetchTagCatalog(token),
      fetchConversations(token),
    ])
    profile.value = nextProfile
    tagCatalog.value = nextTagCatalog
    conversations.value = normalizeConversationCards(nextConversations)
    refreshDraftGreeting()
    workspaceInitialized.value = true
    updateAuthSession({
      displayName: nextProfile.name,
      email: nextProfile.email || null,
      hasCompletedWorkspaceOnboarding: nextProfile.hasCompletedWorkspaceOnboarding,
      profileCompletedAt: nextProfile.profileCompletedAt ?? null,
    })
    workspaceOnboardingOpen.value = !nextProfile.hasCompletedWorkspaceOnboarding && !isAuthRoute.value
  } catch (error) {
    await logout()
    throw error
  } finally {
    loadingWorkspace.value = false
  }
}

function upsertConversation(conversation: ConversationRecord, replaceMessages = false) {
  const index = conversations.value.findIndex((item) => item.id === conversation.id)
  if (index < 0) {
    conversations.value.unshift(conversation)
  } else {
    const current = conversations.value[index]
    conversations.value[index] = normalizeConversationCards([
      {
        ...current,
        ...conversation,
        messages: replaceMessages ? conversation.messages : current.messages,
      },
    ])[0]
  }
}

function upsertRecipe(recipe: RecipeRecord) {
  const index = recipes.value.findIndex((item) => item.id === recipe.id)
  if (index < 0) {
    recipes.value.unshift(recipe)
  } else {
    recipes.value[index] = {
      ...recipes.value[index],
      ...recipe,
    }
  }
}

async function ensureConversationLoaded(conversationId: string) {
  if (loadedConversationIds.value[conversationId]) {
    return
  }
  const token = getAuthToken()
  if (!token) {
    return
  }
  const detail = await fetchConversation(token, conversationId)
  upsertConversation(detail, true)
  loadedConversationIds.value[conversationId] = true
}

async function syncConversationFromBackend(conversationId: string) {
  const token = getAuthToken()
  if (!token) {
    return null
  }
  const detail = await fetchConversation(token, conversationId)
  upsertConversation(detail, true)
  loadedConversationIds.value[conversationId] = true
  return detail
}

async function ensureRecipeLoaded(recipeId: number) {
  if (loadedRecipeIds.value[recipeId]) {
    return
  }
  const token = getAuthToken()
  if (!token) {
    return
  }
  const detail = await fetchRecipe(token, recipeId)
  upsertRecipe(detail)
  loadedRecipeIds.value[recipeId] = true
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
    title: '等你说一句想吃什么',
    stage: 'idea',
    suggestions: draftSuggestions,
    messages: [],
  }
})

const activeSuggestions = computed(
  () => visibleConversation.value?.suggestions ?? (isDraftConversationRoute.value ? draftSuggestions : []),
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

const selectedRecipe = computed(
  () => recipes.value.find((recipe) => recipe.id === activeRecipeId.value) ?? null,
)

const isTyping = computed(
  () => visibleConversation.value !== null && typingConversationId.value === visibleConversation.value.id,
)

const isComposerDisabled = computed(() => isTyping.value || loadingWorkspace.value)
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
const activeConversationMeta = computed(() => {
  if (!visibleConversation.value) {
    return ''
  }

  const stageText =
    visibleConversation.value.currentRecipe
      ? `${stageLabelMap[visibleConversation.value.stage]} · ${visibleConversation.value.currentRecipe}`
      : stageLabelMap[visibleConversation.value.stage]

  if (activeTimerSlot.value?.status === 'running' && activeTimerSlot.value.remainingSeconds > 0) {
    return `${stageText} · 正在倒计时`
  }

  return stageText
})

watch(
  () => route.name,
  async () => {
    refreshDraftGreeting()
    if (!isAuthRoute.value && getAuthToken() && !workspaceInitialized.value) {
      try {
        await loadWorkspaceData()
      } catch {
        // ignore bootstrap errors; logout flow already handles cleanup
      }
    }
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
  () => [route.name, route.params.conversationId, conversations.value.length] as const,
  async ([routeName, routeConversationId]) => {
    if (routeName !== 'chat') {
      return
    }

    const normalizedConversationId = Array.isArray(routeConversationId)
      ? routeConversationId[0]
      : routeConversationId

    if (normalizedConversationId === draftConversationId || !normalizedConversationId) {
      if (!conversations.value.length || normalizedConversationId === draftConversationId) {
        activeConversationId.value = ''
        if (normalizedConversationId !== draftConversationId) {
          await router.replace({
            name: 'chat',
            params: { conversationId: draftConversationId },
          })
        }
        return
      }
      activeConversationId.value = conversations.value[0]?.id ?? ''
      if (activeConversationId.value) {
        await router.replace({
          name: 'chat',
          params: { conversationId: activeConversationId.value },
        })
      }
      return
    }

    activeConversationId.value = normalizedConversationId
    await ensureConversationLoaded(normalizedConversationId)
  },
  { immediate: true },
)

watch(
  () => visibleConversation.value?.messages.length ?? 0,
  async () => {
    await nextTick()
    scrollToBottom('smooth')
  },
)

watch(
  () => activeRecipeId.value,
  async (recipeId) => {
    if (recipeId) {
      await ensureRecipeLoaded(recipeId)
    }
  },
  { immediate: true },
)

onMounted(async () => {
  const authSession = getAuthSession()
  if (authSession) {
    profile.value.name = authSession.displayName || authSession.username
    profile.value.account = authSession.username
    profile.value.email = authSession.email || ''
  } else {
    refreshDraftGreeting()
  }
})

onBeforeUnmount(() => {
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

function openSidebar() {
  sidebarOpen.value = true
}

function formatNow() {
  return new Date().toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit',
  })
}

function closeSidebar() {
  sidebarOpen.value = false
}

async function refreshProfilePanelData() {
  const token = getAuthToken()
  if (!token) {
    return
  }

  const [nextProfile, nextTagCatalog] = await Promise.all([
    fetchProfile(token),
    fetchTagCatalog(token),
  ])
  profile.value = nextProfile
  tagCatalog.value = nextTagCatalog
  updateAuthSession({
    displayName: nextProfile.name,
    email: nextProfile.email || null,
    hasCompletedWorkspaceOnboarding: nextProfile.hasCompletedWorkspaceOnboarding,
    profileCompletedAt: nextProfile.profileCompletedAt ?? null,
  })
}

async function openProfilePanel() {
  profilePanelOpen.value = true
  closeSidebar()
  try {
    await refreshProfilePanelData()
  } catch {
    // keep current local state if refresh fails
  }
}

function closeProfilePanel() {
  profilePanelOpen.value = false
}

function sanitizeTagSelections(selections: TagCatalog): TagCatalog {
  return {
    flavor: selections.flavor.filter((tag) => tagCatalog.value.flavor.includes(tag)),
    method: selections.method.filter((tag) => tagCatalog.value.method.includes(tag)),
    scene: selections.scene.filter((tag) => tagCatalog.value.scene.includes(tag)),
    health: selections.health.filter((tag) => tagCatalog.value.health.includes(tag)),
    time: selections.time.filter((tag) => tagCatalog.value.time.includes(tag)),
    tool: selections.tool.filter((tag) => tagCatalog.value.tool.includes(tag)),
  }
}

async function completeWorkspaceOnboarding(payload: {
  name: string
  cookingPreferenceText: string
  tagSelections: UserProfileSummary['tagSelections']
  allowAutoUpdate: boolean
  autoStartStepTimer: boolean
}) {
  const token = getAuthToken()
  if (!token) {
    return
  }

  const normalizedTagSelections = sanitizeTagSelections(payload.tagSelections)
  const updated = await updateProfile(token, {
    display_name: payload.name,
    cooking_preference_text: payload.cookingPreferenceText,
    tag_selections: normalizedTagSelections,
    allow_auto_update: payload.allowAutoUpdate,
    auto_start_step_timer: payload.autoStartStepTimer,
    complete_workspace_onboarding: true,
  })
  profile.value = updated
  workspaceOnboardingOpen.value = false
  updateAuthSession({
    displayName: updated.name,
    email: updated.email || null,
    hasCompletedWorkspaceOnboarding: true,
    profileCompletedAt: updated.profileCompletedAt ?? null,
  })
  startNewConversation()
}

async function saveProfileSettings(payload: {
  allowAutoUpdate: boolean
  autoStartStepTimer: boolean
  cookingPreferenceText: string
  tagSelections: TagCatalog
  displayName: string
  email: string
}) {
  const token = getAuthToken()
  if (!token) {
    return
  }
  const normalizedTagSelections = sanitizeTagSelections(payload.tagSelections)
  const updated = await updateProfile(token, {
    allow_auto_update: payload.allowAutoUpdate,
    auto_start_step_timer: payload.autoStartStepTimer,
    cooking_preference_text: payload.cookingPreferenceText,
    tag_selections: normalizedTagSelections,
    display_name: payload.displayName,
    email: payload.email || null,
  })
  profile.value = updated
  updateAuthSession({
    displayName: updated.name,
    email: updated.email || null,
    hasCompletedWorkspaceOnboarding: updated.hasCompletedWorkspaceOnboarding,
    profileCompletedAt: updated.profileCompletedAt ?? null,
  })
}

async function logout() {
  const token = getAuthToken()
  try {
    if (token) {
      await requestLogout(token)
    }
  } catch {
    // ignore logout cleanup failure
  }
  clearAuthSession()
  closeProfilePanel()
  workspaceOnboardingOpen.value = false
  activeConversationId.value = ''
  conversations.value = []
  recipes.value = []
  loadedConversationIds.value = {}
  loadedRecipeIds.value = {}
  workspaceInitialized.value = false
  conversationTimers.value = {}
  conversationClientCardState.value = {}
  pendingTimerReplacement.value = null
  timerNotice.value = null
  typingConversationId.value = null
  streamingStatusText.value = ''
  stopCountdownTickerIfIdle()
  void router.push({ name: 'auth-login' })
}

function selectConversation(conversationId: string) {
  activeConversationId.value = conversationId
  void router.push({ name: 'chat', params: { conversationId } })
  closeSidebar()
}

function selectShortcut(shortcutId: string) {
  if (shortcutId === 'recipes') {
    void router.push({ name: 'recipes' })
  }

  closeSidebar()
}

function startNewConversation() {
  activeConversationId.value = ''
  void router.push({ name: 'chat', params: { conversationId: draftConversationId } })
  closeSidebar()
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

function updateConversationCardState(state: ClientCardStateUpdate) {
  const conversationId = visibleConversation.value?.id
  if (!conversationId || conversationId === draftConversationId) {
    return
  }

  const nextState = {
    ...(conversationClientCardState.value[conversationId] ?? {}),
  }

  if (state.type === 'pantry-status') {
    nextState.pantryStatus = {
      readyIngredientIds: [...state.readyIngredientIds],
      focusedIngredientId: state.focusedIngredientId ?? null,
      flashMode: state.flashMode,
    }
  } else {
    nextState.cookingGuide = {
      currentStep: state.currentStep,
      focusedStepId: state.focusedStepId ?? null,
      flashMode: state.flashMode,
    }
  }

  conversationClientCardState.value = {
    ...conversationClientCardState.value,
    [conversationId]: nextState,
  }
}

function buildOutgoingClientCardState(conversationId: string) {
  const state = conversationClientCardState.value[conversationId]
  if (!state) {
    return undefined
  }

  const payload: ConversationClientCardState = {}
  if (state.pantryStatus) {
    payload.pantryStatus = {
      readyIngredientIds: [...state.pantryStatus.readyIngredientIds],
      focusedIngredientId: state.pantryStatus.focusedIngredientId ?? null,
      flashMode: state.pantryStatus.flashMode,
    }
  }
  if (state.cookingGuide) {
    payload.cookingGuide = {
      currentStep: state.cookingGuide.currentStep,
      focusedStepId: state.cookingGuide.focusedStepId ?? null,
      flashMode: state.cookingGuide.flashMode,
    }
  }
  return Object.keys(payload).length ? payload : undefined
}

function clearConversationCardState(conversationId: string) {
  if (!(conversationId in conversationClientCardState.value)) {
    return
  }

  const nextState = { ...conversationClientCardState.value }
  delete nextState[conversationId]
  conversationClientCardState.value = nextState
}

async function ensureConversationForSend() {
  if (activeConversation.value) {
    return activeConversation.value
  }
  const token = getAuthToken()
  if (!token) {
    return null
  }
  const created = await createConversation(token, { source: 'manual' })
  upsertConversation(created, true)
  loadedConversationIds.value[created.id] = true
  activeConversationId.value = created.id
  await router.replace({ name: 'chat', params: { conversationId: created.id } })
  return created
}

function createStreamingAssistantMessage(): ChatMessage {
  return {
    id: `assistant-stream-${Date.now()}`,
    role: 'assistant',
    content: '',
    createdAt: formatNow(),
    cards: [],
  }
}

function describeAction(action?: CardActionEvent) {
  if (!action) {
    return ''
  }
  if (action.actionType === 'view_recipe') {
    return '查看这道菜的详情'
  }
  if (action.actionType === 'try_recipe') {
    return '我想尝试这道菜'
  }
  if (action.actionType === 'ingredients_ready') {
    return '这些都备齐了'
  }
  return action.actionType
}

async function sendMessage(payload: string | { prompt?: string; attachments?: ChatAttachment[]; action?: CardActionEvent }) {
  const prompt = typeof payload === 'string' ? payload.trim() : (payload.prompt || '').trim()
  const attachments = typeof payload === 'string' ? [] : payload.attachments || []
  const action = typeof payload === 'string' ? undefined : payload.action
  const hasAttachments = attachments.length > 0

  if (!prompt && !hasAttachments && !action) {
    return
  }

  const token = getAuthToken()
  if (!token) {
    return
  }

  const conversation = await ensureConversationForSend()
  if (!conversation) {
    return
  }
  if (typingConversationId.value === conversation.id) {
    return
  }

  const clientCardState = buildOutgoingClientCardState(conversation.id)

  let targetConversation =
    conversations.value.find((item) => item.id === conversation.id) ?? conversation

  if (targetConversation.id && targetConversation.id !== draftConversationId) {
    try {
      const synced = await syncConversationFromBackend(targetConversation.id)
      if (synced) {
        targetConversation = conversations.value.find((item) => item.id === synced.id) ?? synced
      }
    } catch {
      // ignore sync failure and continue with current local state
    }
  }

  const userMessage: ChatMessage = {
    id: `user-${Date.now()}`,
    role: 'user',
    content: prompt || describeAction(action),
    attachments: hasAttachments ? attachments : undefined,
    createdAt: formatNow(),
  }
  targetConversation.messages.push(userMessage)

  const placeholder = createStreamingAssistantMessage()
  targetConversation.messages.push(placeholder)
  typingConversationId.value = targetConversation.id
  streamingStatusText.value = '正在理解你的需求...'

  try {
    await streamConversationMessage(
      token,
      targetConversation.id,
      {
        content: prompt || undefined,
        attachments: attachments.map((attachment) => ({
          kind: 'image',
          file_id: attachment.fileId,
          file_url: attachment.fileUrl,
          name: attachment.name,
        })),
        action: action ? toBackendActionPayload(action) : undefined,
        clientCardState,
      },
      ({ event, data }) => {
        if (event === 'status') {
          streamingStatusText.value = data.text || '正在处理...'
          return
        }

        if (event === 'token') {
          placeholder.content += data.text || ''
          return
        }

        if (event === 'final') {
          const index = targetConversation.messages.findIndex((message) => message.id === placeholder.id)
          if (index >= 0) {
            targetConversation.messages[index] = data.message
          } else {
            targetConversation.messages.push(data.message)
          }
          targetConversation.title = data.conversation.title
          targetConversation.stage = data.conversation.stage
          targetConversation.currentRecipe = data.conversation.currentRecipe
          targetConversation.suggestions = data.conversation.suggestions
          clearConversationCardState(targetConversation.id)
          normalizeConversationCards([targetConversation])
          upsertConversation(targetConversation, true)
          loadedConversationIds.value[targetConversation.id] = true
          return
        }

        if (event === 'error') {
          placeholder.content = data.detail || '消息发送失败，请稍后重试。'
        }
      },
    )
    const synced = await syncConversationFromBackend(targetConversation.id)
    if (synced) {
      targetConversation = conversations.value.find((item) => item.id === synced.id) ?? synced
    }
  } catch (error) {
    placeholder.content = error instanceof Error ? error.message : '消息发送失败，请稍后重试。'
  } finally {
    typingConversationId.value = null
    streamingStatusText.value = ''
  }
}

function sendCardAction(action: CardActionEvent) {
  if (isTyping.value) {
    return
  }
  void sendMessage({ action })
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

async function startConversationFromRecipe(recipe: RecipeRecord) {
  const token = getAuthToken()
  if (!token) {
    return
  }
  const created = await createConversation(token, {
    source: 'recipe',
    recipe_id: recipe.id,
  })
  upsertConversation(created, true)
  loadedConversationIds.value[created.id] = true
  activeConversationId.value = created.id
  void router.push({ name: 'chat', params: { conversationId: created.id } })
}

function selectRecipe(recipeId: number) {
  void router.push({ name: 'recipe-detail', params: { recipeId } })
}

function showRecipeLibrary() {
  void router.push({ name: 'recipes' })
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
              :recipes="recipes"
              :selected-recipe="selectedRecipe"
              :selected-recipe-id="activeRecipeId"
              :recommendation-seed="JSON.stringify(profile.tagSelections)"
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
            :meta-text="activeConversationMeta"
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
                    v-for="message in visibleConversation.messages"
                    :key="message.id"
                    :message="message"
                    :auto-start-step-timer="profile.autoStartStepTimer"
                    :interaction-disabled="isTyping"
                    @card-action="sendCardAction"
                    @card-state-change="updateConversationCardState"
                    @timer-request="requestTimer"
                  />
                </template>

                <div v-if="isTyping" class="typing-row">
                  <div class="typing-bubble typing-bubble-with-text">
                    <div class="typing-dots">
                      <span></span>
                      <span></span>
                      <span></span>
                    </div>
                    <p>{{ streamingStatusText || 'ChefMate 正在思考...' }}</p>
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

        <template v-else-if="route.name === 'chat'">
          <section class="chat-stage">
            <section class="message-viewport hover-scroll">
              <div class="message-stream">
                <div class="blank-chat-state">
                  <p class="blank-chat-eyebrow">ChefMate</p>
                  <h3>正在加载这段对话...</h3>
                  <p>如果还没显示出来，稍等一下，或者先切到别的会话再回来看看。</p>
                </div>
              </div>
            </section>
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
          @save-profile="saveProfileSettings"
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

.typing-bubble-with-text {
  align-items: flex-start;
  gap: 0.8rem;
}

.typing-dots {
  display: inline-flex;
  gap: 0.35rem;
  margin-top: 0.15rem;
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

.typing-bubble-with-text p {
  margin: 0;
  color: var(--color-text-soft);
  font-size: 0.9rem;
  line-height: 1.6;
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
