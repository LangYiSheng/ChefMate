import { mockRecipes } from './mockRecipes'
import type {
  ConversationRecord,
  MessageCard,
  NavShortcut,
  RecipeRecord,
  UserProfileSummary,
} from '../types/chat'

export const sidebarShortcuts: NavShortcut[] = [
  {
    id: 'recipes',
    label: '菜谱',
    caption: '手动浏览全部菜谱',
  },
]

export const userProfile: UserProfileSummary = {
  name: '林小满',
  level: '家常熟手',
  account: 'linxiaoman',
  email: 'chefmate.demo@example.com',
  allowAutoUpdate: true,
  autoStartStepTimer: false,
  cookingPreferenceText:
    '我更喜欢工作日晚餐节奏快一点，偏家常、少油、少洗锅。能用空气炸锅或一口平底锅完成的做法会更有安全感，也愿意偶尔尝试一点新口味。',
  tagSelections: {
    flavor: ['清淡', '蒜香'],
    method: ['炒', '空气炸锅'],
    scene: ['家常', '晚餐'],
    health: ['低油', '高蛋白'],
    time: ['10到20分钟'],
    tool: ['空气炸锅', '平底锅'],
  },
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

function buildRecommendationCard(recipes: RecipeRecord[]): MessageCard {
  return {
    type: 'recipe-recommendations',
    title: '今晚可以先从这几道里挑',
    summary: '',
    recipes: recipes.map((recipe) => ({
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
    title: `${recipe.name} 的做法`,
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
    checklist: recipe.ingredients.map((ingredient, index) => ({
      id: String(ingredient.id ?? `${recipe.id}-ingredient-${index + 1}`),
      ingredient: ingredient.ingredientName,
      amount: ingredient.amountText,
      status: index < 2 ? 'ready' : 'pending',
      note:
        ingredient.purpose ||
        (ingredient.isOptional ? '这一项是可选的，没有也可以先做。' : '建议先确认这一项是否备齐。'),
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

function buildCookingGuideCard(recipe: RecipeRecord, currentStep = 2): MessageCard {
  return {
    type: 'cooking-guide',
    title: `${recipe.name} 烹饪步骤`,
    summary: '',
    currentStep,
    totalSteps: recipe.steps.length,
    steps: recipe.steps.map((step, index) => ({
      id: String(step.id ?? `${recipe.id}-step-${step.stepNo}`),
      title: step.title || `步骤 ${step.stepNo}`,
      detail: step.instruction,
      duration: formatStepDuration(step.timerSeconds),
      timerSeconds: step.timerSeconds,
      notes: step.notes,
      status: index + 1 < currentStep ? 'done' : index + 1 === currentStep ? 'current' : 'upcoming',
    })),
  }
}

const tomatoRecipe = mockRecipes.find((recipe) => recipe.id === 101) ?? mockRecipes[0]
const dryPotRecipe = mockRecipes.find((recipe) => recipe.id === 102) ?? mockRecipes[1]
const braisedNoodlesRecipe = mockRecipes.find((recipe) => recipe.id === 105) ?? mockRecipes[4]

const seedConversations: ConversationRecord[] = [
  {
    id: 'conversation-demo-cards',
    title: '卡片总览演示',
    statusText: '全部卡片演示，方便集中检查界面',
    preview: '这一条对话会连续展示推荐、详情、备料、烹饪四类卡片。',
    updatedAt: '刚刚',
    stage: 'cooking',
    intentLabel: '烹饪中',
    currentRecipe: tomatoRecipe.name,
    taskSummary: '',
    quickPrompts: ['再看一遍推荐卡', '切回备料阶段', '继续下一步'],
    messages: [
      {
        id: 'conversation-demo-cards-message-1',
        role: 'assistant',
        content: '这条对话里放了几种常用卡片，方便你一起看看效果。',
        createdAt: '19:12',
      },
      {
        id: 'conversation-demo-cards-message-2',
        role: 'user',
        content: '我想看看推荐阶段的卡片会怎么展示。',
        createdAt: '19:13',
      },
      {
        id: 'conversation-demo-cards-message-3',
        role: 'assistant',
        content: '先看推荐结果。',
        createdAt: '19:13',
        cards: [buildRecommendationCard(mockRecipes.slice(0, 3))],
      },
      {
        id: 'conversation-demo-cards-message-4',
        role: 'user',
        content: '那就展开番茄炒蛋详情给我看看。',
        createdAt: '19:14',
      },
      {
        id: 'conversation-demo-cards-message-5',
        role: 'assistant',
        content: '这是这道菜的详细信息。',
        createdAt: '19:14',
        cards: [buildRecipeDetailCard(tomatoRecipe)],
      },
      {
        id: 'conversation-demo-cards-message-6',
        role: 'user',
        content: '接着看看备料检查卡。',
        createdAt: '19:15',
      },
      {
        id: 'conversation-demo-cards-message-7',
        role: 'assistant',
        content: '这是备料检查。',
        createdAt: '19:15',
        cards: [buildPantryCard(tomatoRecipe)],
      },
      {
        id: 'conversation-demo-cards-message-8',
        role: 'user',
        content: '再让我看看烹饪步骤卡。',
        createdAt: '19:16',
      },
      {
        id: 'conversation-demo-cards-message-9',
        role: 'assistant',
        content: '这是烹饪步骤。',
        createdAt: '19:16',
        cards: [buildCookingGuideCard(tomatoRecipe)],
      },
    ],
  },
  {
    id: 'conversation-1',
    title: '周五晚饭安排',
    statusText: '候选菜已经整理好了，等你拍板',
    preview: '候选菜已经缩到三道，正在确认今天走哪条口味线。',
    updatedAt: '3 分钟前',
    stage: 'planning',
    intentLabel: '推荐中',
    taskSummary: '',
    quickPrompts: ['告诉我更下饭的选项', '需要准备哪些食材', '再推荐一道汤菜'],
    messages: [
      {
        id: 'conversation-1-message-1',
        role: 'assistant',
        content:
          '今天我们更像是在推进一条做饭任务，而不是普通闲聊。我先根据你“工作日、想快一点、不要太油”的约束收缩一下范围。',
        createdAt: '18:42',
      },
      {
        id: 'conversation-1-message-2',
        role: 'user',
        content: '想吃一点香的，但不要太重口，最好 25 分钟内能吃上。',
        createdAt: '18:43',
      },
      {
        id: 'conversation-1-message-3',
        role: 'assistant',
        content: '给你整理了几道更适合现在做的菜。',
        createdAt: '18:43',
        cards: [buildRecommendationCard([mockRecipes[1], mockRecipes[3], mockRecipes[5]])],
      },
    ],
  },
  {
    id: 'conversation-2',
    title: '冰箱清库存',
    statusText: '食材比对完成，差一点就能开做',
    preview: '已识别现有食材，正在判断哪些东西缺口最关键。',
    updatedAt: '16 分钟前',
    stage: 'shopping',
    intentLabel: '备料中',
    currentRecipe: dryPotRecipe.name,
    taskSummary: '',
    quickPrompts: ['把缺料清单列出来', '按现有食材重算菜谱', '能不能换一道菜'],
    messages: [
      {
        id: 'conversation-2-message-1',
        role: 'user',
        content: '冰箱里有半颗花菜、鸡腿肉、两个青椒和一点豆瓣酱，可以做什么？',
        createdAt: '18:07',
      },
      {
        id: 'conversation-2-message-2',
        role: 'assistant',
        content:
          '我先按你手头的东西过一遍备料情况，看看能不能直接开做。',
        createdAt: '18:08',
        cards: [buildPantryCard(dryPotRecipe)],
      },
    ],
  },
  {
    id: 'conversation-3',
    title: '豆角焖面进行中',
    statusText: '下一步准备开盖拌面',
    preview: '当前在焖煮阶段，后面只需要继续跟进步骤和计时提醒。',
    updatedAt: '1 小时前',
    stage: 'cooking',
    intentLabel: '烹饪中',
    currentRecipe: braisedNoodlesRecipe.name,
    taskSummary: '',
    quickPrompts: ['下一步做什么', '帮我记 5 分钟', '面条太干怎么办'],
    messages: [
      {
        id: 'conversation-3-message-1',
        role: 'assistant',
        content:
          '现在已经在烹饪中了，我们就盯着当前步骤和时间往下走。',
        createdAt: '17:15',
        cards: [buildCookingGuideCard(braisedNoodlesRecipe, 3)],
      },
    ],
  },
]

export function buildMockConversations(): ConversationRecord[] {
  return structuredClone(seedConversations)
}
