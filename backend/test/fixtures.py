from __future__ import annotations

import mimetypes
from copy import deepcopy
from pathlib import Path
from typing import Any

from app.services.recipe_catalog_service import recipe_catalog_service


PROJECT_ROOT = Path(__file__).resolve().parents[2]


RECIPE_PRESETS: dict[str, dict[str, Any]] = {
    "weeknight_omelette": {
        "source_type": "generated",
        "name": "快手葱花煎蛋",
        "description": "适合工作日晚上的简易煎蛋。",
        "difficulty": "简单",
        "estimated_minutes": 12,
        "servings": 1,
        "tags": {
            "flavor": ["家常", "清淡"],
            "scene": ["工作日晚餐"],
            "tool": ["平底锅"],
            "time": ["10到20分钟"],
        },
        "ingredients": [
            {"id": "ingredient-egg", "ingredient_name": "鸡蛋", "amount_text": "2 个", "sort_order": 1},
            {"id": "ingredient-scallion", "ingredient_name": "葱花", "amount_text": "1 小把", "sort_order": 2},
            {"id": "ingredient-salt", "ingredient_name": "盐", "amount_text": "少许", "sort_order": 3, "is_optional": True},
        ],
        "steps": [
            {"id": "step-1", "step_no": 1, "title": "打散鸡蛋", "instruction": "把鸡蛋打入碗中，加入葱花和少许盐搅匀。"},
            {"id": "step-2", "step_no": 2, "title": "热锅", "instruction": "平底锅中火预热，倒入少量油润锅。"},
            {"id": "step-3", "step_no": 3, "title": "倒入蛋液", "instruction": "把蛋液倒入锅中，等待边缘凝固。"},
            {"id": "step-4", "step_no": 4, "title": "定型出锅", "instruction": "轻轻翻面或折叠，熟透后出锅。"},
        ],
        "tips": "全程中小火更稳，不容易焦。",
    },
    "air_fryer_fries": {
        "source_type": "generated",
        "name": "空气炸锅薯条",
        "description": "适合新手的空气炸锅快手小吃。",
        "difficulty": "简单",
        "estimated_minutes": 25,
        "servings": 2,
        "tags": {
            "flavor": ["咸鲜"],
            "scene": ["晚餐", "小吃"],
            "tool": ["空气炸锅"],
            "time": ["20到30分钟"],
        },
        "ingredients": [
            {"id": "ingredient-potato", "ingredient_name": "土豆", "amount_text": "2 个", "sort_order": 1},
            {"id": "ingredient-oil", "ingredient_name": "食用油", "amount_text": "1 汤匙", "sort_order": 2},
            {"id": "ingredient-salt", "ingredient_name": "盐", "amount_text": "少许", "sort_order": 3},
        ],
        "steps": [
            {"id": "step-1", "step_no": 1, "title": "切薯条", "instruction": "把土豆去皮后切成粗细均匀的条状。"},
            {"id": "step-2", "step_no": 2, "title": "浸泡沥干", "instruction": "冷水浸泡 10 分钟后擦干表面水分。"},
            {"id": "step-3", "step_no": 3, "title": "拌油调味", "instruction": "加入少量食用油和盐，抓拌均匀。"},
            {"id": "step-4", "step_no": 4, "title": "空气炸锅预热", "instruction": "空气炸锅 180 度预热 3 分钟。"},
            {"id": "step-5", "step_no": 5, "title": "炸至金黄", "instruction": "把薯条铺平，180 度炸 12 到 15 分钟，中途翻动一次。"},
        ],
        "tips": "薯条不要堆太厚，受热会更均匀。",
    },
    "tomato_egg": {
        "source_type": "generated",
        "name": "番茄炒蛋",
        "description": "经典家常快手菜。",
        "difficulty": "简单",
        "estimated_minutes": 18,
        "servings": 2,
        "tags": {
            "flavor": ["酸甜", "家常"],
            "scene": ["午餐", "晚餐"],
            "tool": ["炒锅"],
            "time": ["10到20分钟"],
        },
        "ingredients": [
            {"id": "ingredient-tomato", "ingredient_name": "番茄", "amount_text": "2 个", "sort_order": 1},
            {"id": "ingredient-egg", "ingredient_name": "鸡蛋", "amount_text": "3 个", "sort_order": 2},
            {"id": "ingredient-scallion", "ingredient_name": "葱", "amount_text": "1 根", "sort_order": 3},
        ],
        "steps": [
            {"id": "step-1", "step_no": 1, "title": "准备食材", "instruction": "番茄切块，鸡蛋打散，葱切末。"},
            {"id": "step-2", "step_no": 2, "title": "炒鸡蛋", "instruction": "热锅下油，把蛋液炒到七八成熟盛出。"},
            {"id": "step-3", "step_no": 3, "title": "炒番茄", "instruction": "锅里补少量油，下番茄炒出汁水。"},
            {"id": "step-4", "step_no": 4, "title": "混合调味", "instruction": "倒回鸡蛋，加入葱花翻匀，按口味调味。"},
            {"id": "step-5", "step_no": 5, "title": "收汁出锅", "instruction": "略微收汁后即可出锅。"},
        ],
        "tips": "番茄先炒出汁，口感会更融合。",
    },
    "garlic_broccoli": {
        "source_type": "generated",
        "name": "蒜香西兰花",
        "description": "清爽好上手的家常蔬菜。",
        "difficulty": "简单",
        "estimated_minutes": 15,
        "servings": 2,
        "tags": {
            "flavor": ["清淡", "蒜香"],
            "scene": ["晚餐"],
            "tool": ["炒锅"],
            "time": ["10到20分钟"],
        },
        "ingredients": [
            {"id": "ingredient-broccoli", "ingredient_name": "西兰花", "amount_text": "1 颗", "sort_order": 1},
            {"id": "ingredient-garlic", "ingredient_name": "大蒜", "amount_text": "3 瓣", "sort_order": 2},
            {"id": "ingredient-salt", "ingredient_name": "盐", "amount_text": "少许", "sort_order": 3},
        ],
        "steps": [
            {"id": "step-1", "step_no": 1, "title": "处理西兰花", "instruction": "把西兰花掰成小朵并清洗干净。"},
            {"id": "step-2", "step_no": 2, "title": "焯水", "instruction": "水开后加入少许盐，把西兰花焯 1 分钟捞出。"},
            {"id": "step-3", "step_no": 3, "title": "爆香蒜末", "instruction": "热锅下油，放入蒜末小火炒香。"},
            {"id": "step-4", "step_no": 4, "title": "翻炒西兰花", "instruction": "倒入西兰花快速翻炒均匀。"},
            {"id": "step-5", "step_no": 5, "title": "调味出锅", "instruction": "加少许盐调味，再翻匀后出锅。"},
        ],
        "tips": "焯水时间别太久，颜色和脆感会更好。",
    },
}


