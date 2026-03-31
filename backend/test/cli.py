from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from app.infra.logging import configure_logging
from test.runner import list_datasets, regenerate_report, run_dataset


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="ChefMate Agent 评测系统")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("list-datasets", help="列出可用数据集")

    run_parser = subparsers.add_parser("run", help="运行数据集评测")
    run_parser.add_argument("--dataset", required=True, help="数据集名称，如 agent_core_v1")
    run_parser.add_argument(
        "--suite",
        default="all",
        choices=["all", "stage_capability", "transition_decision", "end_to_end"],
        help="运行范围",
    )
    run_parser.add_argument("--case", help="只运行单条 case_id")
    run_parser.add_argument("--keep-data", action="store_true", help="保留测试用户数据，便于排查")
    run_parser.add_argument("--skip-llm-judge", action="store_true", help="跳过 LLM 补充裁判")

    report_parser = subparsers.add_parser("report", help="基于 summary.json 重新生成 Markdown 报告")
    report_parser.add_argument("--input", required=True, help="summary.json 路径")
    return parser


def main() -> None:
    configure_logging(debug=False)
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "list-datasets":
        print(json.dumps(list_datasets(), ensure_ascii=False, indent=2))
        return

    if args.command == "run":
        run_dir = asyncio.run(
            run_dataset(
                dataset=args.dataset,
                suite=args.suite,
                case_id=args.case,
                keep_data=args.keep_data,
                skip_llm_judge=args.skip_llm_judge,
            )
        )
        print(json.dumps({"run_dir": str(run_dir.resolve())}, ensure_ascii=False, indent=2))
        return

    if args.command == "report":
        output = regenerate_report(Path(args.input).expanduser().resolve())
        print(json.dumps({"report_path": str(output)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
