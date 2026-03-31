from __future__ import annotations

import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from test.case_schema import AgentEvalCase, DatasetBundle
from test.evaluators.judge import judge_case
from test.evaluators.rules import evaluate_case_rules
from test.harness import AgentEvaluationHarness
from test.reporting import build_markdown_report, build_summary_payload, write_report_files


TEST_DIR = Path(__file__).resolve().parent
DATASET_ROOT = TEST_DIR / "datasets"
REPORT_ROOT = TEST_DIR / "reports"


def _load_bundle(path: Path) -> DatasetBundle:
    return DatasetBundle.model_validate(json.loads(path.read_text(encoding="utf-8")))


def list_datasets() -> list[dict[str, Any]]:
    datasets: dict[str, dict[str, Any]] = {}
    for dataset_dir in sorted(path for path in DATASET_ROOT.iterdir() if path.is_dir()):
        bundle_stats: list[DatasetBundle] = []
        for file_path in sorted(dataset_dir.glob("*.json")):
            bundle_stats.append(_load_bundle(file_path))
        if not bundle_stats:
            continue
        suite_counts = Counter()
        total = 0
        for bundle in bundle_stats:
            suite_counts[bundle.suite] += len(bundle.cases)
            total += len(bundle.cases)
        datasets[dataset_dir.name] = {
            "dataset": dataset_dir.name,
            "construction_method": bundle_stats[0].construction_method,
            "total_cases": total,
            "suite_counts": dict(suite_counts),
            "suites": sorted(suite_counts),
        }
    return list(datasets.values())


def load_cases(dataset: str, suite: str, *, case_id: str | None = None) -> tuple[str, list[AgentEvalCase]]:
    dataset_dir = DATASET_ROOT / dataset
    if not dataset_dir.exists():
        raise FileNotFoundError(f"找不到数据集：{dataset}")

    construction_method = "手工场景集"
    cases: list[AgentEvalCase] = []
    for file_path in sorted(dataset_dir.glob("*.json")):
        bundle = _load_bundle(file_path)
        construction_method = bundle.construction_method
        if suite != "all" and bundle.suite != suite:
            continue
        cases.extend(bundle.cases)
    if case_id is not None:
        cases = [case for case in cases if case.case_id == case_id]
    if not cases:
        if case_id is not None:
            raise ValueError(f"在数据集 {dataset} / suite {suite} 下找不到 case：{case_id}")
        raise ValueError(f"在数据集 {dataset} / suite {suite} 下没有可运行的 case。")
    return construction_method, cases


async def run_dataset(
    *,
    dataset: str,
    suite: str,
    case_id: str | None = None,
    keep_data: bool = False,
    skip_llm_judge: bool = False,
) -> Path:
    construction_method, cases = load_cases(dataset, suite, case_id=case_id)
    run_id = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid4().hex[:6]}"
    harness = AgentEvaluationHarness(run_id=run_id, keep_data=keep_data)
    raw_traces: list[dict[str, Any]] = []
    case_results: list[dict[str, Any]] = []
    try:
        for case in cases:
            if case.skip_reason:
                case_results.append(
                    {
                        "case_id": case.case_id,
                        "suite": case.suite,
                        "title": case.title,
                        "goal": case.goal,
                        "tags": case.tags,
                        "passed": False,
                        "skipped": True,
                        "skip_reason": case.skip_reason,
                        "rule_result": {"passed": False, "failures": [f"skip: {case.skip_reason}"], "metrics": {}},
                        "llm_judge": {"skipped": True, "reason": "case_skipped"},
                        "final_assistant_reply": "",
                    }
                )
                continue

            trace = await harness.run_case(case)
            rule_result = evaluate_case_rules(case, trace)
            trace["rule_result"] = rule_result
            llm_result = {"skipped": True, "reason": "skip_llm_judge"} if skip_llm_judge else await judge_case(case, trace)
            final_reply = trace.get("turns", [])[-1].get("assistant_content", "") if trace.get("turns") else ""
            raw_traces.append(trace)
            case_results.append(
                {
                    "case_id": case.case_id,
                    "suite": case.suite,
                    "title": case.title,
                    "goal": case.goal,
                    "tags": case.tags,
                    "passed": bool(rule_result["passed"]),
                    "skipped": False,
                    "rule_result": rule_result,
                    "llm_judge": llm_result,
                    "final_assistant_reply": final_reply,
                }
            )
    finally:
        harness.cleanup()

    summary = build_summary_payload(
        run_id=run_id,
        dataset=dataset,
        construction_method=construction_method,
        suite=suite,
        case_filter=case_id,
        cases=case_results,
    )
    run_dir = REPORT_ROOT / run_id
    write_report_files(run_dir=run_dir, raw_traces=raw_traces, summary=summary)
    return run_dir


def regenerate_report(summary_path: Path) -> Path:
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    target = summary_path.parent / "agent_performance_report.md"
    target.write_text(build_markdown_report(summary), encoding="utf-8")
    return target
