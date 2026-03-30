# ChefMate 前端实现细节须知

## 目的

这份文档用来约定前端后续接入 API 时需要的核心字段、消息结构、卡片结构和接口职责，避免开发过程中遗漏或误解。

## 重要约定

1. 每个对话都要维护一份最新的 `suggestions` 列表。
2. `suggestions` 不是静态字段，而是智能体每次返回新消息时都可能更新。
3. 前端应始终以“该对话最后一次智能体响应里返回的 `suggestions`”作为当前快捷建议。
4. 当前前端 mock 代码里使用的是 `quickPrompts` 命名，后续接 API 时应映射到后端真实字段 `suggestions`。
5. `taskSummary` 不作为用户界面展示字段，后续接口可以不返回；如果后端保留，也不应在前端主界面展示。
6. 每个对话里，同一种卡片类型只保留最新的一个实例；如果同类型卡片有更新，旧卡片应从原位置消失，新卡片只显示在最新消息位置。

## 对话对象建议结构

```ts
type ConversationStage = 'idea' | 'planning' | 'shopping' | 'cooking'

interface ConversationSummary {
  id: string
  title: string
  status_text: string
  stage: ConversationStage
  current_recipe_id?: number | null
  current_recipe_name?: string | null
  updated_at: string
  latest_suggestions: string[]
}
```

说明：

- `status_text` 用于侧边栏主标题。
- `stage + current_recipe_name` 用于界面上的阶段说明，例如 `烹饪中 · 番茄炒蛋`。
- `latest_suggestions` 是该对话当前可点击的建议列表。

## 消息返回建议结构

```ts
interface ConversationMessage {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  created_at: string
  attachments?: MessageAttachment[]
  suggestions?: string[]
  cards?: MessageCard[]
}

interface MessageAttachment {
  id: string
  kind: 'image'
  name: string
  preview_url: string
  file_url?: string
}
```

说明：

- 智能体每次返回消息时，都可以顺带返回新的 `suggestions`。
- 前端收到 assistant 消息后，应更新该对话维护中的“最新 suggestions”。
- 如果本次没有返回 `suggestions`，建议沿用上一条 assistant 消息留下的列表，除非后端明确返回空数组表示清空。
- 用户消息需要支持可选的 `attachments`，当前前端已支持单张图片预览、取消和随消息一起发送。

## 卡片结构建议

### 卡片实例维护原则

1. 一个对话内允许同时存在多种不同类型的卡片。
2. 同一种卡片类型在同一个对话里只保留一个最新实例。
3. 智能体后续返回同类型卡片时，前端应替换旧实例，而不是继续堆叠显示。
4. 卡片本身应携带当前状态，因此即使用户没有点击按钮，智能体也可以通过新一条结构化消息让卡片进入“下一步 / 上一步 / 更新内容 / 更新状态”。
5. 后端的工具调用设计也应遵守这条原则，不要把卡片当成一次性静态内容。

### 1. 推荐结果卡

```ts
interface RecipeRecommendationsCard {
  type: 'recipe-recommendations'
  title: string
  recipes: Array<{
    recipe_id: number
    name: string
    description: string
    tags: string[]
    difficulty: string
    estimated_minutes: number
    servings: number
    actions: Array<{
      id: string
      label: string
      action_type: 'view_recipe' | 'try_recipe'
      payload: {
        recipe_id: number
      }
    }>
  }>
}
```

### 2. 菜谱详情卡

```ts
interface RecipeDetailCard {
  type: 'recipe-detail'
  recipe: {
    id: number
    name: string
    description: string
    difficulty: string
    estimated_minutes: number
    servings: number
    tags: string[]
    ingredients: RecipeIngredient[]
    steps: RecipeStep[]
    tips?: string
  }
  actions: Array<{
    id: string
    label: '想尝试'
    action_type: 'try_recipe'
    payload: {
      recipe_id: number
    }
  }>
}
```

### 3. 备料检查卡

