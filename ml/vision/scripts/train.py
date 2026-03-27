from __future__ import annotations

import argparse
from pathlib import Path

from ultralytics import YOLO

from vision.scripts.common import EXPERIMENTS_DIR


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="训练食材检测模型")
    parser.add_argument("--data", type=Path, required=True, help="YOLO 数据集 yaml 路径")
    parser.add_argument("--model", type=str, default="yolo11n.pt", help="预训练模型或模型配置")
    parser.add_argument("--epochs", type=int, default=100)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--batch", type=int, default=16)
    parser.add_argument("--device", type=str, default="0")
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--patience", type=int, default=30)
    parser.add_argument("--cache", action="store_true", help="是否缓存数据集")
    parser.add_argument(
        "--project",
        type=Path,
        default=EXPERIMENTS_DIR,
        help="训练输出目录",
    )
    parser.add_argument("--name", type=str, default="ingredient_yolo11n", help="实验名称")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    model = YOLO(args.model)

    # 这里统一把训练输出落到 ml/vision/experiments 下，方便管理实验结果。
    model.train(
        data=str(args.data),
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=args.batch,
        device=args.device,
        workers=args.workers,
        patience=args.patience,
        cache=args.cache,
        project=str(args.project),
        name=args.name,
    )


if __name__ == "__main__":
    main()
