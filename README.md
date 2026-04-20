# ChefMate 智能烹饪助手

ChefMate 是一个面向日常做饭场景的智能烹饪助手，目标是陪用户完成从“今天吃什么”到“怎么一步步做出来”的完整流程。系统支持自然语言对话、菜品推荐、食材准备确认、图片识别食材、缺料补买建议、分步骤烹饪指导，以及语音输入等能力。

## 项目内容

项目主要由以下几部分组成：

- `frontend/`：Vue 前端应用，提供登录、对话工作台、菜谱库、食材清单、烹饪步骤卡片、语音输入等交互界面。
- `backend/`：FastAPI 后端服务，提供用户认证、会话管理、菜谱查询、文件上传、智能体对话、图像识别和语音识别接口。
- `ml/`：机器学习工作区，主要用于食材图像识别模型的训练、验证、导出和推理。
- `data/`：数据库表结构、菜谱数据设计和原始菜谱处理脚本。
- `docs/`：需求分析、概要设计、详细设计、技术报告和实现说明等项目文档。
- `demo/`：第三方能力或局部功能的演示脚本。

## 技术栈

### 前端

- Vue 3
- TypeScript
- Vite
- Vue Router
- Pinia
- Fetch、SSE、WebSocket
- Web Audio API 与 AudioWorklet

### 后端

- Python 3.10+
- FastAPI
- Uvicorn
- Pydantic Settings
- SQLAlchemy
- PyMySQL
- LangChain
- LangGraph
- OpenAI 兼容接口
- aiohttp

### 数据库与存储

- MySQL
- 本地文件上传目录
- FastAPI StaticFiles 静态资源暴露

### 机器学习与智能能力

- Ultralytics YOLO
- FoodSeg103 数据集处理流程
- OpenAI 兼容文本模型与多模态模型
- 火山引擎 SAUC WebSocket 语音识别

## 本地开发

### 1. 准备数据库

创建 MySQL 数据库后，可根据 `data/database/` 下的 SQL 文件初始化表结构，例如：

```bash
mysql -u root -p < data/database/chefmate_backend_schema.sql
mysql -u root -p < data/database/recipe_schema.sql
```

如有增量脚本，也需要按时间顺序执行：

```bash
mysql -u root -p chefmate < data/database/20260405_add_voice_wakeup_settings.sql
```

### 2. 启动后端

```bash
cd backend
uv sync
```

在 `backend/.env` 中配置运行参数，常用配置如下：

```env
CHEFMATE_DATABASE_URL=mysql+pymysql://root:password@localhost:3306/chefmate
CHEFMATE_LLM_BASE_URL=https://api.openai.com/v1
CHEFMATE_LLM_API_KEY=your_api_key
CHEFMATE_LLM_MODEL=gpt-4.1-mini
CHEFMATE_CORS_ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```

启动服务：

```bash
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

健康检查地址：

```text
http://127.0.0.1:8000/health
```

### 3. 启动前端

```bash
cd frontend
npm install
npm run dev
```

如后端地址不是默认的 `http://127.0.0.1:8000/api`，可在 `frontend/.env` 中配置：

```env
VITE_API_BASE_URL=http://127.0.0.1:8000/api
```

开发环境默认访问：

```text
http://127.0.0.1:5173
```

### 4. 机器学习工作区

```bash
cd ml
uv sync
uv run python -m vision.cli
```

常用命令：

```bash
uv run python -m vision.cli prepare
uv run python -m vision.cli smoke
uv run python -m vision.cli train
uv run python -m vision.cli export
uv run python -m vision.cli infer your_image.jpg
```

## 部署方式

### 后端部署

1. 在服务器安装 Python 3.10+、uv 和 MySQL。
2. 初始化数据库，并导入 `data/database/` 下的表结构。
3. 在 `backend/.env` 中配置生产环境变量，例如数据库地址、大模型 API Key、CORS 白名单、上传目录等。
4. 安装依赖并启动服务：

```bash
cd backend
uv sync --frozen
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
```

生产环境建议使用 Nginx、systemd、Supervisor 或容器平台托管后端进程，并将 `/assets` 上传资源目录持久化。

### 前端部署

1. 配置生产后端地址：

```env
VITE_API_BASE_URL=https://your-domain.com/api
```

2. 构建静态文件：

```bash
cd frontend
npm install
npm run build
```

3. 将 `frontend/dist/` 部署到 Nginx、静态资源服务器、对象存储或前端托管平台。

### 推荐线上结构

```text
用户浏览器
  -> Nginx / 静态托管
    -> frontend/dist
    -> /api 转发到 FastAPI 后端
    -> /assets 转发或映射到上传资源目录
  -> MySQL
  -> 大模型服务 / 语音识别服务
```

## 备注

- 前端默认请求 `http://127.0.0.1:8000/api`，部署时通常需要通过 `VITE_API_BASE_URL` 覆盖。
- 后端配置统一使用 `CHEFMATE_` 前缀环境变量。
- 图片识别当前支持多模态大模型路线，本地 YOLO 模型路线保留在 `ml/vision` 中用于训练与后续接入。
- 语音识别需要配置火山引擎相关 Key 后才能使用完整能力。
