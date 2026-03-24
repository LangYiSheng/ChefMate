# ChefMate Backend

## 1. 目录目的

该目录用于承载 ChefMate 的 Python 智能体后端，当前采用：

- `FastAPI` 作为对外 API 框架
- 任务管理器负责任务创建、挂起、恢复与推进
- 工作流编排器负责固定流程路由
- 推荐、图像识别、备料检查、烹饪指导作为内部技能模块

当前目录提供的是**基础框架骨架**，便于后续继续实现：

- 推荐系统
- 图像识别
- 任务状态持久化
- 结构化菜谱读取
- LangGraph 工作流接入

## 2. 当前目录结构

```text
backend/
  app/
    api/            # 对外接口与路由
    core/           # 任务管理、工作流、语义对象
    db/             # 数据库契约模型
    schemas/        # API 输入输出模型
    services/       # 领域服务
    skills/         # 技能模块
    config.py       # 配置
    main.py         # FastAPI 应用入口
  pyproject.toml
```

## 3. 后续实现建议

优先实现顺序建议如下：

1. `app/db/contracts.py`
   对齐真实数据库字段，完成查询与持久化层
2. `app/skills/recommendation.py`
   实现长期画像与即时需求融合推荐
3. `app/skills/vision.py`
   实现台面食材识别
4. `app/core/workflow.py`
   替换为 LangGraph 工作流
5. `app/core/task_manager.py`
   从内存任务管理替换为数据库持久化任务管理
