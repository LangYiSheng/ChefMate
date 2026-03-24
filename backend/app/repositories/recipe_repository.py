from __future__ import annotations

from collections import defaultdict

from sqlalchemy import bindparam, text

from app.db.connection import engine
from app.db.contracts import (
    RecipeIngredientRecord,
    RecipeRecord,
    RecipeStepRecord,
    RecipeTagCategoryRecord,
    RecipeTagMapRecord,
    RecipeTagRecord,
)


class RecipeRepository:
    def list_published_recipes(self) -> list[RecipeRecord]:
        query = text(
            """
            SELECT
                id,
                name,
                image_path,
                description,
                difficulty,
                estimated_minutes,
                servings,
                tips,
                status
            FROM recipe
            WHERE status = 'PUBLISHED'
            ORDER BY id
            """
        )
        with engine.connect() as conn:
            rows = conn.execute(query).mappings().all()
        return [RecipeRecord(**row) for row in rows]

    def search_published_recipes_by_name(self, query_text: str, *, exact: bool, limit: int) -> list[RecipeRecord]:
        if exact:
            query = text(
                """
                SELECT
                    id,
                    name,
                    image_path,
                    description,
                    difficulty,
                    estimated_minutes,
                    servings,
                    tips,
                    status
                FROM recipe
                WHERE status = 'PUBLISHED'
                  AND name = :query_text
                ORDER BY id
                LIMIT :limit
                """
            )
            params = {"query_text": query_text, "limit": limit}
        else:
            query = text(
                """
                SELECT
                    id,
                    name,
                    image_path,
                    description,
                    difficulty,
                    estimated_minutes,
                    servings,
                    tips,
                    status
                FROM recipe
                WHERE status = 'PUBLISHED'
                  AND name LIKE :query_text
                ORDER BY id
                LIMIT :limit
                """
            )
            params = {"query_text": f"%{query_text}%", "limit": limit}

        with engine.connect() as conn:
            rows = conn.execute(query, params).mappings().all()
        return [RecipeRecord(**row) for row in rows]

    def get_recipe(self, recipe_id: int) -> RecipeRecord | None:
        query = text(
            """
            SELECT
                id,
                name,
                image_path,
                description,
                difficulty,
                estimated_minutes,
                servings,
                tips,
                status
            FROM recipe
            WHERE id = :recipe_id
            """
        )
        with engine.connect() as conn:
            row = conn.execute(query, {"recipe_id": recipe_id}).mappings().first()
        return RecipeRecord(**row) if row else None

    def get_ingredients_by_recipe_ids(self, recipe_ids: list[int]) -> dict[int, list[RecipeIngredientRecord]]:
        if not recipe_ids:
            return {}
        query = (
            text(
                """
                SELECT
                    id,
                    recipe_id,
                    ingredient_name,
                    amount_value,
                    amount_text,
                    unit,
                    is_optional,
                    purpose,
                    sort_order
                FROM recipe_ingredient
                WHERE recipe_id IN :recipe_ids
                ORDER BY recipe_id, sort_order, id
                """
            )
            .bindparams(bindparam("recipe_ids", expanding=True))
        )
        with engine.connect() as conn:
            rows = conn.execute(query, {"recipe_ids": recipe_ids}).mappings().all()

        grouped: dict[int, list[RecipeIngredientRecord]] = defaultdict(list)
        for row in rows:
            grouped[row["recipe_id"]].append(RecipeIngredientRecord(**row))
        return dict(grouped)

    def get_steps_by_recipe_ids(self, recipe_ids: list[int]) -> dict[int, list[RecipeStepRecord]]:
        if not recipe_ids:
            return {}
        query = (
            text(
                """
                SELECT
                    id,
                    recipe_id,
                    step_no,
                    title,
                    instruction,
                    timer_seconds,
                    notes
                FROM recipe_step
                WHERE recipe_id IN :recipe_ids
                ORDER BY recipe_id, step_no
                """
            )
            .bindparams(bindparam("recipe_ids", expanding=True))
        )
        with engine.connect() as conn:
            rows = conn.execute(query, {"recipe_ids": recipe_ids}).mappings().all()

        grouped: dict[int, list[RecipeStepRecord]] = defaultdict(list)
        for row in rows:
            grouped[row["recipe_id"]].append(RecipeStepRecord(**row))
        return dict(grouped)

    def get_tags_by_recipe_ids(self, recipe_ids: list[int]) -> dict[int, dict[str, list[str]]]:
        if not recipe_ids:
            return {}
        query = (
            text(
                """
                SELECT
                    m.recipe_id,
                    c.category_code,
                    t.tag_name
                FROM recipe_tag_map m
                JOIN recipe_tag t ON t.id = m.tag_id
                JOIN recipe_tag_category c ON c.id = t.category_id
                WHERE m.recipe_id IN :recipe_ids
                  AND t.is_enabled = 1
                ORDER BY m.recipe_id, c.sort_order, t.sort_order, t.id
                """
            )
            .bindparams(bindparam("recipe_ids", expanding=True))
        )
        with engine.connect() as conn:
            rows = conn.execute(query, {"recipe_ids": recipe_ids}).mappings().all()

        grouped: dict[int, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))
        for row in rows:
            grouped[row["recipe_id"]][row["category_code"]].append(row["tag_name"])
        return {recipe_id: dict(tags) for recipe_id, tags in grouped.items()}

    def get_tag_taxonomy(self) -> dict[str, list[str]]:
        query = text(
            """
            SELECT
                c.category_code,
                t.tag_name
            FROM recipe_tag t
            JOIN recipe_tag_category c ON c.id = t.category_id
            WHERE t.is_enabled = 1
            ORDER BY c.sort_order, t.sort_order, t.id
            """
        )
        with engine.connect() as conn:
            rows = conn.execute(query).mappings().all()

        taxonomy: dict[str, list[str]] = defaultdict(list)
        for row in rows:
            taxonomy[row["category_code"]].append(row["tag_name"])
        taxonomy["difficulty"] = ["简单", "中等", "困难"]
        return dict(taxonomy)


recipe_repository = RecipeRepository()
