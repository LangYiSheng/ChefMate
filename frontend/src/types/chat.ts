export type ConversationStage = 'idea' | 'planning' | 'shopping' | 'cooking'

export type MessageRole = 'user' | 'assistant' | 'system'

export type TagCategoryKey = 'flavor' | 'method' | 'scene' | 'health' | 'time' | 'tool'
export type RecipeSearchField = 'name' | 'ingredient' | 'method' | 'flavor'

export type CardActionType = 'view_recipe' | 'try_recipe' | 'ingredients_ready' | 'open_timer'

export interface NavShortcut {
  id: string
  label: string
  caption: string
}

export interface TagCatalog {
  flavor: string[]
  method: string[]
  scene: string[]
  health: string[]
  time: string[]
  tool: string[]
}

export interface UserProfileSummary {
  name: string
  level: string
  account: string
  email: string
  allowAutoUpdate: boolean
  autoStartStepTimer: boolean
  cookingPreferenceText: string
  tagSelections: TagCatalog
  hasCompletedWorkspaceOnboarding?: boolean
  profileCompletedAt?: string | null
  voiceWakeWordEnabled: boolean
  voiceWakeWordPrompted: boolean
}

export interface ConversationRecord {
  id: string
  title: string
  stage: ConversationStage
  currentRecipe?: string
  suggestions: string[]
  messages: ChatMessage[]
}

export interface ChatMessage {
  id: string
  role: MessageRole
  content: string
  createdAt: string
  attachments?: ChatAttachment[]
  cards?: MessageCard[]
  suggestions?: string[]
}

export interface ChatAttachment {
  id: string
  kind: 'image'
  name: string
  previewUrl: string
  fileId?: string
  fileUrl?: string
}

export interface CardActionEvent {
  actionType: CardActionType
  payload: Record<string, unknown>
}

export interface CardAction extends CardActionEvent {
  id: string
  label: string
  tone?: 'primary' | 'secondary' | 'ghost'
}

export interface PantryClientCardState {
  readyIngredientIds: string[]
  focusedIngredientId?: string | null
  flashMode: boolean
}

export interface CookingGuideClientCardState {
  currentStep: number
  focusedStepId?: string | null
  flashMode: boolean
}

export interface ConversationClientCardState {
  pantryStatus?: PantryClientCardState
  cookingGuide?: CookingGuideClientCardState
}

export type ClientCardStateUpdate =
  | ({ type: 'pantry-status' } & PantryClientCardState)
  | ({ type: 'cooking-guide' } & CookingGuideClientCardState)

export interface TimerRequest {
  stepId: string
  label: string
  seconds: number
}

export interface ConversationTimerSlot {
  stepId: string
  label: string
  totalSeconds: number
  remainingSeconds: number
  status: 'running' | 'paused' | 'finished'
}

export type MessageCard =
  | RecipeRecommendationsCard
  | RecipeDetailCard
  | PantryStatusCard
  | CookingGuideCard

export interface RecipeRecommendationsCard {
  type: 'recipe-recommendations'
  title: string
  recipes: RecipeRecommendation[]
}

export interface RecipeRecommendation {
  recipeId: number
  name: string
  description: string
  tags: string[]
  difficulty: RecipeRecord['difficulty']
  estimatedMinutes: number
  servings: number
  actions: CardAction[]
}

export interface RecipeDetailCard {
  type: 'recipe-detail'
  recipe: RecipeRecord
  actions: CardAction[]
}

export interface PantryStatusCard {
  type: 'pantry-status'
  title: string
  checklist: PantryChecklistItem[]
  actions: CardAction[]
}

export interface PantryChecklistItem {
  id: string
  ingredient: string
  amount: string
  status: 'ready' | 'pending' | 'skipped'
  note?: string
  isOptional?: boolean
}

export interface CookingGuideCard {
  type: 'cooking-guide'
  title: string
  currentStep: number
  totalSteps: number
  steps: CookingGuideStep[]
}

export interface CookingGuideStep {
  id: string
  title: string
  detail: string
  duration: string
  timerSeconds?: number | null
  notes?: string
  status: 'done' | 'current' | 'pending' | 'upcoming'
}

export interface RecipeRecord {
  id: number
  name: string
  imagePath?: string | null
  description: string
  difficulty: '简单' | '中等' | '困难'
  estimatedMinutes: number
  servings: number
  tips?: string
  status?: 'DRAFT' | 'PUBLISHED'
  createdAt?: string
  updatedAt?: string
  tags: string[]
  recentActivity?: string
  ingredients: RecipeIngredientRecord[]
  steps: RecipeStepRecord[]
}

export interface RecipeIngredientRecord {
  id?: number | string
  ingredientName: string
  amountValue?: number | null
  amountText: string
  unit?: string | null
  isOptional?: boolean
  purpose?: string
  sortOrder?: number
}

export interface RecipeStepRecord {
  id?: number | string
  stepNo: number
  title?: string
  instruction: string
  timerSeconds?: number | null
  notes?: string
}
