from __future__ import annotations

import argparse
from collections import defaultdict
from pathlib import Path

import numpy as np
from PIL import Image


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="将分割掩码转换为 YOLO 检测框标注")
    parser.add_argument("--images-dir", type=Path, required=True, help="原始图片目录")
    parser.add_argument("--masks-dir", type=Path, required=True, help="分割掩码目录")
    parser.add_argument("--output-images-dir", type=Path, required=True, help="输出图片目录")
    parser.add_argument("--output-labels-dir", type=Path, required=True, help="输出 YOLO 标签目录")
    parser.add_argument(
        "--class-map",
        type=Path,
        required=True,
        help="类别映射文件，每行格式为 原始类别id,目标类别id",
    )
    return parser


def load_class_map(path: Path) -> dict[int, int]:
    mapping: dict[int, int] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        source_id, target_id = line.split(",", maxsplit=1)
        mapping[int(source_id.strip())] = int(target_id.strip())
    return mapping


def mask_to_boxes(mask_array: np.ndarray, class_mapping: dict[int, int]) -> dict[int, list[tuple[int, int, int, int]]]:
    grouped: dict[int, list[tuple[int, int, int, int]]] = defaultdict(list)
    for source_class_id, target_class_id in class_mapping.items():
        ys, xs = np.where(mask_array == source_class_id)
        if len(xs) == 0 or len(ys) == 0:
            continue
        x_min, x_max = int(xs.min()), int(xs.max())
        y_min, y_max = int(ys.min()), int(ys.max())
        grouped[target_class_id].append((x_min, y_min, x_max, y_max))
    return grouped


def to_yolo_line(class_id: int, box: tuple[int, int, int, int], width: int, height: int) -> str:
    x_min, y_min, x_max, y_max = box
    x_center = ((x_min + x_max) / 2) / width
    y_center = ((y_min + y_max) / 2) / height
    box_width = (x_max - x_min) / width
    box_height = (y_max - y_min) / height
    return f"{class_id} {x_center:.6f} {y_center:.6f} {box_width:.6f} {box_height:.6f}"


def main() -> None:
    args = build_parser().parse_args()
    class_mapping = load_class_map(args.class_map)
    args.output_images_dir.mkdir(parents=True, exist_ok=True)
    args.output_labels_dir.mkdir(parents=True, exist_ok=True)

    image_paths = sorted(path for path in args.images_dir.iterdir() if path.is_file())
    for image_path in image_paths:
        mask_path = args.masks_dir / f"{image_path.stem}.png"
        if not mask_path.exists():
            continue

        image = Image.open(image_path).convert("RGB")
        mask = Image.open(mask_path)
        mask_array = np.array(mask)
        width, height = image.size

        lines: list[str] = []
        boxes = mask_to_boxes(mask_array, class_mapping)
        for class_id, class_boxes in boxes.items():
            for box in class_boxes:
                lines.append(to_yolo_line(class_id, box, width, height))

        if not lines:
            continue

        output_image_path = args.output_images_dir / image_path.name
        output_label_path = args.output_labels_dir / f"{image_path.stem}.txt"
        image.save(output_image_path)
        output_label_path.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()

