# ChefMate CLI Demo

这是一个放在 `demo/agent` 下的基础完整命令行 demo，用来验证 ChefMate 的核心闭环：

1. 推荐吃什么
2. 确定要做的菜
3. 明确所需食材
4. 判断现有食材是否够
5. 缺料时给出补买或换菜建议
6. 食材齐备后进入分步骤烹饪指导

## 技术路线

- 以 LangChain Agent 为主入口
- 以显式会话状态和工具函数保证流程可控
- 仅支持在线模型调用

如果依赖未安装，或没有配置模型访问环境变量，程序会在启动时直接报错并退出。

## 安装依赖

建议在 `demo/agent` 目录下创建并激活 Python 虚拟环境后安装：

```bash
pip install -e .
```

如果你要启用真正的 LangChain + OpenAI 模型调用，再额外配置：

```bash
export OPENAI_API_KEY=你的_key
export CHEFMATE_MODEL=gpt-4o-mini
export BASEURL=https://你的兼容网关/v1
```

说明：

- `BASEURL` 用来接兼容 OpenAI 协议的中转网关或模型平台
- 如果你直接连 OpenAI 官方接口，这个变量可以不配
- 代码里也兼容 `OPENAI_BASE_URL` 和 `CHEFMATE_BASE_URL`

## 运行

```bash
python main.py
```

或者：

```bash
python -m agent_app.cli
```

## 可用命令

- `/help`
- `/recipes`
- `/profile`
- `/status`
- `/reset`
- `/exit`

## 推荐体验路径

### 路径 1：从推荐开始

```text
今晚不知道吃什么，想清淡一点，最好 20 分钟内
那就做番茄炒蛋
我有番茄、鸡蛋、葱花
开始做
下一步
```

### 路径 2：从指定菜品开始

```text
我想做青椒土豆丝，需要准备什么
我有土豆、盐、油
缺什么
```

### 路径 3：从现有食材开始

```text
我有鸡蛋、米饭、葱花，能做什么
```

## 当前边界

- 首版只做文本 CLI，不做真实图片识别
- 食材识别以文本列举模拟，但接口设计保留了扩展空间
- 内置菜谱是小规模样本数据，重点是验证流程，不是覆盖完整菜谱库