def build_recipe_preset(name: str) -> dict[str, Any]:
    if name not in RECIPE_PRESETS:
        raise ValueError(f"未知菜谱预设：{name}")
    return deepcopy(RECIPE_PRESETS[name])


def resolve_fixture_path(path_text: str) -> Path:
    path = Path(path_text)
    if not path.is_absolute():
        path = (PROJECT_ROOT / path_text).resolve()
    return path


def resolve_mime_type(path: Path, explicit: str | None = None) -> str:
    if explicit:
        return explicit
    return mimetypes.guess_type(path.name)[0] or "image/jpeg"


def resolve_catalog_reference(kind: str) -> Any:
    entries = recipe_catalog_service.list_entries()
    if not entries:
        raise ValueError("当前菜谱库为空，无法解析 catalog 占位符。")

    index_lookup = {
        "first": 0,
        "second": 1,
        "third": 2,
    }
    for prefix, index in index_lookup.items():
        if kind == f"{prefix}_id":
            if len(entries) <= index:
                raise ValueError(f"菜谱库不足以解析占位符：{kind}")
            return entries[index].id
        if kind == f"{prefix}_name":
            if len(entries) <= index:
                raise ValueError(f"菜谱库不足以解析占位符：{kind}")
            return entries[index].name

    raise ValueError(f"不支持的 catalog 占位符：{kind}")


def resolve_dynamic_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: resolve_dynamic_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [resolve_dynamic_value(item) for item in value]
    if isinstance(value, str) and value.startswith("$catalog:"):
        return resolve_catalog_reference(value.removeprefix("$catalog:"))
    return value

