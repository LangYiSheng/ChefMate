import type {
  CardAction,
  CardActionType,
  CardActionEvent,
  ChatAttachment,
  ChatMessage,
  ConversationClientCardState,
  ConversationRecord,
  ConversationStage,
  CookingGuideCard,
  PantryStatusCard,
  RecipeDetailCard,
  RecipeRecord,
  RecipeRecommendationsCard,
  RecipeSearchField,
  TagCatalog,
  UserProfileSummary,
} from '../types/chat'

const DEFAULT_API_BASE_URL = 'http://127.0.0.1:8000/api'

export interface AuthSessionPayload {
  token: string
  user: UserProfileSummary
}

export interface StreamEventPayload {
  event: 'status' | 'token' | 'final' | 'error'
  data: any
}

export interface VoiceWakeupResponse {
  text: string
  matched: boolean
  matchedKeyword?: string | null
  remainderText: string
}

interface ApiRequestOptions extends RequestInit {
  token?: string
}

export function getApiBaseUrl() {
  return (import.meta.env.VITE_API_BASE_URL || DEFAULT_API_BASE_URL).replace(/\/$/, '')
}

export function getApiOrigin() {
  const apiBaseUrl = getApiBaseUrl()
  if (/^https?:\/\//.test(apiBaseUrl)) {
    return apiBaseUrl.replace(/\/api$/, '')
  }

  if (typeof window !== 'undefined') {
    return window.location.origin
  }

  return ''
}