```ts
interface PantryStatusCard {
  type: 'pantry-status'
  title: string
  checklist: Array<{
    id: string
    ingredient: string
    amount: string
    status: 'ready' | 'pending'
    note?: string
    is_optional?: boolean
  }>
  actions: Array<{
    id: string
    label: '这些都备齐了'
    action_type: 'ingredients_ready'
    payload?: Record<string, never>
  }>
}
```

### 4. 烹饪步骤卡

```ts
interface CookingGuideCard {
  type: 'cooking-guide'
  title: string
  current_step: number
  total_steps: number
  steps: Array<{
    id: string
    title: string
    detail: string
    duration: string
    timer_seconds?: number | null
    notes?: string
    status: 'done' | 'current' | 'upcoming'
  }>
}
```

## 前端动作处理约定

卡片按钮不应该只回传一段自然语言字符串，后续建议统一成结构化动作：

```ts
interface CardActionEvent {
  action_type:
    | 'view_recipe'
    | 'try_recipe'
    | 'ingredients_ready'
    | 'open_timer'
  payload: Record<string, unknown>
}
```

前端收到动作后有两种处理方式：

1. 纯前端动作：例如打开菜谱详情页、注册计时器。
2. 发送消息动作：例如“这些都备齐了”、“想尝试”，前端可根据动作类型组装标准化请求发给后端。

## 计时器相关约定

1. 计时器以“每个对话一个当前计时器槽”为准。
2. 切换对话时，计时器仍继续运行。
3. 如果某个非当前对话正在倒计时，侧边栏应显示额外状态，例如：`烹饪中 · 番茄炒蛋 · 正在倒计时`。
4. 倒计时结束时，前端应自动切换到对应对话，并聚焦该对话中的烹饪步骤卡。
5. 用户设置里需要支持 `auto_start_step_timer` 开关，表示到达带计时步骤时是否自动开启计时器。

## 菜谱数据字段建议

菜谱详情建议优先与数据库结构保持一致，可参考：

- `/mnt/d/ChefMate/data/database/recipe_schema.sql`

建议前端重点依赖这些字段：

```ts
interface RecipeSummary {
  id: number
  name: string
  description: string
  difficulty: '简单' | '中等' | '困难'
  estimated_minutes: number
  servings: number
  tags: string[]
}

interface RecipeIngredient {
  id?: number | string
  ingredient_name: string
  amount_text: string
  amount_value?: number | null
  unit?: string | null
  is_optional?: boolean
  purpose?: string
  sort_order?: number
}

interface RecipeStep {
  id?: number | string
  step_no: number
  title?: string
  instruction: string
  timer_seconds?: number | null
  notes?: string
}
```

## 推荐接口建议

### 获取对话列表

`GET /api/conversations`

返回：`ConversationSummary[]`

### 获取单个对话详情

`GET /api/conversations/:conversationId`

返回：

```ts
interface ConversationDetail extends ConversationSummary {
  messages: ConversationMessage[]
}
```

### 创建新对话

`POST /api/conversations`

请求体可为空，或可选传入初始化场景：

```ts
{
  source?: 'manual' | 'recipe'
  recipe_id?: number
}
```

### 发送消息

`POST /api/conversations/:conversationId/messages`

```ts
interface SendMessageRequest {
  content?: string
  attachments?: Array<{
    kind: 'image'
    file_id?: string
    file_url?: string
    name?: string
  }>
  action?: CardActionEvent
}
```

返回建议：

```ts
interface SendMessageResponse {
  conversation: ConversationSummary
  message: ConversationMessage
}
```

如果后端采用流式返回，也建议在流结束时给出一份最终的结构化消息快照，包含：

- `content`
- `attachments`
- `cards`
- `suggestions`
- `status_text`
- `stage`
- `current_recipe_id`
- `current_recipe_name`

### 获取标签目录

`GET /api/profile/tag-catalog`

返回：

```ts
interface TagCatalogResponse {
  flavor: string[]
  method: string[]
  scene: string[]
  health: string[]
  time: string[]
  tool: string[]
}
```

## 认证页字段与约束

### 登录态门禁规则

1. 未登录时，用户只能访问认证页。
2. 工作台路由（聊天页、菜谱页、设置相关功能）都应视为受保护页面。
3. 登录或注册成功后，才能进入工作台。
4. 已登录用户再次访问认证页时，应自动跳回工作台。
5. 退出登录后，应立即清空前端登录态并返回认证页。

