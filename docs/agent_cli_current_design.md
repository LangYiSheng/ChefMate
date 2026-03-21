# ChefMate CLI Agent 当前设计说明

这份文档描述的是 **当前 `demo/agent` 中这版 LangChain CLI Agent 的实际设计**，目的不是定稿，而是为了在继续改代码前，先把现状完整摊开，方便后续统一校正思路。

文档重点覆盖：

1. 当前 agent 的整体结构
2. 当前阶段划分
3. 各阶段可使用的工具
4. 工具的调用方式
5. 上下文与记忆机制
6. 卡片与流式输出机制
7. 当前设计中的明显问题与待校正点

## 1. 当前整体结构

当前 CLI Agent 位于 [demo/agent](/mnt/d/ChefMate/demo/agent)，核心结构如下：

- [main.py](/mnt/d/ChefMate/demo/agent/main.py)
  - CLI 入口
- [agent_app/cli.py](/mnt/d/ChefMate/demo/agent/agent_app/cli.py)
  - 命令行交互主循环
- [agent_app/langchain_agent.py](/mnt/d/ChefMate/demo/agent/agent_app/langchain_agent.py)
  - LangChain agent 构建
  - 流式事件消费
  - 工具注册
- [agent_app/tools.py](/mnt/d/ChefMate/demo/agent/agent_app/tools.py)
  - 当前全部业务工具逻辑
- [agent_app/models.py](/mnt/d/ChefMate/demo/agent/agent_app/models.py)
  - 会话状态、用户画像、菜谱数据结构
- [agent_app/ui_schema.py](/mnt/d/ChefMate/demo/agent/agent_app/ui_schema.py)
  - 文本块、卡片块、回合结果结构
- [agent_app/cli_renderer.py](/mnt/d/ChefMate/demo/agent/agent_app/cli_renderer.py)
  - CLI 端的流式文本和卡片渲染
- [agent_app/data/recipes.json](/mnt/d/ChefMate/demo/agent/agent_app/data/recipes.json)
  - 当前 demo 使用的本地结构化菜谱数据

当前实现不是数据库驱动，也不是多服务协同，而是：

- 本地结构化数据
- LangChain agent
- 一组 Python 工具函数
- 一套 CLI 输出协议

## 2. 当前阶段划分

当前阶段状态定义在 [models.py](/mnt/d/ChefMate/demo/agent/agent_app/models.py) 的 `SessionStage` 中：

- `DISCOVERY`
  - 需求澄清阶段
- `RECOMMENDATION`
  - 菜品推荐阶段
- `PREPARATION`
  - 备料确认阶段
- `COOKING`
  - 烹饪指导阶段
- `COMPLETE`
  - 当前菜品流程完成阶段

### 2.1 当前阶段流转逻辑

当前代码里的实际主线大致是：

1. 用户表达“吃什么 / 推荐一下”
2. agent 倾向调用 `recommend_dishes`
3. 用户确认某道菜
4. agent 倾向调用 `get_recipe_requirements`
5. 用户提供现有食材
6. agent 倾向调用 `check_ingredients`
7. 若缺料，再调用：
   - `suggest_missing_items`
   - `suggest_alternative_dishes`
8. 若食材齐全，则调用：
   - `start_cooking`
   - 后续通过 `next_cooking_step` / `answer_cooking_question` 推进

### 2.2 当前阶段特点

当前阶段并不是由一个显式工作流引擎强控，而是：

- `SessionState.stage` 记录当前阶段
- 工具函数内部在执行时改写 `stage`
- agent 根据模型理解选择工具

也就是说，当前是：

- “状态 + 工具副作用”驱动阶段流转
- 不是“固定工作流节点 + 路由器”的严格流程

## 3. 当前工具列表

当前工具全部定义在 [langchain_agent.py](/mnt/d/ChefMate/demo/agent/agent_app/langchain_agent.py) 中，并实际逻辑落在 [tools.py](/mnt/d/ChefMate/demo/agent/agent_app/tools.py)。

