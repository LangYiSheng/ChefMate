from __future__ import annotations

from typing import Any

from app.agent.runtime import AgentTurnContext
from app.agent.tool_schemas import IngredientPatchInput, PlanningRecipePatchInput, StepPatchInput
from app.domain.cards import build_recipe_recommendations_card
from app.services.recipe_catalog_service import recipe_catalog_service
from app.utils.recipe_snapshot import flatten_recipe_tags


def build_task_patch_payload(
    *,
    ingredients: list[IngredientPatchInput] | None = None,
    steps: list[StepPatchInput] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    if ingredients:
        payload["ingredients"] = [
            item.model_dump(mode="json", exclude_none=True, exclude_unset=True)
            for item in ingredients
        ]
    if steps:
        payload["steps"] = [
            item.model_dump(mode="json", exclude_none=True, exclude_unset=True)
            for item in steps
        ]
    return payload


def build_planning_patch_payload(patch: PlanningRecipePatchInput) -> dict[str, Any]:
    payload = patch.model_dump(mode="json", exclude_none=True, exclude_unset=True)
    return {key: value for key, value in payload.items() if value != []}


def has_ingredient_status_updates(items: list[IngredientPatchInput] | None) -> bool:
    return any(item.status is not None for item in (items or []))


def has_step_status_updates(items: list[StepPatchInput] | None) -> bool:
    return any(item.status is not None for item in (items or []))


def validate_recipe_tag_filters(
    *,
    flavor: list[str] | None = None,
    method: list[str] | None = None,
    scene: list[str] | None = None,
    health: list[str] | None = None,
    time: list[str] | None = None,
    tool: list[str] | None = None,
    difficulty: list[str] | None = None,
    allow_alias: bool = False,
) -> dict[str, list[str]]:
    raw_tag_filters = {
        "flavor": flavor or [],
        "method": method or [],
        "scene": scene or [],
        "health": health or [],
        "time": time or [],
        "tool": tool or [],
        "difficulty": difficulty or [],
    }
    return recipe_catalog_service.validate_tag_filters(
        raw_tag_filters,
        categories=raw_tag_filters.keys(),
        allow_alias=allow_alias,
    )


def rank_candidate_ids(
    entries: dict[int, Any],
    candidate_scores: dict[int, float],
) -> list[int]:
    return [
        item_id
        for item_id, _ in sorted(candidate_scores.items(), key=lambda pair: (-pair[1], pair[0]))
        if item_id in entries
    ]


def set_recipe_recommendation_card(
    current_turn: AgentTurnContext,
    chosen_entries: list[Any],
) -> None:
    current_turn.response_card_type = "recipe-recommendations"
    current_turn.response_card = build_recipe_recommendations_card(
        [
            {
                "id": entry.id,
                "name": entry.name,
                "description": entry.description or "",
                "tags": flatten_recipe_tags(entry.tags)[:4],
                "difficulty": entry.difficulty,
                "estimated_minutes": entry.estimated_minutes,
                "servings": entry.servings,
            }
            for entry in chosen_entries
        ]
    ).model_dump(mode="json")


def format_recipe_candidate(entry: Any) -> str:
    tags = "/".join(flatten_recipe_tags(entry.tags)[:4])
    tag_text = f"，标签：{tags}" if tags else ""
    return f"{entry.id} - {entry.name}（{entry.estimated_minutes} 分钟，{entry.difficulty}{tag_text}）"


def search_candidate_scores(
    *,
    query: str | None,
    ingredients: list[str] | None,
    step_text: str | None,
    tag_filters: dict[str, list[str]],
    limit: int,
    name_match_first: bool,
) -> tuple[dict[int, float], list[str], list[str], dict[int, set[str]]]:
    candidate_scores: dict[int, float] = {}
    candidate_sources: dict[int, set[str]] = {}
    attempted: list[str] = []
    resolved_ingredients = [item.strip() for item in (ingredients or []) if item and item.strip()]

    if query and name_match_first:
        attempted.append(f"完整菜名：{query}")
        for item in recipe_catalog_service.search_recipes_by_name(query, exact=True, limit=limit * 4)["candidates"]:
            candidate_scores[item["id"]] = max(candidate_scores.get(item["id"], 0.0), 3.0 + item.get("score", 0.0))
            candidate_sources.setdefault(item["id"], set()).add("name")
        for item in recipe_catalog_service.search_recipes_by_name(query, exact=False, limit=limit * 4)["candidates"]:
            candidate_scores[item["id"]] = max(candidate_scores.get(item["id"], 0.0), 2.0 + item.get("score", 0.0))
            candidate_sources.setdefault(item["id"], set()).add("name")
        if candidate_scores:
            return candidate_scores, attempted, resolved_ingredients, candidate_sources

    if query and not resolved_ingredients:
        resolved_ingredients = recipe_catalog_service.extract_ingredient_terms_from_text(query)

    if resolved_ingredients:
        attempted.append(f"食材：{'、'.join(resolved_ingredients)}")
        for item in recipe_catalog_service.find_recipes_by_ingredients(resolved_ingredients, exact_only=False, limit=limit * 4)["candidates"]:
            candidate_scores[item["id"]] = max(candidate_scores.get(item["id"], 0.0), 1.0 + item.get("score", 0.0))
            candidate_sources.setdefault(item["id"], set()).add("ingredients")

    if any(tag_filters.values()):
        attempted.append(
            "标签："
            + "；".join(
                f"{category}={','.join(values)}"
                for category, values in tag_filters.items()
                if values
            )
        )
        for item in recipe_catalog_service.filter_recipes_by_tags(match_mode="fuzzy", limit=limit * 4, **tag_filters)["candidates"]:
            candidate_scores[item["id"]] = max(candidate_scores.get(item["id"], 0.0), item.get("score", 0.0))
            candidate_sources.setdefault(item["id"], set()).add("tags")

    if step_text:
        attempted.append(f"步骤文本：{step_text}")
        for item in recipe_catalog_service.search_recipes_by_step_text(step_text, limit=limit * 4)["candidates"]:
            candidate_scores[item["id"]] = max(candidate_scores.get(item["id"], 0.0), 0.75 + item.get("score", 0.0))
            candidate_sources.setdefault(item["id"], set()).add("step_text")

    return candidate_scores, attempted, resolved_ingredients, candidate_sources
