# 菜谱结构化处理工具

这个目录用于把 `data/recipe_origin/dishes` 下的原始 Markdown 菜谱，逐个转换成结构化 JSON，并人工审核后保存。

## 目录说明

- `review_app.py`
  - 本地审核程序
- `prompt_template.md`
  - 发给模型的提示词模板
- `tag_catalog.json`
  - 固定标签全集
- `workspace/`
  - 程序运行后自动生成的状态与结果目录

## 运行前准备

设置以下环境变量：

- `OPENAI_BASE_URL`
- `OPENAI_API_KEY`
- `OPENAI_MODEL_NAME`

也可以直接填写同目录下的 `.env` 文件，程序启动时会自动读取。

另外需要先安装 `openai` Python 包。

可选环境变量：

- `OPENAI_TIMEOUT_SECONDS`
- `OPENAI_TEMPERATURE`
- `OPENAI_USE_JSON_MODE`

说明：

- 如果你用的是 OpenAI 官方或兼容得比较好的接口，`OPENAI_USE_JSON_MODE` 保持默认即可
- 如果你的自定义 `base_url` 不支持 `response_format={"type":"json_object"}`，就把它设为 `0`
- 当前程序会优先尝试 JSON mode；如果接口明确返回不支持 `json_object`，会自动退回普通文本 JSON 模式
- 当前程序仅使用 `openai` Python SDK 发起请求

## 启动方式

```bash
python data/recipe_origin/processor/review_app.py
```

启动后默认监听：

- [http://127.0.0.1:8765](http://127.0.0.1:8765)

## 审核流程

程序会：

1. 扫描 `data/recipe_origin/dishes` 下所有 `.md` 文件
2. 按固定顺序编号
3. 左侧展示原始 Markdown
4. 右侧展示模型转换后的结构化 JSON
5. 支持：
   - `生成/重试`
   - `批量生成`
     - 可设置批量条数
     - 可设置并发数
   - `校验`
   - `通过`
   - `拒绝`
   - `上一条`
   - `下一条`

## 断点续跑

程序会把审核状态写入：

- `workspace/review_state.json`

通过后的 JSON 会保存到：

- `workspace/approved/`

拒绝记录会保存到：

- `workspace/rejected/`

重新打开程序后，会优先回到当前未处理的下一条。

## 当前内置校验

程序会对结构化 JSON 做基础校验，包括：

- 顶层字段是否完整
- `tags` 中的标签是否都来自固定标签集合
- `difficulty` 是否合法
- `tags.tool` 是否都来自固定厨具集合
- `estimated_minutes` 与 `tags.time` 是否大体一致
- `ingredients`、`steps`、`tips` 的基本结构是否合法

说明：

- 页面中的“校验错误”会阻止通过
- 页面中的“校验提醒”不会阻止通过，但建议人工确认