function createHeaders(options: ApiRequestOptions) {
  const headers = new Headers(options.headers)
  if (!headers.has('Content-Type') && options.body && !(options.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json')
  }
  if (options.token) {
    headers.set('Authorization', `Bearer ${options.token}`)
  }
  return headers
}

async function apiFetch<T>(path: string, options: ApiRequestOptions = {}): Promise<T> {
  const response = await fetch(`${getApiBaseUrl()}${path}`, {
    ...options,
    headers: createHeaders(options),
  })

  if (!response.ok) {
    let detail = `请求失败：${response.status}`
    try {
      const payload = await response.json()
      detail = payload.detail || detail
    } catch {
      // ignore
    }
    throw new Error(detail)
  }

  return (await response.json()) as T
}

function resolveAssetUrl(url?: string | null) {
  if (!url) {
    return ''
  }
  if (/^https?:\/\//.test(url) || url.startsWith('data:')) {
    return url
  }
  return `${getApiOrigin()}${url.startsWith('/') ? '' : '/'}${url}`
}

function normalizeAction(action: any): CardAction {
  return {
    id: String(action.id),
    label: String(action.label),
    actionType: action.action_type as CardActionType,
    payload: action.payload || {},
    tone: action.action_type === 'try_recipe' || action.action_type === 'ingredients_ready' ? 'primary' : 'ghost',
  }
}

function normalizeAttachment(attachment: any): ChatAttachment {
  return {
    id: String(attachment.id),
    kind: 'image',
    name: String(attachment.name),
    previewUrl: resolveAssetUrl(attachment.preview_url || attachment.file_url),
    fileId: attachment.id ? String(attachment.id) : undefined,
    fileUrl: resolveAssetUrl(attachment.file_url || attachment.preview_url),
  }
}

function toBackendClientCardState(cardState?: ConversationClientCardState) {
  if (!cardState) {
    return undefined
  }

  const payload: Record<string, unknown> = {}

  if (cardState.pantryStatus) {
    payload.pantry_status = {
      ready_ingredient_ids: cardState.pantryStatus.readyIngredientIds,
      focused_ingredient_id: cardState.pantryStatus.focusedIngredientId,
      flash_mode: cardState.pantryStatus.flashMode,
    }
  }

  if (cardState.cookingGuide) {
    payload.cooking_guide = {
      current_step: cardState.cookingGuide.currentStep,
      focused_step_id: cardState.cookingGuide.focusedStepId,
      flash_mode: cardState.cookingGuide.flashMode,
    }
  }

  return Object.keys(payload).length ? payload : undefined
}

function normalizeRecipe(record: any): RecipeRecord {
  return {
    id: Number(record.id),
    name: String(record.name),
    imagePath: record.image_path ? resolveAssetUrl(record.image_path) : null,
    description: String(record.description || ''),
    difficulty: record.difficulty,
    estimatedMinutes: Number(record.estimated_minutes || 0),
    servings: Number(record.servings || 0),
    tips: record.tips || '',
    tags: Array.isArray(record.tags) ? record.tags : [],
    recentActivity: record.recent_activity || undefined,
    ingredients: Array.isArray(record.ingredients)
      ? record.ingredients.map((item: any) => ({
          id: item.id,
          ingredientName: item.ingredient_name,
          amountValue: item.amount_value,
          amountText: item.amount_text,
          unit: item.unit,
          isOptional: item.is_optional,
          purpose: item.purpose,
          sortOrder: item.sort_order,
        }))
      : [],
    steps: Array.isArray(record.steps)
      ? record.steps.map((item: any) => ({
          id: item.id,
          stepNo: Number(item.step_no),
          title: item.title || undefined,
          instruction: item.instruction,
          timerSeconds: item.timer_seconds,
          notes: item.notes || undefined,
        }))
      : [],
  }
}

function normalizeCard(card: any): RecipeRecommendationsCard | RecipeDetailCard | PantryStatusCard | CookingGuideCard {
  if (card.type === 'recipe-recommendations') {
    return {
      type: 'recipe-recommendations',
      title: String(card.title),
      recipes: Array.isArray(card.recipes)
        ? card.recipes.map((item: any) => ({
            recipeId: Number(item.recipe_id),
            name: item.name,
            description: item.description || '',
            tags: item.tags || [],
            difficulty: item.difficulty,
            estimatedMinutes: Number(item.estimated_minutes || 0),
            servings: Number(item.servings || 0),
            actions: Array.isArray(item.actions) ? item.actions.map(normalizeAction) : [],
          }))
        : [],
    }
  }

  if (card.type === 'recipe-detail') {
    return {
      type: 'recipe-detail',
      recipe: normalizeRecipe(card.recipe),
      actions: Array.isArray(card.actions) ? card.actions.map(normalizeAction) : [],
    }
  }

  if (card.type === 'pantry-status') {
    return {
      type: 'pantry-status',
      title: String(card.title),
      checklist: Array.isArray(card.checklist)
        ? card.checklist.map((item: any) => ({
            id: String(item.id),
            ingredient: item.ingredient,
            amount: item.amount,
            status: item.status,
            note: item.note || '',
            isOptional: Boolean(item.is_optional),
          }))
        : [],
      actions: Array.isArray(card.actions) ? card.actions.map(normalizeAction) : [],
    }
  }

  return {
    type: 'cooking-guide',
    title: String(card.title),
    currentStep: Number(card.current_step || 1),
    totalSteps: Number(card.total_steps || 0),
    steps: Array.isArray(card.steps)
      ? card.steps.map((item: any) => ({
          id: String(item.id),
          title: item.title,
          detail: item.detail,
          duration: item.duration,
          timerSeconds: item.timer_seconds,
          notes: item.notes || undefined,
          status: item.status === 'pending' ? 'upcoming' : item.status,
        }))
      : [],
  }
}

function normalizeMessage(message: any): ChatMessage {
  const createdAt = message.created_at
    ? new Date(message.created_at).toLocaleTimeString('zh-CN', {
        hour: '2-digit',
        minute: '2-digit',
      })
    : ''
  return {
    id: String(message.id),
    role: message.role,
    content: message.content || '',
    createdAt,
    attachments: Array.isArray(message.attachments) ? message.attachments.map(normalizeAttachment) : [],
    suggestions: Array.isArray(message.suggestions) ? message.suggestions : undefined,
    cards: Array.isArray(message.cards) ? message.cards.map(normalizeCard) : [],
  }
}

export function normalizeConversation(record: any): ConversationRecord {
  return {
    id: String(record.id),
    title: String(record.title),
    stage: record.stage as ConversationStage,
    currentRecipe: record.current_recipe_name || undefined,
    suggestions: Array.isArray(record.suggestions) ? record.suggestions : [],
    messages: Array.isArray(record.messages) ? record.messages.map(normalizeMessage) : [],
  }
}

export function normalizeProfile(record: any): UserProfileSummary {
  return {
    name: record.display_name || record.username,
    level: 'ChefMate 用户',
    account: record.username,
    email: record.email || '',
    allowAutoUpdate: Boolean(record.allow_auto_update),
    autoStartStepTimer: Boolean(record.auto_start_step_timer),
    cookingPreferenceText: record.cooking_preference_text || '',
    tagSelections: normalizeTagCatalog(record.tag_selections || {}),
    hasCompletedWorkspaceOnboarding: Boolean(record.has_completed_workspace_onboarding),
    profileCompletedAt: record.profile_completed_at || null,
    voiceWakeWordEnabled: Boolean(record.voice_wake_word_enabled),
    voiceWakeWordPrompted: Boolean(record.voice_wake_word_prompted),
  }
}

export function normalizeTagCatalog(record: any): TagCatalog {
  return {
    flavor: Array.isArray(record.flavor) ? record.flavor : [],
    method: Array.isArray(record.method) ? record.method : [],
    scene: Array.isArray(record.scene) ? record.scene : [],
    health: Array.isArray(record.health) ? record.health : [],
    time: Array.isArray(record.time) ? record.time : [],
    tool: Array.isArray(record.tool) ? record.tool : [],
  }
}

export async function login(username: string, password: string): Promise<AuthSessionPayload> {
  const response = await apiFetch<any>('/auth/login', {
    method: 'POST',
    body: JSON.stringify({ username, password }),
  })
  return {
    token: response.token,
    user: normalizeProfile(response.user),
  }
}

export async function register(username: string, email: string, password: string): Promise<AuthSessionPayload> {
  const response = await apiFetch<any>('/auth/register', {
    method: 'POST',
    body: JSON.stringify({
      username,
      email: email.trim() || null,
      password,
    }),
  })
  return {
    token: response.token,
    user: normalizeProfile(response.user),
  }
}

export async function fetchMe(token: string) {
  return normalizeProfile(await apiFetch<any>('/auth/me', { token }))
}

export async function logout(token: string) {
  await apiFetch('/auth/logout', { method: 'POST', token })
}

export async function fetchProfile(token: string) {
  return normalizeProfile(await apiFetch<any>('/profile', { token }))
}

export async function updateProfile(token: string, payload: Record<string, unknown>) {
  return normalizeProfile(
    await apiFetch<any>('/profile', {
      method: 'PATCH',
      token,
      body: JSON.stringify(payload),
    }),
  )
}

export async function fetchTagCatalog(token: string) {
  return normalizeTagCatalog(await apiFetch<any>('/profile/tag-catalog', { token }))
}

export async function uploadImage(token: string, file: File) {
  const formData = new FormData()
  formData.append('image', file)
  const response = await apiFetch<any>('/files/images', {
    method: 'POST',
    token,
    body: formData,
  })
  return normalizeAttachment(response)
}

export async function checkVoiceWakeup(token: string, audioBase64: string, sampleRate = 16000) {
  const response = await apiFetch<any>('/voice/wakeup/check', {
    method: 'POST',
    token,
    body: JSON.stringify({
      audio_base64: audioBase64,
      sample_rate: sampleRate,
      format: 'pcm_s16le',
    }),
  })
  return {
    text: String(response.text || ''),
    matched: Boolean(response.matched),
    matchedKeyword: response.matched_keyword || null,
    remainderText: String(response.remainder_text || ''),
  } satisfies VoiceWakeupResponse
}

export async function fetchConversations(token: string) {
  const response = await apiFetch<any[]>('/conversations', { token })
  return response.map(normalizeConversation)
}

export async function fetchConversation(token: string, conversationId: string) {
  return normalizeConversation(await apiFetch<any>(`/conversations/${conversationId}`, { token }))
}

export async function createConversation(
  token: string,
  payload: { source?: 'manual' | 'recipe'; recipe_id?: number | null } = {},
) {
  const response = await apiFetch<any>('/conversations', {
    method: 'POST',
    token,
    body: JSON.stringify(payload),
  })
  return normalizeConversation(response.conversation)
}

export async function deleteConversations(token: string, conversationIds: string[]) {
  const response = await apiFetch<any>('/conversations', {
    method: 'DELETE',
    token,
    body: JSON.stringify({
      conversation_ids: conversationIds,
    }),
  })
  return {
    deletedIds: Array.isArray(response.deleted_ids) ? response.deleted_ids.map(String) : [],
    deletedCount: Number(response.deleted_count || 0),
  }
}

export async function fetchRecipes(
  token: string,
  params: {
    keyword?: string
    tag?: string
    searchFields?: RecipeSearchField[]
    limit?: number
    offset?: number
  } = {},
) {
  const search = new URLSearchParams()
  if (params.keyword) {
    search.set('keyword', params.keyword)
  }
  if (params.tag) {
    search.set('tag', params.tag)
  }
  if (params.searchFields?.length) {
    params.searchFields.forEach((field) => search.append('search_fields', field))
  }
  if (params.limit !== undefined) {
    search.set('limit', String(params.limit))
  }
  if (params.offset !== undefined) {
    search.set('offset', String(params.offset))
  }
  const response = await apiFetch<any>(`/recipes${search.size ? `?${search.toString()}` : ''}`, { token })
  return {
    items: Array.isArray(response.items) ? response.items.map(normalizeRecipe) : [],
    recentItems: Array.isArray(response.recent_items) ? response.recent_items.map(normalizeRecipe) : [],
    total: Number(response.total || 0),
  }
}

export async function fetchRecipe(token: string, recipeId: number) {
  return normalizeRecipe(await apiFetch<any>(`/recipes/${recipeId}`, { token }))
}

export async function sendConversationMessage(
  token: string,
  conversationId: string,
  payload: {
    content?: string
    attachments?: Array<{ kind: 'image'; file_id?: string; file_url?: string; name?: string }>
    action?: { action_type: CardActionType; payload: Record<string, unknown> }
    clientCardState?: ConversationClientCardState
  },
) {
  const response = await apiFetch<any>(`/conversations/${conversationId}/messages`, {
    method: 'POST',
    token,
    body: JSON.stringify({
      content: payload.content,
      attachments: payload.attachments,
      action: payload.action,
      client_card_state: toBackendClientCardState(payload.clientCardState),
    }),
  })
  return {
    conversation: normalizeConversation(response.conversation),
    message: normalizeMessage(response.message),
  }
}

export async function streamConversationMessage(
  token: string,
  conversationId: string,
  payload: {
    content?: string
    attachments?: Array<{ kind: 'image'; file_id?: string; file_url?: string; name?: string }>
    action?: { action_type: CardActionType; payload: Record<string, unknown> }
    clientCardState?: ConversationClientCardState
  },
  onEvent: (event: StreamEventPayload) => void,
) {
  const response = await fetch(`${getApiBaseUrl()}/conversations/${conversationId}/messages/stream`, {
    method: 'POST',
    headers: createHeaders({
      token,
      headers: { 'Content-Type': 'application/json' },
    }),
    body: JSON.stringify({
      content: payload.content,
      attachments: payload.attachments,
      action: payload.action,
      client_card_state: toBackendClientCardState(payload.clientCardState),
    }),
  })

  if (!response.ok || !response.body) {
    let detail = `请求失败：${response.status}`
    try {
      const payload = await response.json()
      detail = payload.detail || detail
    } catch {
      // ignore
    }
    throw new Error(detail)
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) {
      break
    }
    buffer += decoder.decode(value, { stream: true })
    let boundaryIndex = buffer.indexOf('\n\n')
    while (boundaryIndex >= 0) {
      const rawEvent = buffer.slice(0, boundaryIndex)
      buffer = buffer.slice(boundaryIndex + 2)
      boundaryIndex = buffer.indexOf('\n\n')

      const eventNameLine = rawEvent
        .split('\n')
        .find((line) => line.startsWith('event:'))
      const dataLine = rawEvent
        .split('\n')
        .find((line) => line.startsWith('data:'))

      if (!eventNameLine || !dataLine) {
        continue
      }

      const eventName = eventNameLine.replace('event:', '').trim() as StreamEventPayload['event']
      const dataText = dataLine.replace('data:', '').trim()
      const data = dataText ? JSON.parse(dataText) : {}
      if (eventName === 'final') {
        onEvent({
          event: eventName,
          data: {
            conversation: normalizeConversation(data.conversation),
            message: normalizeMessage(data.message),
          },
        })
        continue
      }
      onEvent({ event: eventName, data })
    }
  }
}

export function toBackendActionPayload(action: CardActionEvent) {
  return {
    action_type: action.actionType,
    payload: action.payload,
  }
}
