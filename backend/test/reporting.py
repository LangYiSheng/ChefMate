from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import date, datetime, time
from enum import Enum
from pathlib import Path
from typing import Any


METRIC_LABELS = {
    "case_pass_rate": "样例通过率",
    "required_tool_hit_rate": "必需工具命中率",
    "forbidden_tool_violation_rate": "禁止工具违规率",
    "tool_order_compliance_rate": "工具顺序符合率",
    "final_stage_accuracy": "最终阶段正确率",
    "task_state_assertion_pass_rate": "任务状态断言通过率",
    "end_to_end_completion_rate": "端到端完成率",
    "error_free_run_rate": "无异常运行率",
    "llm_average_score": "LLM 裁判平均分",
}


def build_summary_payload(
    *,
    run_id: str,
    dataset: str,
    construction_method: str,
    suite: str,
    case_filter: str | None,
    cases: list[dict[str, Any]],
) -> dict[str, Any]:
    suite_counts = Counter(case["suite"] for case in cases)
    tag_counter = Counter(tag for case in cases for tag in case.get("tags", []))
    overall = _build_metric_block(cases)
    per_suite = {
        suite_name: _build_metric_block([case for case in cases if case["suite"] == suite_name])
        for suite_name in sorted(suite_counts)
    }
    return {
        "run_id": run_id,
        "dataset": dataset,
        "suite": suite,
        "case_filter": case_filter,
        "construction_method": construction_method,
        "dataset_overview": {
            "total_cases": len(cases),
            "suite_counts": dict(suite_counts),
            "coverage_tags": sorted(tag_counter),
            "tag_counts": dict(tag_counter),
            "has_client_card_state_cases": any("client_card_state" in case.get("tags", []) for case in cases),
            "has_card_action_cases": any("card_action" in case.get("tags", []) for case in cases),
            "has_rollback_cases": any("rollback" in case.get("tags", []) for case in cases),
            "has_cancel_cases": any("cancel" in case.get("tags", []) for case in cases),
            "has_illegal_transition_cases": any("illegal_transition" in case.get("tags", []) for case in cases),
        },
        "overall_metrics": overall,
        "suite_metrics": per_suite,
        "cases": cases,
    }


def _safe_rate(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 4) if denominator else 0.0


