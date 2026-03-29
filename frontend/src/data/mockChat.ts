import type {
  ConversationRecord,
  NavShortcut,
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
  focus: '本周目标：20 分钟内完成两顿晚餐',
  preferences: ['偏清淡', '不吃香菜', '常用空气炸锅'],
  email: 'chefmate.demo@example.com',
  availableTime: '工作日晚饭 30 分钟内，周末可慢一点',
  kitchenMode: '更偏家常快手，也愿意尝试一点新菜',
  tools: ['空气炸锅', '不粘锅', '电饭煲', '小烤箱'],
}

const seedConversations: ConversationRecord[] = [
  {
    id: 'conversation-1',
    title: '周五晚饭安排',
    statusText: '候选菜已经整理好了，等你拍板',
    preview: '候选菜已经缩到三道，正在确认今天走哪条口味线。',
    updatedAt: '3 分钟前',
    stage: 'planning',
    intentLabel: '推荐中',
    taskSummary: '用户想在 25 分钟内做一顿偏家常但不要太油的晚饭。',
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
        content:
          '可以，右边这组卡片就是模拟后续 API 返回后的展示方式。推荐理由、时间、热量这些字段都已经按任务型聊天界面拆好了。',
        createdAt: '18:43',
        cards: [
          {
            type: 'recipe-recommendations',
            title: '第一轮候选菜',
            summary: '更偏家常、易成功，同时保留一点香气层次。',
            recipes: [
              {
                id: 'recipe-1',
                name: '蒜香鸡腿排配煎时蔬',
                duration: '22 分钟',
                difficulty: '轻松上手',
                calories: '498 kcal / 1 人份',
                fitReason: '煎锅路线更快，调味也不容易失控。',
                highlights: ['高成功率', '锅具简单', '适合下班后'],
              },
              {
                id: 'recipe-2',
                name: '黑椒杏鲍菇牛肉粒',
                duration: '25 分钟',
                difficulty: '中等',
                calories: '530 kcal / 2 人份',
                fitReason: '香气足但不重辣，适合想吃得更满足一点。',
                highlights: ['口味平衡', '卖相好', '适合分享'],
              },
              {
                id: 'recipe-3',
                name: '照烧三文鱼饭',
                duration: '18 分钟',
                difficulty: '简单',
                calories: '460 kcal / 1 人份',
                fitReason: '更清爽，适合赶时间时直接上手。',
                highlights: ['时间短', '清爽不腻', '摆盘友好'],
              },
            ],
          },
        ],
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
    currentRecipe: '干锅花菜鸡腿肉',
    taskSummary: '以现有食材为主，尽量少买，优先判断是否能直接开做。',
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
          '这类消息以后很适合接图片识别和食材比对接口。现在我先用死数据展示一下“备料检查卡”在聊天流里的样子。',
        createdAt: '18:08',
        cards: [
          {
            type: 'pantry-status',
            title: '现有食材状态',
            summary: '会优先判断能否直接做，再决定是补买还是换菜。',
            completion: 0.68,
            checklist: [
              {
                ingredient: '鸡腿肉',
                amount: '300g',
                status: 'ready',
                note: '完全够做一份主菜，可以直接进入腌制。',
              },
              {
                ingredient: '花菜',
                amount: '半颗',
                status: 'ready',
                note: '建议切小朵，能更快熟透。',
              },
              {
                ingredient: '蒜末',
                amount: '2 瓣',
                status: 'missing',
                note: '如果没有蒜，香气层次会薄一些。',
              },
              {
                ingredient: '豆瓣酱',
                amount: '1 勺',
                status: 'low',
                note: '库存不足时建议再补一点清水和生抽做平衡。',
              },
            ],
            actions: ['生成补买清单', '换成更省料的菜', '直接按现有食材开做'],
          },
        ],
      },
    ],
  },
  {
    id: 'conversation-3',
    title: '红烧排骨进行中',
    statusText: '下一步准备开盖收汁',
    preview: '当前在焖煮阶段，后面只需要继续跟进步骤和计时提醒。',
    updatedAt: '1 小时前',
    stage: 'cooking',
    intentLabel: '烹饪中',
    currentRecipe: '红烧排骨',
    taskSummary: '用户已开火，需要跟踪步骤、火候和计时。',
    quickPrompts: ['下一步做什么', '帮我记 5 分钟', '排骨太柴怎么办'],
    messages: [
      {
        id: 'conversation-3-message-1',
        role: 'assistant',
        content:
          '烹饪阶段的核心不是再给大量介绍，而是要让用户一眼看到“当前步骤、剩余时间、注意事项”。所以页面会把重点卡片放在消息体里靠近输入区的位置。',
        createdAt: '17:15',
        cards: [
          {
            type: 'cooking-guide',
            title: '焖煮阶段进度',
            summary: '前端可直接根据步骤状态高亮，并触发本地倒计时提醒。',
            currentStep: 3,
            totalSteps: 6,
            timers: [
              {
                label: '焖煮提醒',
                duration: '05:00',
              },
              {
                label: '收汁提醒',
                duration: '01:30',
              },
            ],
            steps: [
              {
                title: '焯水去血沫',
                detail: '冷水下锅，煮开后捞出冲净。',
                duration: '5 分钟',
                status: 'done',
              },
              {
                title: '炒糖色',
                detail: '小火慢熬，颜色到琥珀色后立刻下排骨。',
                duration: '2 分钟',
                status: 'done',
              },
              {
                title: '加水焖煮',
                detail: '没过排骨后盖盖焖煮，保持小火轻沸。',
                duration: '20 分钟',
                status: 'current',
              },
              {
                title: '开盖收汁',
                detail: '收汁阶段记得勤翻动，避免糊底。',
                duration: '3 分钟',
                status: 'upcoming',
              },
              {
                title: '试味调盐',
                detail: '最后再判断咸淡，避免前面越煮越咸。',
                duration: '1 分钟',
                status: 'upcoming',
              },
              {
                title: '装盘撒葱花',
                detail: '如果用户不吃香菜，这里只给葱花方案。',
                duration: '30 秒',
                status: 'upcoming',
              },
            ],
          },
        ],
      },
    ],
  },
]

export function buildMockConversations(): ConversationRecord[] {
  return structuredClone(seedConversations)
}
