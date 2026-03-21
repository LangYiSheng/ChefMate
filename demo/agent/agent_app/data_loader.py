from __future__ import annotations

import json
from pathlib import Path

from agent_app.models import IngredientRequirement, Recipe, UserProfile


DATA_DIR = Path(__file__).resolve().parent / "data"


def load_recipes() -> list[Recipe]:
    # 把 JSON 菜谱数据转成 dataclass，后面工具层就能直接按字段使用。
    raw = json.loads((DATA_DIR / "recipes.json").read_text(encoding="utf-8"))
    recipes: list[Recipe] = []
    for item in raw:
        recipes.append(
            Recipe(
                name=item["name"],
                aliases=item.get("aliases", []),
                summary=item["summary"],
                estimated_minutes=item["estimated_minutes"],
                difficulty=item["difficulty"],
                servings=item.get("servings", 2),
                flavor_tags=item.get("flavor_tags", []),
                health_tags=item.get("health_tags", []),
                available_tools=item.get("available_tools", []),
                ingredients=[
                    IngredientRequirement(
                        name=ingredient["name"],
                        amount=ingredient["amount"],
                        optional=ingredient.get("optional", False),
                        purpose=ingredient.get("purpose", ""),
                    )
                    for ingredient in item["ingredients"]
                ],
                steps=item["steps"],
                tips=item.get("tips", []),
            )
        )
    return recipes


def load_sample_profile() -> UserProfile:
    # demo 先带一份默认用户画像，方便开箱即用。
    raw = json.loads((DATA_DIR / "user_profile.sample.json").read_text(encoding="utf-8"))
    return UserProfile(
        flavor_preferences=raw.get("flavor_preferences", []),
        dietary_restrictions=raw.get("dietary_restrictions", []),
        health_goal=raw.get("health_goal", "均衡"),
        cooking_skill_level=raw.get("cooking_skill_level", "新手"),
        max_cook_time=raw.get("max_cook_time", 30),
        available_tools=raw.get("available_tools", ["炒锅", "汤锅", "电饭煲"]),
    )
