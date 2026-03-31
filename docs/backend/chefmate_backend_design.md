# ChefMate 后端设计说明

## 1. 本次设计的核心目标

这版后端围绕一个核心原则展开：**让 ChefMate 真正成为“任务驱动的烹饪智能体”**，而不是一个普通聊天接口。

需要同时满足下面几件事：

1. 一个用户可以有多个对话。
2. 一个对话里可以经历多个任务，但同一时刻只能有一个活动任务。
3. 一个任务要能完整经历：`无任务 -> 推荐中 -> 备料中 -> 烹饪中 -> 无任务`。
4. 任务里的菜谱必须是**动态快照**，不能直接引用菜谱库里的静态数据。
5. 模型必须通过 `LangChain + LangGraph` 驱动，并通过工具真实读写后端状态。
6. 消息必须支持流式输出，并能带一张结构化卡片给前端渲染。
7. 前端不能再依赖 mock 数据，所有界面数据都来自真实接口。

## 2. 核心领域模型

### 2.1 用户

用户长期记忆由三部分组成：

- 偏好标签
- 偏好文本
- 历史任务

标签不单独自定义新字典，直接约束到现有 `recipe_tag` 表，保证和菜谱推荐体系使用同一份标签语义。

### 2.2 对话

对话负责承载：

- 标题 `title`
- 当前阶段 `stage`
- 当前展示菜名 `current_recipe_name`
- 当前快捷建议 `suggestions`
- 压缩摘要 `summary_text`
- 当前活动任务 `current_task_id`
- 消息列表

短期记忆由三块组成：

- 最近 `n` 条消息滑动窗口
- 对较远消息的压缩摘要
- 当前任务的完整动态菜谱快照

### 2.3 任务

任务是整个智能体流程的主轴。

任务表里保存：

- 所属用户、所属对话
- 当前阶段
- 当前状态
- 是否记录到历史任务
- `recipe_snapshot_json`
- 来源菜谱 `source_recipe_id`
- 完成/取消结果

这里的 `recipe_snapshot_json` 是关键。

它不是菜谱库里的静态 recipe，而是**任务执行时自己的动态副本**，里面除了基础做法，还会记录：

- 食材准备状态
- 步骤完成状态
- 当前步骤推进情况
- 用户和模型在本次任务里对菜谱的增删改

## 3. 阶段流转设计

### 3.1 阶段枚举

后端对前端直接暴露以下阶段值，和前端文档保持一致：

- `idea`: 无任务 / 闲聊
- `planning`: 推荐中
- `shopping`: 备料中
- `cooking`: 烹饪中

### 3.2 阶段校验

为了防止模型口头推进但状态不一致，阶段推进全部通过 `TaskService` 统一完成，并带校验：

- `idea -> planning`
  - 创建活动任务
- `planning -> shopping`
  - 必须已经有完整任务菜谱
- `shopping -> cooking`
  - 必需食材必须全部 `ready`
- `cooking -> idea`
  - 正常完成时，全部步骤必须 `done`
- 任意取消
  - 推荐中取消：不记入历史
  - 备料中/烹饪中取消：记入历史

## 4. 智能体编排设计

## 4.1 为什么用 LangGraph

这里没有把所有逻辑塞进一个大函数，而是拆成：

- `AgentTurnContext`: 单轮运行上下文
- `build_stage_prompt`: 阶段提示词装配
- `build_stage_tools`: 阶段工具白名单
- `build_agent_graph`: 基于 `create_react_agent` 构建单轮 ReAct 图

这样做的好处：

- 阶段约束清晰
- 工具白名单清晰
- 每轮运行输入输出边界清晰
- 后续做阶段能力测试时更容易定位

### 4.2 单轮执行流程

单轮消息处理流程如下：

1. 用户消息先落库。
2. 读取用户档案、对话摘要、近期消息、历史任务、当前任务快照。
3. 构建 `AgentTurnContext`。
4. 按当前阶段生成系统提示词和工具集合。
5. 用 `LangGraph create_react_agent` 执行工具调用循环。
6. 工具在执行中直接真实修改数据库状态。
7. 最终生成 assistant 文本。
8. 统一组装卡片、suggestions、title，并把 assistant 消息落库。

### 4.3 工具分层

#### 通用工具

- `get_user_memory`
- `update_user_memory`

#### 无任务阶段

- `start_recommendation_task`

#### 推荐中

- `recommend_recipes`
- `create_or_update_task_recipe`
- `show_recipe_detail_card`
- `recognize_image_ingredients`
- `advance_to_preparation`
- `cancel_recommendation_task`

#### 备料中

- `update_task_recipe_for_preparation`
- `show_pantry_card`
- `advance_to_cooking`
- `rollback_to_recommendation`
- `cancel_preparation_task`

#### 烹饪中

- `update_task_recipe_for_cooking`
- `show_cooking_card`
- `complete_cooking_task`
- `rollback_to_preparation`
- `cancel_cooking_task`

### 4.4 菜谱更新白名单

为了避免模型在错误阶段乱改结构，菜谱更新做了阶段白名单：

- 推荐中：通过整份覆盖方式创建/替换任务菜谱
- 备料中：允许改食材和步骤相关字段
- 烹饪中：只允许改步骤相关字段

对应实现集中在：

- `/mnt/d/ChefMate/backend/app/utils/recipe_snapshot.py`
- `/mnt/d/ChefMate/backend/app/services/task_service.py`

