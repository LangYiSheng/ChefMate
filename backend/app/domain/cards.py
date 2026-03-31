from __future__ import annotations

from app.domain.enums import CardActionType, CardType, IngredientStatus, StepStatus
from app.domain.models import (
    CardAction,
    CookingGuideCard,
    CookingGuideStep,
    PantryChecklistItem,
    PantryStatusCard,
    RecipeDetailCard,
    RecipeRecommendationCardItem,
    RecipeRecommendationsCard,
    RecipeSummaryCardRecipe,
    TaskRecipeSnapshot,
)


def format_duration(timer_seconds: int | None) -> str:
    if not timer_seconds:
        return "跟着感觉推进"
    if timer_seconds < 60:
        return f"{timer_seconds} 秒"
    return f"{round(timer_seconds / 60)} 分钟"


def build_recipe_recommendations_card(recipes: list[dict]) -> RecipeRecommendationsCard:
    return RecipeRecommendationsCard(
        title="给你先挑了这几道",
        recipes=[
            RecipeRecommendationCardItem(
                recipe_id=item["id"],
                name=item["name"],
                description=item.get("description") or "",
                tags=item.get("tags", []),
                difficulty=item["difficulty"],
                estimated_minutes=item["estimated_minutes"],
                servings=item["servings"],
                actions=[
                    CardAction(
                        id=f"view-{item['id']}",
                        label="查看详情",
                        action_type=CardActionType.VIEW_RECIPE,
                        payload={"recipe_id": item["id"]},
                    ),
                    CardAction(
                        id=f"try-{item['id']}",
                        label="想尝试",
                        action_type=CardActionType.TRY_RECIPE,
                        payload={"recipe_id": item["id"]},
                    ),
                ],
            )
            for item in recipes
        ],
    )


def build_recipe_detail_card(
    recipe: TaskRecipeSnapshot,
    *,
    source_recipe_id: int | None = None,
    include_try_action: bool = True,
) -> RecipeDetailCard:
    actions: list[CardAction] = []
    if include_try_action and source_recipe_id is not None:
        actions.append(
            CardAction(
                id=f"try-{source_recipe_id}",
                label="想尝试",
                action_type=CardActionType.TRY_RECIPE,
                payload={"recipe_id": source_recipe_id},
            )
        )
    return RecipeDetailCard(
        recipe=RecipeSummaryCardRecipe(
            id=source_recipe_id or 0,
            name=recipe.name,
            description=recipe.description,
            difficulty=recipe.difficulty,
            estimated_minutes=recipe.estimated_minutes,
            servings=recipe.servings,
            tags=[tag for values in recipe.tags.values() for tag in values],
            ingredients=recipe.ingredients,
            steps=recipe.steps,
            tips=recipe.tips,
        ),
        actions=actions,
    )


def build_pantry_status_card(recipe: TaskRecipeSnapshot) -> PantryStatusCard:
    return PantryStatusCard(
        title=f"{recipe.name} 备料清单",
        checklist=[
            PantryChecklistItem(
                id=item.id,
                ingredient=item.ingredient_name,
                amount=item.amount_text,
                status=item.status,
                note=item.note or item.purpose,
                is_optional=item.is_optional,
            )
            for item in sorted(
                recipe.ingredients,
                key=lambda entry: (
                    entry.sort_order if entry.sort_order is not None else 10**9,
                    entry.id,
                ),
            )
        ],
        actions=[
            CardAction(
                id="ingredients-ready",
                label="这些都备齐了",
                action_type=CardActionType.INGREDIENTS_READY,
                payload={},
            )
        ],
    )


def build_cooking_guide_card(recipe: TaskRecipeSnapshot) -> CookingGuideCard:
    current_step = 1
    for step in sorted(recipe.steps, key=lambda entry: entry.step_no):
        if step.status == StepStatus.CURRENT:
            current_step = step.step_no
            break
        if step.status == StepStatus.DONE:
            current_step = min(step.step_no + 1, len(recipe.steps) or 1)

    return CookingGuideCard(
        title=f"{recipe.name} 烹饪步骤",
        current_step=current_step,
        total_steps=len(recipe.steps),
        steps=[
            CookingGuideStep(
                id=item.id,
                title=item.title or f"步骤 {item.step_no}",
                detail=item.instruction,
                duration=format_duration(item.timer_seconds),
                timer_seconds=item.timer_seconds,
                notes=item.note or item.notes,
                status=item.status,
            )
            for item in sorted(recipe.steps, key=lambda entry: entry.step_no)
        ],
    )


def has_ready_for_cooking(recipe: TaskRecipeSnapshot) -> bool:
    required = [item for item in recipe.ingredients if not item.is_optional]
    if not required:
        return True
    return all(item.status == IngredientStatus.READY for item in required)