### 3.1 推荐阶段相关

#### `recommend_dishes`

作用：

- 根据用户当前需求推荐 1 到 3 道菜

当前内部做法：

- 提取用户输入中的时间限制
- 提取用户输入中提到的食材
- 结合 `UserProfile`
- 在本地 `recipes.json` 中做简化版规则过滤和打分
- 生成推荐卡片
- 更新：
  - `state.stage = RECOMMENDATION`
  - `state.last_recommendations`

### 3.2 备料阶段相关

#### `get_recipe_requirements`

作用：

- 展示目标菜品所需食材和基础信息

当前内部做法：

- 根据菜名或别名定位菜谱
- 生成“菜谱信息卡”
- 更新：
  - `state.target_recipe`
  - `state.stage = PREPARATION`
  - `state.current_step_index = 0`

#### `check_ingredients`

作用：

- 根据用户提供的已有食材判断能否开做

当前内部做法：

- 对用户输入食材做简单归一化
- 与菜谱关键食材做比对
- 生成：
  - “备料检查卡” 或
  - “缺失食材卡”
- 更新：
  - `state.available_ingredients`
  - `state.missing_ingredients`
  - `state.target_recipe`
  - `state.stage = PREPARATION`

#### `suggest_missing_items`

作用：

- 给出缺料后的补买建议

当前内部做法：

- 根据 `state.missing_ingredients` 生成文本说明
- 目前是规则文本，不是结构化购物单

#### `suggest_alternative_dishes`

作用：

- 当缺料时，给出更容易完成的换菜建议

当前内部做法：

- 基于已有食材和菜谱关键食材做简单重叠排序
- 生成替代方案卡片

### 3.3 烹饪阶段相关

#### `start_cooking`

作用：

- 确认开始做菜，并进入第一个步骤

当前内部做法：

- 检查是否存在目标菜品
- 检查 `missing_ingredients` 是否为空
- 更新：
  - `state.stage = COOKING`
  - `state.current_step_index = 0`
- 调用 `current_step_text`

#### `next_cooking_step`

作用：

- 将步骤指针推进到下一步

当前内部做法：

- `current_step_index += 1`
- 再调用 `current_step_text`

#### `answer_cooking_question`

作用：

- 处理做菜过程中的追问

当前内部做法：

- 如果用户问“下一步”，走 `next_cooking_step`
- 如果用户问“当前做到哪”，走当前步骤返回
- 如果用户问“没有某调料怎么办”，走替代规则
- 如果用户问“还要多久”，返回粗略剩余步数估计

### 3.4 用户画像相关

#### `update_user_profile`

作用：

- 根据用户输入更新长期偏好

当前内部做法：

- 识别：
  - 口味偏好
  - 健康目标
  - 做饭熟练度
  - 忌口
  - 时间限制
- 更新 `UserProfile`

## 4. 当前工具调用方式

当前工具调用方式是：

- 在 [langchain_agent.py](/mnt/d/ChefMate/demo/agent/agent_app/langchain_agent.py) 中通过 `@tool` 暴露为 LangChain 工具
- 由 `create_agent(...)` 注册给 LangChain
- 模型根据用户输入自行选择工具

### 4.1 当前特点

- 现在是 **模型自治选工具**
- 没有做“阶段 -> 工具白名单”的硬约束
- 也没有显式的“某阶段禁止某些工具”

这意味着当前的工具访问控制是比较松的。

### 4.2 当前调用参数特点

当前工具大多接收的还是文本输入，例如：

- `recommend_dishes(user_request: str)`
- `check_ingredients(user_input: str)`
- `suggest_alternative_dishes(user_input: str)`

也就是说，很多工具的输入还是自然语言字符串，不是统一结构化对象。

这会带来两个结果：

- 工具实现方便
- 但工具边界不够清晰，也不够像生产服务接口