## 5. 流式输出与卡片协议

### 5.1 流式输出

消息流式接口：

- `POST /api/conversations/{conversation_id}/messages/stream`

返回 `text/event-stream`，事件类型：

- `status`
- `token`
- `final`
- `error`

其中：

- `status` 用来显示工具执行中的中间提示
- `token` 是 assistant 正文的增量文本
- `final` 带最终结构化快照

### 5.2 单消息单卡片

遵守前端约定：

- 一条消息最多携带一张卡片
- 一个对话中同类型卡片只保留最新一张
- 新卡片出现时，旧卡片会在对话历史里被覆盖隐藏

后端存储方式是：

- `conversation_message.card_type`
- `conversation_message.card_payload_json`

前端收到对话详情后，会按类型去重展示。

### 5.3 当前支持的四类卡片

- `recipe-recommendations`
- `recipe-detail`
- `pantry-status`
- `cooking-guide`

卡片组装统一由后端公共 builder 负责，避免让每个工具直接手拼前端 JSON：

- `/mnt/d/ChefMate/backend/app/domain/cards.py`

## 6. 数据库设计

本次新增 SQL 文件：

- `/mnt/d/ChefMate/data/database/chefmate_backend_schema.sql`

新增核心表如下：

- `chefmate_user`
- `user_preference_tag`
- `auth_session`
- `uploaded_asset`
- `conversation`
- `conversation_task`
- `conversation_message`
- `conversation_message_attachment`

### 6.1 与现有菜谱库的关系

- 静态菜谱仍来自 `recipe / recipe_ingredient / recipe_step / recipe_tag*`
- 用户偏好标签直接引用 `recipe_tag`
- 任务里的动态菜谱走 `conversation_task.recipe_snapshot_json`

这保证了：

- 推荐系统和用户长期偏好标签共享一套标签语义
- 任务阶段对菜谱的修改不会污染菜谱库

## 7. 认证与上传设计

### 7.1 认证

认证改成真实后端会话：

- 注册 / 登录返回 token
- 前端把 token 存到本地登录态
- 后续请求走 `Authorization: Bearer <token>`

接口：

- `POST /api/auth/register`
- `POST /api/auth/login`
- `GET /api/auth/me`
- `POST /api/auth/logout`

### 7.2 图片上传

为满足“先上传，再识别”的要求，增加本地对象存储式接口：

- `POST /api/files/images`

上传后会返回：

- `file_id`
- `file_url`
- `preview_url`

然后用户消息把图片作为附件发给对话接口；模型如果需要识别，会在推荐阶段调用图片识别工具。

## 8. 前端对接说明

这次前端已去掉对 mock 数据的实际依赖，改为真实接口：

- 登录/注册
- 当前用户档案
- 标签目录
- 对话列表
- 对话详情
- 创建对话
- 发送消息
- 流式消息
- 图片上传
- 菜谱列表
- 菜谱详情

卡片动作也不再靠自然语言字符串，而是结构化回传：

- `view_recipe`
- `try_recipe`
- `ingredients_ready`

## 9. 测试预埋点

虽然这次没有正式开发测试系统，但现在的结构已经为后续测试留好了插口：

### 9.1 阶段能力测试

可以基于阶段固定的工具白名单来测试：

- 某阶段是否调用了不该调用的工具
- 某阶段是否完成了目标

### 9.2 状态流转测试

可以围绕 `TaskService` 直接测：

- 阶段推进校验是否正确
- 回滚/取消/完成是否正确写库

### 9.3 端到端测试

可以用数据集驱动消息输入，验证：

- 工具调用顺序
- 最终阶段
- 最终任务快照
- 卡片类型
- assistant 输出

## 10. 当前实现对应的关键文件

### 后端

- `/mnt/d/ChefMate/backend/app/services/conversation_service.py`
- `/mnt/d/ChefMate/backend/app/services/task_service.py`
- `/mnt/d/ChefMate/backend/app/agent/tools.py`
- `/mnt/d/ChefMate/backend/app/agent/graph.py`
- `/mnt/d/ChefMate/backend/app/agent/prompts.py`
- `/mnt/d/ChefMate/backend/app/utils/recipe_snapshot.py`
- `/mnt/d/ChefMate/backend/app/domain/cards.py`
- `/mnt/d/ChefMate/backend/app/api/routes/conversations.py`

### 前端

- `/mnt/d/ChefMate/frontend/src/App.vue`
- `/mnt/d/ChefMate/frontend/src/lib/api.ts`
- `/mnt/d/ChefMate/frontend/src/components/ComposerPanel.vue`
- `/mnt/d/ChefMate/frontend/src/components/cards/*`

## 11. 后续优先建议

下一步建议按这个顺序继续：

1. 先把后端和前端在你的环境里跑通，重点验证完整主流程。
2. 然后补测试系统，优先覆盖阶段流转和工具使用。
3. 接着再考虑记忆摘要优化、推荐策略优化、图片识别效果优化。

如果后面你要继续扩展能力，我建议优先保持现在这个边界：

- 状态推进走 `TaskService`
- 卡片组装走 `domain/cards.py`
- 单轮执行走 `ConversationService + AgentTurnContext`
- LangGraph 只负责单轮 ReAct 编排

这样我们后面迭代起来会比较稳。 
