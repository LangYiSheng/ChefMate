from __future__ import annotations

from typing import Any, Literal
from uuid import uuid4

from app.domain.cards import has_ready_for_cooking
from app.domain.enums import IngredientStatus, StepStatus, TaskRecipeSourceType
from app.domain.models import TaskRecipeIngredient, TaskRecipeSnapshot, TaskRecipeStep


RecipeUpdateMode = Literal["planning", "shopping", "cooking"]

INGREDIENT_STATUS_ALIASES: dict[str, IngredientStatus] = {
    "pending": IngredientStatus.PENDING,
    "todo": IngredientStatus.PENDING,
    "not_ready": IngredientStatus.PENDING,
    "ready": IngredientStatus.READY,
    "done": IngredientStatus.READY,
    "completed": IngredientStatus.READY,
    "prepared": IngredientStatus.READY,
    "skipped": IngredientStatus.SKIPPED,
    "skip": IngredientStatus.SKIPPED,
}

STEP_STATUS_ALIASES: dict[str, StepStatus] = {
    "pending": StepStatus.PENDING,
    "todo": StepStatus.PENDING,
    "upcoming": StepStatus.PENDING,
    "current": StepStatus.CURRENT,
    "in_progress": StepStatus.CURRENT,
    "doing": StepStatus.CURRENT,
    "done": StepStatus.DONE,
    "completed": StepStatus.DONE,
    "finished": StepStatus.DONE,
}


def build_task_recipe_snapshot_from_catalog(lookup: Any) -> TaskRecipeSnapshot:
    if lookup is None or lookup.recipe is None:
        raise ValueError("指定的菜谱不存在。")
    ingredients = [
        TaskRecipeIngredient(
            id=f"ingredient-{index + 1}",
            ingredient_name=item.ingredient_name,
            amount_text=item.amount_text,
            amount_value=item.amount_value,
            unit=item.unit,
            is_optional=item.is_optional,
            purpose=item.purpose,
            sort_order=index,
            status=IngredientStatus.PENDING,
        )
        for index, item in enumerate(lookup.ingredients or [])
    ]
    steps = [
        TaskRecipeStep(
            id=f"step-{item.step_no}",
            step_no=item.step_no,
            title=item.title,
            instruction=item.instruction,
            timer_seconds=item.timer_seconds,
            notes=item.notes,
            status=StepStatus.CURRENT if index == 0 else StepStatus.PENDING,
        )
        for index, item in enumerate(lookup.steps or [])
    ]
    snapshot = TaskRecipeSnapshot(
        source_type=TaskRecipeSourceType.CATALOG,
        source_recipe_id=lookup.recipe.id,
        name=lookup.recipe.name,
        description=lookup.recipe.description or "",
        difficulty=lookup.recipe.difficulty,
        estimated_minutes=lookup.recipe.estimated_minutes,
        servings=lookup.recipe.servings,
        tags=lookup.tags or {},
        ingredients=ingredients,
        steps=steps,
        tips=lookup.recipe.tips,
    )
    normalize_snapshot_defaults(snapshot)
    normalize_step_progress(snapshot)
    return snapshot


def build_task_recipe_snapshot_from_generated(recipe_payload: dict[str, Any]) -> TaskRecipeSnapshot:
    snapshot = TaskRecipeSnapshot(**recipe_payload)
    if snapshot.source_type != TaskRecipeSourceType.GENERATED:
        snapshot.source_type = TaskRecipeSourceType.GENERATED
    snapshot.ingredients = [
        ingredient.model_copy(
            update={
                "id": ingredient.id or str(uuid4()),
                "sort_order": ingredient.sort_order if ingredient.sort_order is not None else index,
                "status": ingredient.status or IngredientStatus.PENDING,
            }
        )
        for index, ingredient in enumerate(snapshot.ingredients)
    ]
    normalized_steps = []
    for index, step in enumerate(sorted(snapshot.steps, key=lambda item: item.step_no)):
        normalized_steps.append(
            step.model_copy(
                update={
                    "id": step.id or f"step-{step.step_no}",
                    "status": step.status or (StepStatus.CURRENT if index == 0 else StepStatus.PENDING),
                }
            )
        )
    snapshot.steps = normalized_steps
    normalize_snapshot_defaults(snapshot)
    normalize_step_progress(snapshot)
    return snapshot


def load_task_recipe_snapshot(raw: str | dict[str, Any] | None) -> TaskRecipeSnapshot | None:
    if raw is None:
        return None
    if isinstance(raw, TaskRecipeSnapshot):
        return raw
    if isinstance(raw, dict):
        snapshot = TaskRecipeSnapshot(**_sanitize_snapshot_payload(raw))
    else:
        import json

        snapshot = TaskRecipeSnapshot(**_sanitize_snapshot_payload(json.loads(raw)))
    normalize_snapshot_defaults(snapshot)
    normalize_step_progress(snapshot)
    return snapshot


