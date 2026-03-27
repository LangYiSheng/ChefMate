from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml


VISION_ROOT = Path(__file__).resolve().parents[1]
CONFIGS_DIR = VISION_ROOT / "configs"
DATASETS_DIR = VISION_ROOT / "datasets"
RAW_DIR = DATASETS_DIR / "raw"
PROCESSED_DIR = DATASETS_DIR / "processed"
EXPERIMENTS_DIR = VISION_ROOT / "experiments"
WEIGHTS_DIR = VISION_ROOT / "weights"


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def load_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def dump_yaml(path: Path, payload: dict[str, Any]) -> None:
    ensure_dir(path.parent)
    path.write_text(yaml.safe_dump(payload, allow_unicode=True, sort_keys=False), encoding="utf-8")


def dump_json(path: Path, payload: dict[str, Any]) -> None:
    ensure_dir(path.parent)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def find_latest_experiment_dir() -> Path | None:
    if not EXPERIMENTS_DIR.exists():
        return None
    candidates = [path for path in EXPERIMENTS_DIR.iterdir() if path.is_dir()]
    if not candidates:
        return None
    return max(candidates, key=lambda path: path.stat().st_mtime)


def find_latest_weight_file() -> Path | None:
    latest_experiment = find_latest_experiment_dir()
    if latest_experiment is None:
        return None
    best_weight = latest_experiment / "weights" / "best.pt"
    if best_weight.exists():
        return best_weight
    return None
