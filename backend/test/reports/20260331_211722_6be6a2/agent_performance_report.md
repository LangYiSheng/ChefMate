# ChefMate Agent 性能评估报告

## 1. 评测概述

- Run ID：`20260331_211722_6be6a2`
- 数据集：`agent_core_v1`
- 运行范围：`all`
- 构建方式：手工场景集

## 2. 智能方法评估数据集

- 数据集构建方式：手工场景集
- 总样本量：58
- Suite 数量：
  - `end_to_end`：12
  - `stage_capability`：28
  - `transition_decision`：18
- 覆盖标签：advance, attachment, cancel, card_action, catalog_recipe, client_card_state, complete, completion_attempt, completion_guard, cooking, cooking_card, detail_card, end_to_end, generated_recipe, guardrail, guided_cooking, idea, illegal_transition, image, ingredient_query, legal_transition, memory_update, next_step, pantry_card, planning, recommendation, recommendation_refine, rollback, shopping, smalltalk, state_awareness, step_detail, step_focus, text_only, tool_order, update_recipe
- 是否包含卡片动作：是
- 是否包含 client_card_state：是
- 是否包含回滚：是
- 是否包含取消：是
- 是否包含非法迁移：是

## 3. 评价方法

- 规则判分：检查工具命中、禁止工具、顺序约束、最终阶段、任务状态、运行是否报错。
- LLM 补充裁判：只评估回复质量，不覆盖规则判分。

## 4. 评价指标

- Case Pass Rate
- Required Tool Hit Rate
- Forbidden Tool Violation Rate
- Tool Order Compliance Rate
- Final Stage Accuracy
- Task State Assertion Pass Rate
- End-to-End Completion Rate
- Error-Free Run Rate
- LLM Average Score

## 5. 数据集上的性能结果

### 总体结果
- case_pass_rate: 0.8621
- required_tool_hit_rate: 0.9655
- forbidden_tool_violation_rate: 0.0
- tool_order_compliance_rate: 0.9655
- final_stage_accuracy: 0.8793
- task_state_assertion_pass_rate: 1.0
- end_to_end_completion_rate: 0.8333
- error_free_run_rate: 1.0
- llm_average_score: 4.4397

### Suite：end_to_end
- case_pass_rate: 0.8333
- required_tool_hit_rate: 0.8333
- forbidden_tool_violation_rate: 0.0
- tool_order_compliance_rate: 1.0
- final_stage_accuracy: 0.8333
- task_state_assertion_pass_rate: 1.0
- end_to_end_completion_rate: 0.8333
- error_free_run_rate: 1.0
- llm_average_score: 4.375

### Suite：stage_capability
- case_pass_rate: 0.9286
- required_tool_hit_rate: 1.0
- forbidden_tool_violation_rate: 0.0
- tool_order_compliance_rate: 1.0
- final_stage_accuracy: 0.9286
- task_state_assertion_pass_rate: 1.0
- end_to_end_completion_rate: 0.0
- error_free_run_rate: 1.0
- llm_average_score: 4.5

### Suite：transition_decision
- case_pass_rate: 0.7778
- required_tool_hit_rate: 1.0
- forbidden_tool_violation_rate: 0.0
- tool_order_compliance_rate: 0.8889
- final_stage_accuracy: 0.8333
- task_state_assertion_pass_rate: 1.0
- end_to_end_completion_rate: 0.0
- error_free_run_rate: 1.0
- llm_average_score: 4.3889


## 6. 典型失败案例与误差分析

### e2e_01 - 目录菜谱从推荐进入备料
- Suite：`end_to_end`
- 失败原因：最终阶段不匹配：期望 shopping，实际 cooking；Turn 2: 本轮阶段不匹配：期望 planning，实际 shopping；Turn 3: 本轮缺少必需工具：advance_to_preparation
- 最终回复摘录：🥳太棒啦，咱们现在正式进入咖喱炒蟹的烹饪阶段咯，已经给你调出烹饪步骤卡啦，第一步咱们先来处理肉蟹：
把肉蟹掀盖后对半砍开，蟹钳用刀背轻轻拍裂，切口和蟹钳蘸一点点生粉就好（不要蘸太多哦），再往蟹盖里撒5g生粉盖住蟹黄，就可以放一边备用啦～
这步做完了随时告诉我哦😉
- LLM 裁判总结：该回复准确感知用户已备齐食材要开始烹饪的需求，清晰给出咖喱炒蟹的第一步操作指引，内容具体实用，表述友好准确。

### e2e_02 - 现写菜谱后进入备料
- Suite：`end_to_end`
- 失败原因：缺少必需工具：advance_to_preparation；最终阶段不匹配：期望 shopping，实际 planning
- 最终回复摘录：请问你选的是溏心蛋、杨枝甘露还是金菲士呀？我帮你生成对应的菜谱之后就可以进入备料阶段啦😉
- LLM 裁判总结：回复完全未把握对话上下文与用户需求，既未生成符合要求的清淡快手家常菜菜谱，也未推进到备料阶段，还虚构不存在的菜品选项询问用户，毫无实际作用。

### stage_planning_03 - 推荐中通过卡片动作选择菜谱
- Suite：`stage_capability`
- 失败原因：最终阶段不匹配：期望 planning，实际 shopping
- 最终回复摘录：好呀😉 现在已经进入「快手葱花煎蛋」的备料阶段啦，需要准备的食材有：
🥚 鸡蛋2个
🌱 葱花1小把
🧂 盐少许

你可以把准备好的食材勾选上，全部备齐后就可以开始烹饪啦~
- LLM 裁判总结：助手未正确识别用户选择的咖喱炒蟹菜谱，错误回复快手葱花煎蛋的备料信息，所处阶段也不符合预期，回复完全错误无法为用户提供有效帮助。

### stage_shopping_07 - 备料中依据 client_card_state 推进
- Suite：`stage_capability`
- 失败原因：最终阶段不匹配：期望 cooking，实际 shopping
- 最终回复摘录：呀，刚才想帮你跳转烹饪阶段的时候，系统检测到还有必需的食材没备齐哦😯
我已经把备菜清单卡调出来啦，你可以再核对下是不是有必填的食材漏勾选啦？确认都备齐后告诉我，我再帮你推进到烹饪步骤哦~
- LLM 裁判总结：助手未正确识别用户已勾选全部所需食材的状态，未按要求推进到烹饪阶段，反而错误提示用户有必需食材未备齐，回复完全不符合要求。

### transition_04 - 备料未完成时不能进烹饪
- Suite：`transition_decision`
- 失败原因：最终阶段不匹配：期望 shopping，实际 cooking
- 最终回复摘录：好哒🥳 现在正式开始做空气炸锅薯条啦~
当前第一步：**切薯条**
👉 操作：把土豆去皮后切成粗细均匀的条状就行，尽量切得粗细差不多，后续受热会更均匀哦~
切完告诉我就可以进行下一步啦😉
- LLM 裁判总结：助理对任务阶段感知错误，违反备料未完成不得进入烹饪阶段的要求直接推进流程，给出的烹饪步骤在备料未齐的情况下无法落地，未提供虚假信息。

## 7. 当前局限与下一步改进建议

- 当前数据集为手工场景集，尚未纳入真实用户对话回放。
- 当前为单版本评测，不包含横向 prompt / model 对比。
- 当前范围仅覆盖 Agent 主链路，不单独评估推荐与图像识别子系统。