### 需要后端同步的登录态扩展字段

```ts
interface AuthSessionMeta {
  is_first_workspace_visit?: boolean
  has_completed_workspace_onboarding?: boolean
  profile_completed_at?: string | null
}
```

说明：

- `is_first_workspace_visit`
  建议由后端直接返回，用于判断当前用户是否第一次进入工作台。
- `has_completed_workspace_onboarding`
  用于记录用户是否已经完整走完首次欢迎模态框中的引导流程；只有完成后，后续才不再弹出。
- `profile_completed_at`
  用于判断用户是否已经完成最基本的个人信息、档案或设置初始化。

当前前端先用本地登录态临时承接这些信息，后续接入后端时应迁移为服务端可同步字段。

### 首次欢迎模态框流程约定

首次进入工作台时，应弹出全屏 onboarding 模态框，并按以下步骤推进：

1. 欢迎页：介绍 ChefMate 的主要能力与使用方式。
2. 个人信息页：至少采集账户显示名称。
3. 偏好档案页：允许用户选择长期记忆标签，并填写偏好文本；该步可跳过。
4. 设置页：确认是否允许 ChefMate 根据聊天过程自动更新长期记忆档案。
5. 设置页：提供 `auto_start_step_timer`，表示进入带计时的步骤时是否自动开启计时器。
6. 结束页：引导用户开启一个新对话，并在完成后把用户记为非首次访问。

### 登录表单

```ts
interface LoginRequest {
  username: string
  password: string
}
```

### 注册表单

```ts
interface RegisterRequest {
  username: string
  email?: string | null
  password: string
  confirm_password: string // 前端确认字段，后端可不必原样接收
}
```

### 用户名约束

1. 长度：4-20 位。
2. 必须以字母开头。
3. 仅允许字母、数字、下划线。
4. 正则建议：`^[A-Za-z][A-Za-z0-9_]{3,19}$`

### 密码约束

1. 长度：8-32 位。
2. 至少包含 1 个字母和 1 个数字。
3. 可使用常见符号：`~ ! @ # $ % ^ & * _ - + = . ?`
4. 正则建议：`^(?=.*[A-Za-z])(?=.*\d)[A-Za-z\d~!@#$%^&*_\-+=.?]{8,32}$`

### 邮箱约束

1. 邮箱为可选字段。
2. 如果填写，必须符合标准邮箱格式。

### 认证接口建议

#### 登录

`POST /api/auth/login`

```ts
interface LoginApiRequest {
  username: string
  password: string
}
```

#### 注册

`POST /api/auth/register`

```ts
interface RegisterApiRequest {
  username: string
  email?: string | null
  password: string
}
```

#### 当前用户信息

`GET /api/auth/me`

#### 退出登录

`POST /api/auth/logout`

### 获取用户档案

`GET /api/profile`

### 更新用户档案

`PATCH /api/profile`

```ts
interface UpdateProfileRequest {
  allow_auto_update?: boolean
  auto_start_step_timer?: boolean
  cooking_preference_text?: string
  tag_selections?: {
    flavor?: string[]
    method?: string[]
    scene?: string[]
    health?: string[]
    time?: string[]
    tool?: string[]
  }
  display_name?: string
  email?: string | null
}
```

### 菜谱列表

`GET /api/recipes`

支持查询参数：

- `keyword`
- `tag`
- `limit`
- `offset`

### 菜谱详情

`GET /api/recipes/:recipeId`

## 前端落地时的注意点

1. `suggestions` 一定要按对话维度维护，不能做成全局唯一一份。
2. 智能体返回新消息时，除了追加消息本身，还要同步更新：
   - `status_text`
   - `stage`
   - `current_recipe_id / current_recipe_name`
   - `latest_suggestions`
3. 卡片按钮后续最好统一走 `action_type + payload`，不要长期依赖自然语言拼接。
4. 计时器状态目前是前端维护，后续如果要多端同步，再考虑是否上升为服务端状态。
