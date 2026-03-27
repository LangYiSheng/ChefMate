from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from pydantic import BaseModel


SUPPORTED_IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}


def bootstrap_path() -> None:
    backend_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(backend_root))


def guess_mime_type(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in {".jpg", ".jpeg"}:
        return "image/jpeg"
    if suffix == ".png":
        return "image/png"
    if suffix == ".webp":
        return "image/webp"
    if suffix == ".bmp":
        return "image/bmp"
    return "application/octet-stream"


def print_payload(payload) -> None:
    if isinstance(payload, BaseModel):
        payload = payload.model_dump(mode="json")
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def list_images(folder: Path) -> list[Path]:
    return sorted(path for path in folder.iterdir() if path.is_file() and path.suffix.lower() in SUPPORTED_IMAGE_SUFFIXES)


def normalize_label(value: str) -> str:
    return value.strip().lower().replace(" ", "").replace("　", "")


def normalize_ingredient_list(values: list[str]) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for item in values:
        cleaned = normalize_label(item)
        if not cleaned:
            continue
        if cleaned not in seen:
            normalized.append(cleaned)
            seen.add(cleaned)
    return normalized


def read_ground_truth(json_path: Path) -> list[str]:
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    if isinstance(payload, list):
        return [str(item) for item in payload]
    if isinstance(payload, dict) and isinstance(payload.get("ingredients"), list):
        return [str(item) for item in payload["ingredients"]]
    raise ValueError(f"{json_path} 的标注格式不正确，应为数组或 {{\"ingredients\": [...]}}。")


def detect_ingredients_for_image(image_path: Path, user_hint: str | None):
    from app.skills.vision import vision_skill

    image_bytes = image_path.read_bytes()
    return vision_skill.detect_ingredients(
        image_bytes=image_bytes,
        mime_type=guess_mime_type(image_path),
        filename=image_path.name,
        user_hint=user_hint,
    )


def to_ingredient_names(result) -> list[str]:
    payload = result.model_dump(mode="json") if isinstance(result, BaseModel) else result
    items = payload.get("ingredients", [])
    names = [item["name"] for item in items if isinstance(item, dict) and item.get("name")]
    return normalize_ingredient_list(names)


def generate_json_annotations(folder: Path, *, user_hint: str | None, overwrite: bool) -> dict:
    details: list[dict] = []
    image_paths = list_images(folder)

    for image_path in image_paths:
        json_path = image_path.with_suffix(".json")
        if json_path.exists() and not overwrite:
            details.append(
                {
                    "image": image_path.name,
                    "status": "skipped_existing_json",
                    "json_path": str(json_path),
                }
            )
            continue

        result = detect_ingredients_for_image(image_path, user_hint)
        ingredients = to_ingredient_names(result)
        json_path.write_text(json.dumps(ingredients, ensure_ascii=False, indent=2), encoding="utf-8")
        details.append(
            {
                "image": image_path.name,
                "status": "written",
                "json_path": str(json_path),
                "ingredients": ingredients,
            }
        )

    return {
        "mode": "generate_annotations",
        "folder": str(folder),
        "image_count": len(image_paths),
        "written_count": sum(1 for item in details if item["status"] == "written"),
        "skipped_count": sum(1 for item in details if item["status"] != "written"),
        "details": details,
    }


def safe_divide(numerator: float, denominator: float) -> float:
    return round(numerator / denominator, 4) if denominator else 0.0


def evaluate_folder(folder: Path, *, user_hint: str | None) -> dict:
    details: list[dict] = []
    image_paths = list_images(folder)

    total_tp = 0
    total_fp = 0
    total_fn = 0
    exact_match_count = 0
    jaccard_sum = 0.0
    missing_label_files: list[str] = []

    for image_path in image_paths:
        json_path = image_path.with_suffix(".json")
        if not json_path.exists():
            missing_label_files.append(image_path.name)
            continue

        ground_truth = normalize_ingredient_list(read_ground_truth(json_path))
        prediction = to_ingredient_names(detect_ingredients_for_image(image_path, user_hint))

        gt_set = set(ground_truth)
        pred_set = set(prediction)
        tp = len(gt_set & pred_set)
        fp = len(pred_set - gt_set)
        fn = len(gt_set - pred_set)

        precision = safe_divide(tp, tp + fp)
        recall = safe_divide(tp, tp + fn)
        f1 = safe_divide(2 * precision * recall, precision + recall) if (precision + recall) else 0.0
        jaccard = safe_divide(len(gt_set & pred_set), len(gt_set | pred_set)) if (gt_set or pred_set) else 1.0
        exact_match = gt_set == pred_set

        total_tp += tp
        total_fp += fp
        total_fn += fn
        exact_match_count += 1 if exact_match else 0
        jaccard_sum += jaccard

        details.append(
            {
                "image": image_path.name,
                "ground_truth": ground_truth,
                "predicted": prediction,
                "tp": tp,
                "fp": fp,
                "fn": fn,
                "precision": precision,
                "recall": recall,
                "f1": round(f1, 4),
                "jaccard": jaccard,
                "exact_match": exact_match,
                "missed": sorted(gt_set - pred_set),
                "extra": sorted(pred_set - gt_set),
            }
        )

    evaluated_count = len(details)
    micro_precision = safe_divide(total_tp, total_tp + total_fp)
    micro_recall = safe_divide(total_tp, total_tp + total_fn)
    micro_f1 = safe_divide(2 * micro_precision * micro_recall, micro_precision + micro_recall) if (
        micro_precision + micro_recall
    ) else 0.0

    return {
        "mode": "evaluate",
        "folder": str(folder),
        "image_count": len(image_paths),
        "evaluated_count": evaluated_count,
        "missing_label_count": len(missing_label_files),
        "missing_label_files": missing_label_files,
        "metrics": {
            "exact_match_accuracy": safe_divide(exact_match_count, evaluated_count),
            "micro_precision": micro_precision,
            "micro_recall": micro_recall,
            "micro_f1": round(micro_f1, 4),
            "average_jaccard": safe_divide(jaccard_sum, evaluated_count),
        },
        "details": details,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="ChefMate 图像识别批量测试脚本")
    parser.add_argument("input_path", type=str, help="图片路径，或图片所在文件夹路径")
    parser.add_argument("--user-hint", type=str, help="可选补充提示")
    parser.add_argument("--evaluate", action="store_true", help="对文件夹中的图片和同名 JSON 标注进行评估")
    parser.add_argument("--overwrite", action="store_true", help="批量生成 JSON 时允许覆盖已有同名 JSON")
    return parser


def main() -> None:
    bootstrap_path()

    args = build_parser().parse_args()
    input_path = Path(args.input_path).expanduser().resolve()

    if input_path.is_file():
        result = detect_ingredients_for_image(input_path, args.user_hint)
        print_payload(result)
        return

    if not input_path.is_dir():
        raise FileNotFoundError(f"找不到输入路径：{input_path}")

    if args.evaluate:
        print_payload(evaluate_folder(input_path, user_hint=args.user_hint))
        return

    print_payload(generate_json_annotations(input_path, user_hint=args.user_hint, overwrite=args.overwrite))


if __name__ == "__main__":
    main()
