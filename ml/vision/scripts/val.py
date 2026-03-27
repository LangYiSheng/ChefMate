from __future__ import annotations

import argparse
from pathlib import Path

from ultralytics import YOLO


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="验证食材检测模型")
    parser.add_argument("--weights", type=Path, required=True, help="待验证模型权重路径")
    parser.add_argument("--data", type=Path, required=True, help="YOLO 数据集 yaml 路径")
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--batch", type=int, default=16)
    parser.add_argument("--device", type=str, default="0")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    model = YOLO(str(args.weights))
    metrics = model.val(
        data=str(args.data),
        imgsz=args.imgsz,
        batch=args.batch,
        device=args.device,
    )
    print(getattr(metrics, "results_dict", metrics))


if __name__ == "__main__":
    main()
