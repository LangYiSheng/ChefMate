export type ConversationStage = 'idea' | 'planning' | 'shopping' | 'cooking'

export type MessageRole = 'user' | 'assistant' | 'system'

export type TagCategoryKey = 'flavor' | 'method' | 'scene' | 'health' | 'time' | 'tool'

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
}

export interface ConversationRecord {
  id: string
  title: string
  statusText: string
  preview: string
  updatedAt: string
  stage: ConversationStage
  intentLabel: string
  currentRecipe?: string
  taskSummary: string
  quickPrompts: string[]
  messages: ChatMessage[]
}

export interface ChatMessage {
  id: string
  role: MessageRole
  content: string
  createdAt: string
  attachments?: ChatAttachment[]
  cards?: MessageCard[]
}

export interface ChatAttachment {
  id: string
  kind: 'image'
  name: string
  previewUrl: string
}

export interface CardAction {
  id: string
  label: string
  message: string
  tone?: 'primary' | 'secondary' | 'ghost'
}

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
  summary: string
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
  detailAction: CardAction
  tryAction: CardAction
}

export interface RecipeDetailCard {
  type: 'recipe-detail'
  title: string
  summary: string
  recipe: RecipeRecord
  actions: CardAction[]
}

export interface PantryStatusCard {
  type: 'pantry-status'
  title: string
  summary: string
  checklist: PantryChecklistItem[]
  actions: CardAction[]
}

export interface PantryChecklistItem {
  id: string
  ingredient: string
  amount: string
  status: 'ready' | 'pending'
  note: string
  isOptional?: boolean
}

export interface CookingGuideCard {
  type: 'cooking-guide'
  title: string
  summary: string
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
  status: 'done' | 'current' | 'upcoming'
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
