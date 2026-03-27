from __future__ import annotations

import argparse
from pathlib import Path

from ultralytics import YOLO

from vision.scripts.common import EXPERIMENTS_DIR


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="使用训练后的权重做本地推理")
    parser.add_argument("--weights", type=Path, required=True, help="模型权重路径")
    parser.add_argument("--source", type=str, required=True, help="图片、文件夹或视频路径")
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--conf", type=float, default=0.25)
    parser.add_argument(
        "--project",
        type=Path,
        default=EXPERIMENTS_DIR,
        help="推理结果输出目录",
    )
    parser.add_argument("--name", type=str, default="predict", help="推理结果目录名")
    return parser


def run_infer(args: argparse.Namespace) -> None:
    model = YOLO(str(args.weights))
    model.predict(
        source=args.source,
        imgsz=args.imgsz,
        conf=args.conf,
        project=str(args.project),
        name=args.name,
        save=True,
    )


def main() -> None:
    args = build_parser().parse_args()
    run_infer(args)


if __name__ == "__main__":
    main()