## 5. 当前上下文与记忆设计

### 5.1 当前会话状态

当前会话状态定义在 `SessionState`：

- `stage`
- `target_recipe`
- `available_ingredients`
- `missing_ingredients`
- `last_recommendations`
- `current_card_contexts`
- `current_step_index`
- `servings`
- `notes`
- `chat_history`

### 5.2 当前用户长期信息

当前长期画像定义在 `UserProfile`：

- `flavor_preferences`
- `dietary_restrictions`
- `health_goal`
- `cooking_skill_level`
- `max_cook_time`
- `available_tools`

### 5.3 当前模型上下文来源

当前模型每轮调用时，能拿到的上下文主要包括：

1. 先前的 `chat_history`
2. 当前用户输入
3. 如果存在卡片上下文，会额外插入一条 `SystemMessage`
4. 如果存在序号引用解析结果，也会额外插入一条 `SystemMessage`

### 5.4 当前卡片上下文记忆

当前设计里，卡片不只是显示层产物，也会被摘要后写入：

- `state.current_card_contexts`

写入时机：

- 每轮调用结束，构建 `TurnResult` 时

当前摘要内容大致包括：

- 卡片标题
- 副标题
- 标签
- 字段
- 列表项（前几项）

### 5.5 当前“第2个”这类引用处理

当前已经加入一层引用解析：

- 支持：
  - `第2个`
  - `第二个`
  - `第二道`
  - `第1+1个`

当前做法不是改写用户原话，而是：

- 计算出引用序号
- 找到 `last_recommendations` 中对应的菜名
- 额外插入一条系统上下文告诉模型：
  - 用户指的是哪一张推荐卡
  - 对应哪道菜

这一步是为了解决：

- 用户说“我想要第2个”
- 模型看不见 UI 卡片本体

的问题。

## 6. 当前卡片与流式输出设计

### 6.1 当前输出协议

定义在 [ui_schema.py](/mnt/d/ChefMate/demo/agent/agent_app/ui_schema.py)：

- `TextBlock`
- `CardBlock`
- `TraceStep`
- `TurnResult`

当前一轮输出由：

- 若干文本块
- 若干卡片块
- 可选 trace 步骤

组成。

### 6.2 当前卡片类型

当前已经出现的卡片类型包括：

- `recipe_recommendation`
  - 推荐菜品卡
- `recipe_detail`
  - 菜谱信息卡
- `ingredient_check`
  - 备料通过卡
- `missing_ingredients`
  - 缺失食材卡
- `alternative_recipes`
  - 替代方案卡
- `cooking_step`
  - 当前步骤卡

### 6.3 当前流式机制

当前在 [langchain_agent.py](/mnt/d/ChefMate/demo/agent/agent_app/langchain_agent.py) 中已经接入：

- `stream_mode=["custom", "updates", "messages"]`

当前这三类流的用途是：

- `messages`
  - 模型 token 流式文本
- `updates`
  - 工具调用事件 / 工具完成事件
- `custom`
  - 工具内部主动发出的卡片与 trace 事件

### 6.4 当前 CLI 端显示策略

当前 [cli_renderer.py](/mnt/d/ChefMate/demo/agent/agent_app/cli_renderer.py) 的策略是：

- `trace`
  - 不展示给用户
- `tool_call`
  - 展示为中文业务动作
- `tool_result`
  - 不展示
- `card`
  - 缓存后在文本后统一渲染
- `text_delta`
  - 按字符流式打印

## 7. 当前数据来源

当前卡片数据 **不是数据库读取**，而是：

- 来自 [recipes.json](/mnt/d/ChefMate/demo/agent/agent_app/data/recipes.json) 里的本地 demo 数据

这意味着当前设计是：

- “本地样例数据驱动的 agent demo”

不是：

- “真实数据库 + 检索层 + 服务层”的正式架构

## 8. 当前设计的主要问题

