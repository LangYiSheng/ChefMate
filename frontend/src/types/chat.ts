export type ConversationStage = 'idea' | 'planning' | 'shopping' | 'cooking'

export type MessageRole = 'user' | 'assistant' | 'system'

export interface NavShortcut {
  id: string
  label: string
  caption: string
}

export interface UserProfileSummary {
  name: string
  level: string
  focus: string
  preferences: string[]
  email: string
  availableTime: string
  kitchenMode: string
  tools: string[]
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
  cards?: MessageCard[]
}

export type MessageCard = RecipeRecommendationsCard | PantryStatusCard | CookingGuideCard

export interface RecipeRecommendationsCard {
  type: 'recipe-recommendations'
  title: string
  summary: string
  recipes: RecipeRecommendation[]
}

export interface RecipeRecommendation {
  id: string
  name: string
  duration: string
  difficulty: string
  calories: string
  fitReason: string
  highlights: string[]
}

export interface PantryStatusCard {
  type: 'pantry-status'
  title: string
  summary: string
  completion: number
  checklist: PantryChecklistItem[]
  actions: string[]
}

export interface PantryChecklistItem {
  ingredient: string
  amount: string
  status: 'ready' | 'missing' | 'low'
  note: string
}

export interface CookingGuideCard {
  type: 'cooking-guide'
  title: string
  summary: string
  currentStep: number
  totalSteps: number
  timers: CookingTimer[]
  steps: CookingGuideStep[]
}

export interface CookingTimer {
  label: string
  duration: string
}

export interface CookingGuideStep {
  title: string
  detail: string
  duration: string
  status: 'done' | 'current' | 'upcoming'
}
