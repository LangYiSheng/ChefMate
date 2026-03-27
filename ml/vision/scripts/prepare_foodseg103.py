from __future__ import annotations

import argparse
import shutil
import threading
import time
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from datasets import DatasetDict, load_dataset
from PIL import Image
from tqdm import tqdm

from vision.scripts.common import CONFIGS_DIR, PROCESSED_DIR, dump_json, dump_yaml, ensure_dir, load_yaml


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="从 FoodSeg103 构建项目食材检测数据集")
    parser.add_argument(
        "--mapping",
        type=Path,
        default=CONFIGS_DIR / "foodseg103_ingredient_map.example.yaml",
        help="FoodSeg103 到项目类别的映射文件",
    )
    parser.add_argument(
        "--output-name",
        type=str,
        default="ingredient_detection_foodseg103",
        help="输出数据集目录名",
    )
    parser.add_argument(
        "--repo-id",
        type=str,
        default="EduardoPacheco/FoodSeg103",
        help="Hugging Face 数据集仓库名",
    )
    parser.add_argument(
        "--max-samples-per-split",
        type=int,
        default=0,
        help="每个 split 最多处理多少条，0 表示全部处理",
    )
    parser.add_argument(
        "--min-box-area-ratio",
        type=float,
        default=0.001,
        help="检测框最小面积比例，过小目标直接忽略",
    )
    parser.add_argument(
        "--clear-output",
        action="store_true",
        help="是否先清空旧输出目录",
    )
    return parser


def load_mapping(path: Path) -> tuple[list[str], dict[int, int]]:
    payload = load_yaml(path)
    items = payload.get("classes", [])
    names: list[str] = []
    source_to_target: dict[int, int] = {}
    for target_id, item in enumerate(items):
        target_name = str(item["target_name"]).strip()
        names.append(target_name)
        for source_id in item.get("source_ids", []):
            source_to_target[int(source_id)] = target_id
    return names, source_to_target


def to_boxes(mask_array: np.ndarray, source_to_target: dict[int, int], min_area_ratio: float) -> list[tuple[int, tuple[int, int, int, int]]]:
    height, width = mask_array.shape
    min_area = height * width * min_area_ratio
    grouped_positions: dict[int, tuple[np.ndarray, np.ndarray]] = {}

    for source_class_id, target_class_id in source_to_target.items():
        ys, xs = np.where(mask_array == source_class_id)
        if len(xs) == 0 or len(ys) == 0:
            continue
        if len(xs) < min_area:
            continue
        grouped_positions[target_class_id] = (ys, xs)

    boxes: list[tuple[int, tuple[int, int, int, int]]] = []
    for target_class_id, (ys, xs) in grouped_positions.items():
        x_min, x_max = int(xs.min()), int(xs.max())
        y_min, y_max = int(ys.min()), int(ys.max())
        boxes.append((target_class_id, (x_min, y_min, x_max, y_max)))
    return boxes


def to_yolo_line(class_id: int, box: tuple[int, int, int, int], width: int, height: int) -> str:
    x_min, y_min, x_max, y_max = box
    x_center = ((x_min + x_max) / 2) / width
    y_center = ((y_min + y_max) / 2) / height
    box_width = (x_max - x_min) / width
    box_height = (y_max - y_min) / height
    return f"{class_id} {x_center:.6f} {y_center:.6f} {box_width:.6f} {box_height:.6f}"