下面这些是当前实现里比较明显、而且值得后续校正的点。

### 8.1 阶段控制还不够硬

当前是：

- 工具内部自己改 `stage`
- 模型自己决定调用哪一个工具

问题是：

- 缺少显式阶段路由
- 缺少按阶段限制工具集合
- 容易出现“阶段不清、工具乱跳”

### 8.2 工具粒度和概要设计并不完全一致

概要设计里更偏业务模块：

- 日常聊天
- 获取菜品建议
- 食材准备
- 烹饪指导

但当前工具是实现导向的：

- `recommend_dishes`
- `check_ingredients`
- `start_cooking`

这会导致：

- 用户可见动作和代码层动作之间存在偏差
- 工具调用展示容易显得“不像产品行为”

### 8.3 工具输入大多仍是自然语言字符串

当前很多工具仍是：

- 输入一段文本
- 内部自己再解析

而不是：

- 明确结构化参数对象

问题是：

- 工具边界不清晰
- 后续对接前后端接口时会比较难收口

### 8.4 卡片是“展示产物”，不是“业务对象”

虽然当前已经把卡片摘要写回上下文，但本质上：

- 业务逻辑先出结果
- 再拼卡片

这意味着卡片还不是领域层的一等对象。

后果是：

- 上下文同步容易漏
- CLI / Web / 模型上下文三者可能出现不一致

### 8.5 当前记忆只有会话内，没有持久化

当前：

- `UserProfile` 是本地样例
- `SessionState` 是内存态

所以没有：

- 跨会话持久记忆
- 用户真实长期偏好存储
- 历史任务恢复

### 8.6 当前没有真正的“日常聊天模块”

概要设计中把“日常聊天”作为一级模块，但当前实现里：

- 聊天本质上只是模型自由回复
- 没有单独设计“闲聊转任务”的明确路由策略

### 8.7 当前没有图片能力

概要设计中食材准备模块应支持：

- 图片识别食材种类

但当前 demo 还没有：

- 图片输入
- 图片识别工具
- 图片上下文入模

### 8.8 当前“引用理解”只是补丁，不是完整机制

目前只补了：

- `第2个`
- `第二道`
- `第1+1个`

但更自然的说法还没系统支持，比如：

- “上面中间那个”
- “刚才第二个”
- “前两个里第二个”
- “那个清爽一点的”

## 9. 我建议你接下来重点校正的点

为了后面重新修代码更稳，我建议优先拍板下面这些问题：

1. 当前 agent 是否要改成“阶段驱动 + 每阶段工具白名单”的设计
2. 工具命名和工具粒度是否要严格按概要设计的业务模块来重构
3. 工具输入是否要改成结构化参数，而不是自然语言字符串
4. 卡片是否要上升为正式业务对象，而不是单纯 UI 渲染块
5. 当前上下文记忆里，哪些内容应该进入模型上下文，哪些只属于前端展示
6. “第2个 / 刚才那个 / 中间那个”这类 UI 指代，是否要独立做一层引用解析器
7. 推荐模块是否应该拆成：
   - 需求解析
   - 推荐候选生成
   - 推荐结果呈现
   这三个更清晰的步骤
8. 食材准备模块是否应该拆成：
   - 展示所需食材
   - 录入现有食材
   - 判断缺料情况
   - 生成补买建议
   这几个清晰动作

## 10. 当前结论

当前这版 agent 已经具备一个“可跑的 CLI demo 骨架”，包括：

- LangChain 在线工具调用
- 流式输出
- 结构化卡片
- 会话状态
- 卡片上下文入模

但它离“按 ChefMate 产品思路严谨设计”的状态还有明显距离。

更准确地说，当前实现是：

- 一个已经开始向产品形态靠近的 demo

还不是：

- 一个经过清晰业务建模后的稳定 agent 设计

所以下一步最合理的动作，确实不是继续堆补丁，而是先把设计校正清楚，再按统一思路回改代码。
