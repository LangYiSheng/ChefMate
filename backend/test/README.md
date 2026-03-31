# ChefMate Agent 评测系统

本目录用于在**不改主后端运行逻辑**的前提下，对 ChefMate Agent 做独立评测。

## 运行方式

请在 `backend/` 目录下执行：

```bash
python -m test.cli list-datasets
python -m test.cli run --dataset agent_core_v1 --suite all
python -m test.cli run --dataset agent_core_v1 --suite stage_capability --case stage_cooking_01
python -m test.cli report --input test/reports/<run_id>/summary.json
```

## 输出内容

每次运行会在 `backend/test/reports/<run_id>/` 下生成：

- `raw_traces.json`
- `summary.json`
- `agent_performance_report.md`

## 说明

- 评测系统默认使用真实模型和真实数据库，不使用 mock。
- 运行过程中会创建独立评测用户，并在默认情况下自动清理数据。
- 如果需要排查失败案例，可加 `--keep-data` 保留测试数据。
- 如果希望保留并复盘某一条失败样例，推荐把 `--keep-data` 和 `--case <case_id>` 一起使用。
- 建议使用项目后端自己的虚拟环境解释器来运行，确保 `pydantic`、`langchain`、`sqlalchemy` 等依赖可用。