def dump_task_recipe_snapshot(snapshot: TaskRecipeSnapshot | None) -> str | None:
    if snapshot is None:
        return None
    import json

    return json.dumps(snapshot.model_dump(mode="json"), ensure_ascii=False)


def flatten_recipe_tags(tags: dict[str, list[str]]) -> list[str]:
    return [item for values in tags.values() for item in values]


def apply_recipe_patch(
    snapshot: TaskRecipeSnapshot,
    patch: dict[str, Any],
    *,
    mode: RecipeUpdateMode,
) -> TaskRecipeSnapshot:
    allowed_top_level = {
        "planning": {
            "name",
            "description",
            "difficulty",
            "estimated_minutes",
            "servings",
            "tags",
            "tips",
            "ingredients",
            "steps",
        },
        "shopping": {"ingredients", "steps"},
        "cooking": {"steps"},
    }[mode]
    unknown_top_level = set(patch) - allowed_top_level
    if unknown_top_level:
        raise ValueError(f"当前阶段不能更新这些字段：{sorted(unknown_top_level)}")

    for field in ("name", "description", "difficulty", "estimated_minutes", "servings", "tags", "tips"):
        if field in patch:
            setattr(snapshot, field, patch[field])

    if "ingredients" in patch:
        if mode == "cooking":
            raise ValueError("烹饪中阶段不能再修改食材准备状态。")
        _apply_ingredient_patch(snapshot, patch["ingredients"], allow_add=True)

    if "steps" in patch:
        _apply_step_patch(snapshot, patch["steps"], allow_add=(mode == "planning"))

    normalize_snapshot_defaults(snapshot)
    normalize_step_progress(snapshot)
    return snapshot


def ensure_can_enter_preparation(snapshot: TaskRecipeSnapshot | None) -> None:
    if snapshot is None:
        raise ValueError("当前任务还没有菜谱，不能进入备料阶段。")
    if not snapshot.ingredients or not snapshot.steps:
        raise ValueError("当前菜谱信息不完整，至少需要食材和步骤。")


def ensure_can_enter_cooking(snapshot: TaskRecipeSnapshot | None) -> None:
    ensure_can_enter_preparation(snapshot)
    if not has_ready_for_cooking(snapshot):
        raise ValueError("还有必需食材未备齐，不能进入烹饪阶段。")


def ensure_can_complete(snapshot: TaskRecipeSnapshot | None) -> None:
    if snapshot is None:
        raise ValueError("当前没有可完成的任务。")
    if any(step.status != StepStatus.DONE for step in snapshot.steps):
        raise ValueError("还有步骤未完成，暂时不能结束本次烹饪。")


def normalize_step_progress(snapshot: TaskRecipeSnapshot) -> None:
    ordered_steps = sorted(snapshot.steps, key=lambda item: item.step_no)
    current_exists = any(step.status == StepStatus.CURRENT for step in ordered_steps)
    if current_exists:
        seen_current = False
        for step in ordered_steps:
            if step.status == StepStatus.CURRENT and not seen_current:
                seen_current = True
                continue
            if step.status == StepStatus.CURRENT and seen_current:
                step.status = StepStatus.PENDING
        snapshot.steps = ordered_steps
        return

    for step in ordered_steps:
        if step.status != StepStatus.DONE:
            step.status = StepStatus.CURRENT
            break
    snapshot.steps = ordered_steps


def normalize_snapshot_defaults(snapshot: TaskRecipeSnapshot) -> None:
    snapshot.ingredients = [
        ingredient.model_copy(
            update={
                "sort_order": ingredient.sort_order if ingredient.sort_order is not None else index,
                "status": normalize_ingredient_status(ingredient.status),
                "amount_text": ingredient.amount_text or "适量",
            }
        )
        for index, ingredient in enumerate(snapshot.ingredients)
    ]
    snapshot.steps = [
        step.model_copy(
            update={
                "status": normalize_step_status(step.status),
            }
        )
        for step in sorted(snapshot.steps, key=lambda item: item.step_no)
    ]


def normalize_ingredient_status(value: IngredientStatus | str | None) -> IngredientStatus:
    if isinstance(value, IngredientStatus):
        return value
    normalized = str(value or "").strip().lower()
    if not normalized:
        return IngredientStatus.PENDING
    if normalized in INGREDIENT_STATUS_ALIASES:
        return INGREDIENT_STATUS_ALIASES[normalized]
    raise ValueError(f"不支持的食材状态：{value}")


