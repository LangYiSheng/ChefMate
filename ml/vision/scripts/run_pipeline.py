from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
from typing import Any

from ultralytics import YOLO

from vision.scripts.common import CONFIGS_DIR, EXPERIMENTS_DIR, PROCESSED_DIR, WEIGHTS_DIR, dump_json, ensure_dir
from vision.scripts.prepare_foodseg103 import run_prepare


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="一键执行 FoodSeg103 数据准备、训练、验证、导出与报告生成")
    parser.add_argument("--mapping", type=Path, default=CONFIGS_DIR / "foodseg103_ingredient_map.example.yaml")
    parser.add_argument("--dataset-name", type=str, default="ingredient_detection_foodseg103")
    parser.add_argument("--model", type=str, default="yolo11n.pt")
    parser.add_argument("--epochs", type=int, default=100)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--batch", type=int, default=16)
    parser.add_argument("--device", type=str, default="0")
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--patience", type=int, default=30)
    parser.add_argument("--conf", type=float, default=0.25)
    parser.add_argument("--cache", action="store_true")
    parser.add_argument("--export-format", type=str, default="onnx")
    parser.add_argument("--max-samples-per-split", type=int, default=0)
    parser.add_argument("--clear-output", action="store_true")
    parser.add_argument("--experiment-name", type=str, default="")
    return parser


def metrics_to_dict(metrics: Any) -> dict[str, float | None]:
    box = getattr(metrics, "box", None)
    results_dict = getattr(metrics, "results_dict", None)
    return {
        "map50": getattr(box, "map50", None),
        "map50_95": getattr(box, "map", None),
        "precision": getattr(box, "mp", None),
        "recall": getattr(box, "mr", None),
        "fitness": getattr(metrics, "fitness", None),
        "raw_results_dict": results_dict if isinstance(results_dict, dict) else None,
    }


def build_report_markdown(
    *,
    experiment_name: str,
    dataset_yaml: Path,
    model_name: str,
    export_format: str,
    metrics: dict[str, float | None],
    best_weights: Path,
    exported_path: str | Path | None,
    export_error: str | None,
) -> str:
    lines = [
        f"# 实验报告：{experiment_name}",
        "",
        f"- 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"- 数据集配置：`{dataset_yaml.as_posix()}`",
        f"- 训练模型：`{model_name}`",
        f"- 导出格式：`{export_format}`",
        f"- 最佳权重：`{best_weights.as_posix()}`",
    ]
    if exported_path:
        lines.append(f"- 导出结果：`{Path(str(exported_path)).as_posix()}`")
    if export_error:
        lines.append(f"- 导出状态：失败，原因：`{export_error}`")
    lines.extend(
        [
            "",
            "## 量化结果",
            "",
            f"- mAP@50：{metrics.get('map50')}",
            f"- mAP@50:95：{metrics.get('map50_95')}",
            f"- Precision：{metrics.get('precision')}",
            f"- Recall：{metrics.get('recall')}",
            f"- Fitness：{metrics.get('fitness')}",
            "",
            "## 说明",
            "",
            "- 当前结果来自自动化训练流水线输出。",
            "- 如果后续加入自采集台面食材数据，可继续在该实验基础上微调。",
        ]
    )
    return "\n".join(lines)


def run_pipeline(args: argparse.Namespace) -> Path:
    dataset_root = PROCESSED_DIR / args.dataset_name
    dataset_yaml = dataset_root / "dataset.yaml"
    experiment_name = args.experiment_name or f"{args.dataset_name}_{Path(args.model).stem}"

    # 先用 FoodSeg103 构建项目所需的检测数据，再进入训练流程。
    prepare_args = argparse.Namespace(
        mapping=args.mapping,
        output_name=args.dataset_name,
        repo_id="EduardoPacheco/FoodSeg103",
        max_samples_per_split=args.max_samples_per_split,
        min_box_area_ratio=0.001,
        clear_output=args.clear_output,
    )
    run_prepare(prepare_args)

    model = YOLO(args.model)
    train_result = model.train(
        data=str(dataset_yaml),
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=args.batch,
        device=args.device,
        workers=args.workers,
        patience=args.patience,
        cache=args.cache,
        project=str(EXPERIMENTS_DIR),
        name=experiment_name,
    )

    run_dir = Path(getattr(train_result, "save_dir", EXPERIMENTS_DIR / experiment_name))
    best_weights = run_dir / "weights" / "best.pt"

    trained_model = YOLO(str(best_weights))
    metrics = trained_model.val(
        data=str(dataset_yaml),
        imgsz=args.imgsz,
        batch=args.batch,
        device=args.device,
        conf=args.conf,
    )
    export_result = None
    export_error = None
    try:
        export_result = trained_model.export(format=args.export_format, imgsz=args.imgsz)
    except Exception as exc:
        export_error = str(exc)
        print(f"WARNING: 模型导出失败，将保留训练与验证结果。原因：{export_error}", flush=True)

    metrics_payload = metrics_to_dict(metrics)
    report_payload = {
        "experiment_name": experiment_name,
        "dataset_yaml": dataset_yaml.as_posix(),
        "model": args.model,
        "epochs": args.epochs,
        "imgsz": args.imgsz,
        "batch": args.batch,
        "device": args.device,
        "metrics": metrics_payload,
        "best_weights": best_weights.as_posix(),
        "export_result": str(export_result) if export_result is not None else None,
        "export_error": export_error,
    }
    dump_json(run_dir / "metrics_summary.json", report_payload)
    (run_dir / "report.md").write_text(
        build_report_markdown(
            experiment_name=experiment_name,
            dataset_yaml=dataset_yaml,
            model_name=args.model,
            export_format=args.export_format,
            metrics=metrics_payload,
            best_weights=best_weights,
            exported_path=export_result,
            export_error=export_error,
        ),
        encoding="utf-8",
    )

    if best_weights.exists():
        ensure_dir(WEIGHTS_DIR)
        target_weight = WEIGHTS_DIR / f"{experiment_name}.pt"
        target_weight.write_bytes(best_weights.read_bytes())

    return run_dir


def main() -> None:
    args = build_parser().parse_args()
    run_dir = run_pipeline(args)
    print(f"实验完成，输出目录：{run_dir}")
    print(f"量化报告：{(run_dir / 'report.md').as_posix()}")


if __name__ == "__main__":
    main()
