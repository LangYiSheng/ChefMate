from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from pydantic import BaseModel


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
    return "application/octet-stream"


def print_payload(payload) -> None:
    if isinstance(payload, BaseModel):
        payload = payload.model_dump(mode="json")
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def main() -> None:
    bootstrap_path()

    from app.skills.vision import vision_skill

    parser = argparse.ArgumentParser(description="ChefMate 图像识别食材测试脚本")
    parser.add_argument("image_path", type=str, help="待识别图片路径")
    parser.add_argument("--user-hint", type=str, help="可选补充提示")
    args = parser.parse_args()

    image_path = Path(args.image_path).expanduser().resolve()
    image_bytes = image_path.read_bytes()
    result = vision_skill.detect_ingredients(
        image_bytes=image_bytes,
        mime_type=guess_mime_type(image_path),
        filename=image_path.name,
        user_hint=args.user_hint,
    )
    print_payload(result)


if __name__ == "__main__":
    main()
