from __future__ import annotations

import argparse
from pathlib import Path

from ultralytics import YOLO


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="导出食材检测模型")
    parser.add_argument("--weights", type=Path, required=True, help="待导出模型权重路径")
    parser.add_argument("--format", type=str, default="onnx", help="导出格式，如 onnx / torchscript")
    parser.add_argument("--imgsz", type=int, default=640)
    return parser


def run_export(args: argparse.Namespace):
    model = YOLO(str(args.weights))
    return model.export(format=args.format, imgsz=args.imgsz)


def main() -> None:
    args = build_parser().parse_args()
    result = run_export(args)
    print(result)


if __name__ == "__main__":
    main()