def _build_metric_block(cases: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(cases)
    if total == 0:
        return {}

    llm_scores: list[float] = []
    metric_counts: dict[str, list[bool]] = defaultdict(list)
    for case in cases:
        rule_metrics = case.get("rule_result", {}).get("metrics", {})
        for key, value in rule_metrics.items():
            if value is None:
                continue
            metric_counts[key].append(bool(value))
        judge = case.get("llm_judge", {})
        if not judge.get("skipped") and judge.get("average_score") is not None:
            llm_scores.append(float(judge["average_score"]))

    block = {
        "case_pass_rate": _safe_rate(sum(1 for case in cases if case.get("passed")), total),
        "required_tool_hit_rate": _safe_rate(sum(metric_counts.get("required_tools_ok", [])), len(metric_counts.get("required_tools_ok", []))),
        "forbidden_tool_violation_rate": round(
            1 - _safe_rate(sum(metric_counts.get("forbidden_tools_ok", [])), len(metric_counts.get("forbidden_tools_ok", []))),
            4,
        ) if metric_counts.get("forbidden_tools_ok") else None,
        "tool_order_compliance_rate": _safe_rate(sum(metric_counts.get("tool_order_ok", [])), len(metric_counts.get("tool_order_ok", []))),
        "final_stage_accuracy": _safe_rate(sum(metric_counts.get("final_stage_ok", [])), len(metric_counts.get("final_stage_ok", []))),
        "task_state_assertion_pass_rate": _safe_rate(sum(metric_counts.get("task_assertions_ok", [])), len(metric_counts.get("task_assertions_ok", []))),
        "end_to_end_completion_rate": _safe_rate(sum(metric_counts.get("end_to_end_ok", [])), len(metric_counts.get("end_to_end_ok", []))),
        "error_free_run_rate": _safe_rate(sum(metric_counts.get("error_free_ok", [])), len(metric_counts.get("error_free_ok", []))),
        "llm_average_score": round(sum(llm_scores) / len(llm_scores), 4) if llm_scores else None,
    }
    return block


def build_markdown_report(summary: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append("# ChefMate Agent 性能评估报告")
    lines.append("")
    lines.append("## 1. 评测概述")
    lines.append("")
    lines.append(f"- Run ID：`{summary['run_id']}`")
    lines.append(f"- 数据集：`{summary['dataset']}`")
    lines.append(f"- 运行范围：`{summary['suite']}`")
    if summary.get("case_filter"):
        lines.append(f"- 单例 Case：`{summary['case_filter']}`")
    lines.append(f"- 构建方式：{summary['construction_method']}")
    lines.append("")
    lines.append("## 2. 智能方法评估数据集")
    lines.append("")
    overview = summary["dataset_overview"]
    lines.append(f"- 数据集构建方式：{summary['construction_method']}")
    lines.append(f"- 总样本量：{overview['total_cases']}")
    lines.append("- Suite 数量：")
    for suite_name, count in overview["suite_counts"].items():
        lines.append(f"  - `{suite_name}`：{count}")
    lines.append(f"- 覆盖标签：{', '.join(overview['coverage_tags']) if overview['coverage_tags'] else '无'}")
    lines.append(f"- 是否包含卡片动作：{'是' if overview['has_card_action_cases'] else '否'}")
    lines.append(f"- 是否包含 client_card_state：{'是' if overview['has_client_card_state_cases'] else '否'}")
    lines.append(f"- 是否包含回滚：{'是' if overview['has_rollback_cases'] else '否'}")
    lines.append(f"- 是否包含取消：{'是' if overview['has_cancel_cases'] else '否'}")
    lines.append(f"- 是否包含非法迁移：{'是' if overview['has_illegal_transition_cases'] else '否'}")
    lines.append("")
    lines.append("## 3. 评价方法")
    lines.append("")
    lines.append("- 规则判分：检查工具命中、禁止工具、顺序约束、最终阶段、任务状态、运行是否报错。")
    lines.append("- LLM 补充裁判：只评估回复质量，不覆盖规则判分。")
    lines.append("")
    lines.append("## 4. 评价指标")
    lines.append("")
    lines.append("- 样例通过率")
    lines.append("- 必需工具命中率")
    lines.append("- 禁止工具违规率")
    lines.append("- 工具顺序符合率")
    lines.append("- 最终阶段正确率")
    lines.append("- 任务状态断言通过率")
    lines.append("- 端到端完成率")
    lines.append("- 无异常运行率")
    lines.append("- LLM 裁判平均分")
    lines.append("")
    lines.append("## 5. 数据集上的性能结果")
    lines.append("")
    lines.extend(_render_metric_block("总体结果", summary["overall_metrics"]))
    for suite_name, metrics in summary["suite_metrics"].items():
        lines.extend(_render_metric_block(f"Suite：{suite_name}", metrics))
    lines.append("")
    lines.append("## 6. 典型失败案例与误差分析")
    lines.append("")
    failed_cases = [case for case in summary["cases"] if not case.get("passed")]
    if not failed_cases:
        lines.append("- 本次运行未出现规则失败案例。")
    else:
        for case in failed_cases[:5]:
            lines.append(f"### {case['case_id']} - {case['title']}")
            lines.append(f"- Suite：`{case['suite']}`")
            lines.append(f"- 失败原因：{'；'.join(case.get('rule_result', {}).get('failures', [])[:5])}")
            final_reply = case.get("final_assistant_reply") or ""
            if final_reply:
                lines.append(f"- 最终回复摘录：{final_reply[:200]}")
            judge = case.get("llm_judge", {})
            if not judge.get("skipped"):
                lines.append(f"- LLM 裁判总结：{judge.get('summary')}")
            lines.append("")
    lines.append("## 7. 当前局限与下一步改进建议")
    lines.append("")
    lines.append("- 当前数据集为手工场景集，尚未纳入真实用户对话回放。")
    lines.append("- 当前为单版本评测，不包含横向 prompt / model 对比。")
    lines.append("- 当前范围仅覆盖 Agent 主链路，不单独评估推荐与图像识别子系统。")
    return "\n".join(lines).strip() + "\n"


def _render_metric_block(title: str, metrics: dict[str, Any]) -> list[str]:
    lines = [f"### {title}"]
    if not metrics:
        lines.append("- 无数据")
        lines.append("")
        return lines
    for key, value in metrics.items():
        label = METRIC_LABELS.get(key, key)
        lines.append(f"- {label}: {value}")
    lines.append("")
    return lines


def write_report_files(
    *,
    run_dir: Path,
    raw_traces: list[dict[str, Any]],
    summary: dict[str, Any],
) -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "raw_traces.json").write_text(
        json.dumps(raw_traces, ensure_ascii=False, indent=2, default=_json_default),
        encoding="utf-8",
    )
    (run_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, default=_json_default),
        encoding="utf-8",
    )
    (run_dir / "agent_performance_report.md").write_text(
        build_markdown_report(summary),
        encoding="utf-8",
    )


def _json_default(value: Any) -> Any:
    if isinstance(value, (datetime, date, time)):
        return value.isoformat()
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Path):
        return str(value)
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    return str(value)
