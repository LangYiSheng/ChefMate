from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from pydantic import BaseModel


def bootstrap_path() -> None:
    backend_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(backend_root))


def print_section(title: str, payload) -> None:
    if isinstance(payload, BaseModel):
        payload = payload.model_dump(mode="json")
    print(f"\n=== {title} ===")
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def main() -> None:
    bootstrap_path()

    from app.skills.recommendation import recommendation_skill

    parser = argparse.ArgumentParser(description="ChefMate 推荐系统测试脚本")
    parser.add_argument("--all", action="store_true", help="运行全部示例测试")
    parser.add_argument("--name", type=str, help="按名字查询菜谱")
    parser.add_argument("--name-exact", action="store_true", help="名字查询是否精确匹配")
    parser.add_argument("--ingredients", nargs="*", help="按现有食材查菜谱")
    parser.add_argument("--ingredients-exact-only", action="store_true", help="只返回可直接做的菜")
    parser.add_argument("--flavor", nargs="*", default=None)
    parser.add_argument("--method", nargs="*", default=None)
    parser.add_argument("--scene", nargs="*", default=None)
    parser.add_argument("--health", nargs="*", default=None)
    parser.add_argument("--time", nargs="*", default=None)
    parser.add_argument("--tool", nargs="*", default=None)
    parser.add_argument("--difficulty", nargs="*", default=None)
    parser.add_argument("--match-mode", choices=["exact", "fuzzy"], default="fuzzy")
    parser.add_argument("--recipe-id", type=int, help="按 recipe_id 获取完整菜谱")
    parser.add_argument(
        "--include",
        nargs="*",
        help="详情查询时返回哪些部分，可选 recipe/details tags ingredients steps all",
    )
    parser.add_argument("--limit", type=int, default=5)
    args = parser.parse_args()

    if args.all:
        print_section(
            "名字模糊查：番茄炒蛋",
            recommendation_skill.search_recipes_by_name("番茄炒蛋", exact=False, limit=args.limit),
        )
        print_section(
            "标签模糊筛：清淡 + 快手 + 炒锅",
            recommendation_skill.filter_recipes_by_tags(
                flavor=["清淡"],
                scene=["快手"],
                tool=["炒锅"],
                match_mode="fuzzy",
                limit=args.limit,
            ),
        )
        print_section(
            "食材查：番茄 鸡蛋 葱",
            recommendation_skill.find_recipes_by_ingredients(
                ["番茄", "鸡蛋", "葱"],
                exact_only=False,
                limit=args.limit,
            ),
        )
        print_section(
            "按 ID 获取完整菜谱：1",
            recommendation_skill.get_recipe_by_id(1, include=["recipe", "tags", "ingredients", "steps"]),
        )
        return

    if args.name:
        print_section(
            f"名字查询：{args.name}",
            recommendation_skill.search_recipes_by_name(
                args.name,
                exact=args.name_exact,
                limit=args.limit,
            ),
        )

    has_tag_filter = any(
        value
        for value in [args.flavor, args.method, args.scene, args.health, args.time, args.tool, args.difficulty]
    )
    if has_tag_filter:
        print_section(
            "标签筛选",
            recommendation_skill.filter_recipes_by_tags(
                flavor=args.flavor,
                method=args.method,
                scene=args.scene,
                health=args.health,
                time=args.time,
                tool=args.tool,
                difficulty=args.difficulty,
                match_mode=args.match_mode,
                limit=args.limit,
            ),
        )

    if args.ingredients:
        print_section(
            "食材查询",
            recommendation_skill.find_recipes_by_ingredients(
                args.ingredients,
                exact_only=args.ingredients_exact_only,
                limit=args.limit,
            ),
        )

    if args.recipe_id is not None:
        print_section(
            f"菜谱详情：{args.recipe_id}",
            recommendation_skill.get_recipe_by_id(args.recipe_id, include=args.include),
        )


if __name__ == "__main__":
    main()