def normalize_step_status(value: StepStatus | str | None) -> StepStatus:
    if isinstance(value, StepStatus):
        return value
    normalized = str(value or "").strip().lower()
    if not normalized:
        return StepStatus.PENDING
    if normalized in STEP_STATUS_ALIASES:
        return STEP_STATUS_ALIASES[normalized]
    raise ValueError(f"不支持的步骤状态：{value}")


def _sanitize_snapshot_payload(raw: dict[str, Any]) -> dict[str, Any]:
    payload = dict(raw)

    ingredients: list[dict[str, Any]] = []
    for index, item in enumerate(payload.get("ingredients") or []):
        if not isinstance(item, dict):
            continue
        next_item = dict(item)
        next_item["sort_order"] = next_item.get("sort_order") if next_item.get("sort_order") is not None else index
        next_item["status"] = normalize_ingredient_status(next_item.get("status"))
        next_item["amount_text"] = next_item.get("amount_text") or "适量"
        ingredients.append(next_item)
    payload["ingredients"] = ingredients

    steps: list[dict[str, Any]] = []
    for item in payload.get("steps") or []:
        if not isinstance(item, dict):
            continue
        next_item = dict(item)
        next_item["status"] = normalize_step_status(next_item.get("status"))
        steps.append(next_item)
    payload["steps"] = steps
    return payload


def _apply_ingredient_patch(
    snapshot: TaskRecipeSnapshot,
    payload: list[dict[str, Any]],
    *,
    allow_add: bool,
) -> None:
    allowed_fields = {
        "id",
        "ingredient_name",
        "amount_text",
        "amount_value",
        "unit",
        "is_optional",
        "purpose",
        "sort_order",
        "status",
        "note",
    }
    for item in payload:
        unknown_fields = set(item) - allowed_fields
        if unknown_fields:
            raise ValueError(f"食材更新包含不允许的字段：{sorted(unknown_fields)}")
        target = None
        if item.get("id"):
            target = next((entry for entry in snapshot.ingredients if entry.id == item["id"]), None)
        if target is None and item.get("ingredient_name"):
            target = next(
                (
                    entry
                    for entry in snapshot.ingredients
                    if entry.ingredient_name == item["ingredient_name"]
                ),
                None,
            )
        if target is None:
            if not allow_add:
                raise ValueError("试图更新不存在的食材。")
            snapshot.ingredients.append(
                TaskRecipeIngredient(
                    id=item.get("id") or str(uuid4()),
                    ingredient_name=item["ingredient_name"],
                    amount_text=item.get("amount_text") or "适量",
                    amount_value=item.get("amount_value"),
                    unit=item.get("unit"),
                    is_optional=bool(item.get("is_optional", False)),
                    purpose=item.get("purpose"),
                    sort_order=int(item.get("sort_order", len(snapshot.ingredients))),
                    status=normalize_ingredient_status(item.get("status")),
                    note=item.get("note"),
                )
            )
            continue

        for field in allowed_fields - {"id", "ingredient_name"}:
            if field not in item or item[field] is None:
                continue
            if field == "status":
                setattr(target, field, normalize_ingredient_status(item[field]))
                continue
            if field == "sort_order":
                setattr(target, field, int(item[field]))
                continue
            setattr(target, field, item[field])


def _apply_step_patch(
    snapshot: TaskRecipeSnapshot,
    payload: list[dict[str, Any]],
    *,
    allow_add: bool,
) -> None:
    allowed_fields = {
        "id",
        "step_no",
        "title",
        "instruction",
        "timer_seconds",
        "notes",
        "status",
        "note",
    }
    for item in payload:
        unknown_fields = set(item) - allowed_fields
        if unknown_fields:
            raise ValueError(f"步骤更新包含不允许的字段：{sorted(unknown_fields)}")
        target = None
        if item.get("id"):
            target = next((entry for entry in snapshot.steps if entry.id == item["id"]), None)
        if target is None and item.get("step_no") is not None:
            target = next((entry for entry in snapshot.steps if entry.step_no == item["step_no"]), None)
        if target is None:
            if not allow_add:
                raise ValueError("试图更新不存在的步骤。")
            snapshot.steps.append(
                TaskRecipeStep(
                    id=item.get("id") or f"step-{item['step_no']}",
                    step_no=int(item["step_no"]),
                    title=item.get("title"),
                    instruction=item.get("instruction") or "",
                    timer_seconds=item.get("timer_seconds"),
                    notes=item.get("notes"),
                    status=normalize_step_status(item.get("status")),
                    note=item.get("note"),
                )
            )
            continue

        for field in allowed_fields - {"id", "step_no"}:
            if field not in item or item[field] is None:
                continue
            if field == "status":
                setattr(target, field, normalize_step_status(item[field]))
                continue
            setattr(target, field, item[field])