def prepare_split(
    split_name: str,
    rows,
    *,
    output_root: Path,
    source_to_target: dict[int, int],
    max_samples: int,
    min_box_area_ratio: float,
    target_names: list[str],
) -> dict[str, object]:
    images_dir = ensure_dir(output_root / "images" / split_name)
    labels_dir = ensure_dir(output_root / "labels" / split_name)
    class_counter: Counter[str] = Counter()
    kept_samples = 0
    total_rows = min(len(rows), max_samples) if max_samples else len(rows)

    for row_index, row in enumerate(
        tqdm(
            rows,
            total=total_rows,
            desc=f"处理 {split_name}",
            unit="sample",
        )
    ):
        if max_samples and kept_samples >= max_samples:
            break

        image = row["image"]
        label = row["label"]
        image_pil = image if isinstance(image, Image.Image) else image["image"]
        label_pil = label if isinstance(label, Image.Image) else label["image"]
        image_rgb = image_pil.convert("RGB")
        label_array = np.array(label_pil)
        width, height = image_rgb.size

        boxes = to_boxes(label_array, source_to_target, min_area_ratio=min_box_area_ratio)
        if not boxes:
            continue

        sample_id = row.get("id", row_index)
        image_name = f"{split_name}_{sample_id}.jpg"
        label_name = f"{split_name}_{sample_id}.txt"
        image_rgb.save(images_dir / image_name, quality=95)

        yolo_lines: list[str] = []
        for class_id, box in boxes:
            yolo_lines.append(to_yolo_line(class_id, box, width, height))
            class_counter[target_names[class_id]] += 1

        (labels_dir / label_name).write_text("\n".join(yolo_lines), encoding="utf-8")
        kept_samples += 1

    return {
        "split": split_name,
        "samples": kept_samples,
        "class_box_count": dict(class_counter),
    }


def load_dataset_with_status(repo_id: str) -> DatasetDict:
    stop_event = threading.Event()

    def worker() -> None:
        start_time = time.time()
        dots = 0
        while not stop_event.wait(2):
            dots = (dots + 1) % 4
            elapsed = int(time.time() - start_time)
            suffix = "." * dots if dots else "."
            print(f"正在从 Hugging Face 下载并缓存数据集{suffix} 已等待 {elapsed}s", flush=True)

    thread = threading.Thread(target=worker, daemon=True)
    print(f"开始加载数据集：{repo_id}", flush=True)
    print("首次下载可能会比较久，请耐心等一会儿。", flush=True)
    thread.start()
    try:
        dataset: DatasetDict = load_dataset(repo_id)
        return dataset
    finally:
        stop_event.set()
        thread.join(timeout=1)
        print("数据集加载完成。", flush=True)


def create_dataset_yaml(output_root: Path, names: list[str]) -> Path:
    dataset_yaml_path = output_root / "dataset.yaml"
    dump_yaml(
        dataset_yaml_path,
        {
            # Ultralytics 在 Windows 下对 "." 的解析有时会偏到工作目录，直接写清楚根目录更稳。
            "path": output_root.resolve().as_posix(),
            "train": "images/train",
            "val": "images/validation",
            "test": "images/validation",
            "names": {index: name for index, name in enumerate(names)},
        },
    )
    return dataset_yaml_path


def run_prepare(args: argparse.Namespace) -> dict[str, object]:
    target_names, source_to_target = load_mapping(args.mapping)
    output_root = PROCESSED_DIR / args.output_name

    if args.clear_output and output_root.exists():
        shutil.rmtree(output_root)

    ensure_dir(output_root)
    dataset: DatasetDict = load_dataset_with_status(args.repo_id)
    split_sizes = {split_name: len(split_rows) for split_name, split_rows in dataset.items()}
    print(f"数据集分片大小：{split_sizes}", flush=True)

    split_reports: list[dict[str, object]] = []
    for split_name in ["train", "validation"]:
        if split_name not in dataset:
            continue
        split_report = prepare_split(
            split_name,
            dataset[split_name],
            output_root=output_root,
            source_to_target=source_to_target,
            max_samples=args.max_samples_per_split,
            min_box_area_ratio=args.min_box_area_ratio,
            target_names=target_names,
        )
        split_reports.append(split_report)

    dataset_yaml_path = create_dataset_yaml(output_root, target_names)
    summary = {
        "repo_id": args.repo_id,
        "output_root": output_root.as_posix(),
        "mapping_file": args.mapping.as_posix(),
        "target_classes": target_names,
        "dataset_yaml": dataset_yaml_path.as_posix(),
        "splits": split_reports,
    }
    dump_json(output_root / "prepare_summary.json", summary)
    return summary


def main() -> None:
    args = build_parser().parse_args()
    summary = run_prepare(args)
    output_root = summary["output_root"]
    dataset_yaml_path = summary["dataset_yaml"]
    print(f"已生成检测数据集：{output_root}")
    print(f"数据集配置文件：{dataset_yaml_path}")


if __name__ == "__main__":
    main()
