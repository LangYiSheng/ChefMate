from __future__ import annotations

from app.db.contracts import RecipeIngredientRecord, RecipeRecord
from app.domain.models import UserProfileSnapshot
from app.repositories.conversation_repository import conversation_repository
from app.repositories.recipe_repository import recipe_repository
from app.schemas.recipe import (
    RecipeDetailResponse,
    RecipeIngredientResponse,
    RecipeListResponse,
    RecipeSummaryResponse,
)
from app.services.recipe_catalog_service import RecipeCatalogEntry, recipe_catalog_service


class RecipeService:
    SEARCH_FIELDS = ("name", "ingredient", "method", "flavor")
    TAG_MATCH_WEIGHTS = {
        "flavor": 2.0,
        "method": 1.2,
        "scene": 1.5,
        "health": 1.7,
        "time": 1.5,
        "tool": 1.4,
        "difficulty": 1.0,
    }

    def list_recipes(
        self,
        *,
        user: UserProfileSnapshot,
        keyword: str | None = None,
        tag: str | None = None,
        search_fields: list[str] | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> RecipeListResponse:
        resolved_search_fields = self._resolve_search_fields(search_fields) if keyword and keyword.strip() else []
        entries = self._load_summary_entries()
        entry_map = {entry.id: entry for entry in entries}
        recent_items = self._build_recent_recipe_summaries(user=user, entry_map=entry_map, limit=3)

        if keyword and keyword.strip():
            searchable_entries = entries
            if "ingredient" in resolved_search_fields:
                searchable_entries = self._attach_ingredients(entries)
            entries = self._search_entries(
                entries=searchable_entries,
                keyword=keyword,
                search_fields=resolved_search_fields,
            )
        else:
            entries = self._recommend_entries_for_user(user=user, entries=entries)

        if tag and tag.strip():
            entries = [
                entry
                for entry in entries
                if any(tag.strip() == tag_name for tags in entry.tags.values() for tag_name in tags)
            ]

        total = len(entries)
        sliced = entries[offset : offset + limit]
        return RecipeListResponse(
            items=[
                self._to_summary_response(entry)
                for entry in sliced
            ],
            recent_items=recent_items,
            total=total,
            limit=limit,
            offset=offset,
        )

    def _resolve_search_fields(self, search_fields: list[str] | None) -> list[str]:
        if not search_fields:
            return list(self.SEARCH_FIELDS)

        normalized: list[str] = []
        invalid: list[str] = []
        for field in search_fields:
            value = field.strip().lower()
            if not value:
                continue
            if value in self.SEARCH_FIELDS:
                if value not in normalized:
                    normalized.append(value)
                continue
            invalid.append(field)

        if invalid:
            available = "、".join(self.SEARCH_FIELDS)
            raise ValueError(f"搜索范围不合法：{'、'.join(invalid)}。可选范围有：{available}")
        return normalized or list(self.SEARCH_FIELDS)

    def _search_entries(
        self,
        *,
        entries: list[RecipeCatalogEntry],
        keyword: str,
        search_fields: list[str],
    ) -> list[RecipeCatalogEntry]:
        tokens = self._normalize_tokens(keyword)
        if not tokens:
            return entries

        scored_entries: list[tuple[float, RecipeCatalogEntry]] = []
        for entry in entries:
            score = 0.0

            if "name" in search_fields:
                score += self._score_text_match(entry.name, tokens, weight=4.2)
                score += self._score_text_match(entry.description or "", tokens, weight=1.2)

            if "ingredient" in search_fields:
                score += sum(
                    self._score_text_match(ingredient.ingredient_name, tokens, weight=3.4)
                    for ingredient in entry.ingredients
                )

            if "method" in search_fields:
                score += sum(
                    self._score_text_match(tag_name, tokens, weight=2.5)
                    for tag_name in entry.tags.get("method", [])
                )

            if "flavor" in search_fields:
                score += sum(
                    self._score_text_match(tag_name, tokens, weight=2.8)
                    for tag_name in entry.tags.get("flavor", [])
                )

            if score <= 0:
                continue
            scored_entries.append((score, entry))

        scored_entries.sort(key=lambda item: (-item[0], item[1].estimated_minutes, item[1].id))
        return [entry for _, entry in scored_entries]

    def _recommend_entries_for_user(
        self,
        *,
        user: UserProfileSnapshot,
        entries: list[RecipeCatalogEntry],
    ) -> list[RecipeCatalogEntry]:
        entry_map = {entry.id: entry for entry in entries}
        tag_filters = {
            category: values
            for category, values in user.tag_selections.model_dump().items()
            if values
        }
        if not tag_filters:
            return sorted(entries, key=lambda item: (item.estimated_minutes, item.id))

        validated_filters = recipe_catalog_service.validate_tag_filters(
            tag_filters,
            categories=tag_filters.keys(),
            allow_alias=False,
        )
        scored_entries: list[tuple[float, RecipeCatalogEntry]] = []
        for entry in entries:
            score = self._score_tag_preferences(entry, validated_filters)
            if score <= 0:
                continue
            scored_entries.append((score, entry))

        scored_entries.sort(key=lambda item: (-item[0], item[1].estimated_minutes, item[1].id))
        ordered_ids = [entry.id for _, entry in scored_entries]
        fallback_ids = [
            entry.id
            for entry in sorted(entries, key=lambda item: (item.estimated_minutes, item.id))
            if entry.id not in ordered_ids
        ]
        ordered_ids.extend(fallback_ids)
        return [entry_map[item_id] for item_id in ordered_ids if item_id in entry_map]

    def _load_summary_entries(self) -> list[RecipeCatalogEntry]:
        recipes = recipe_repository.list_published_recipes()
        recipe_ids = [item.id for item in recipes]
        tags_map = recipe_repository.get_tags_by_recipe_ids(recipe_ids)
        return [self._build_summary_entry(recipe=item, tags=tags_map.get(item.id, {})) for item in recipes]

    def _attach_ingredients(self, entries: list[RecipeCatalogEntry]) -> list[RecipeCatalogEntry]:
        recipe_ids = [entry.id for entry in entries]
        ingredients_map = recipe_repository.get_ingredients_by_recipe_ids(recipe_ids)
        return [
            entry.model_copy(
                update={
                    "ingredients": [
                        self._build_ingredient_response(item)
                        for item in ingredients_map.get(entry.id, [])
                    ]
                }
            )
            for entry in entries
        ]

    def _build_summary_entry(self, *, recipe: RecipeRecord, tags: dict[str, list[str]]) -> RecipeCatalogEntry:
        return RecipeCatalogEntry(
            id=recipe.id,
            name=recipe.name,
            aliases=[],
            image_path=recipe.image_path,
            description=recipe.description,
            difficulty=recipe.difficulty,
            estimated_minutes=recipe.estimated_minutes,
            servings=recipe.servings,
            tips=recipe.tips,
            tags=tags,
            ingredients=[],
            steps=[],
        )

    def _build_ingredient_response(self, item: RecipeIngredientRecord) -> RecipeIngredientResponse:
        return RecipeIngredientResponse(
            id=item.id,
            ingredient_name=item.ingredient_name,
            amount_text=item.amount_text,
            amount_value=float(item.amount_value) if item.amount_value is not None else None,
            unit=item.unit,
            is_optional=item.is_optional,
            purpose=item.purpose,
            sort_order=item.sort_order,
        )

    def _to_summary_response(
        self,
        entry: RecipeCatalogEntry,
        *,
        recent_activity: str | None = None,
    ) -> RecipeSummaryResponse:
        return RecipeSummaryResponse(
            id=entry.id,
            name=entry.name,
            description=entry.description,
            difficulty=entry.difficulty,
            estimated_minutes=entry.estimated_minutes,
            servings=entry.servings,
            tags=[tag_name for tags in entry.tags.values() for tag_name in tags],
            image_path=entry.image_path,
            recent_activity=recent_activity,
        )

    def _build_recent_recipe_summaries(
        self,
        *,
        user: UserProfileSnapshot,
        entry_map: dict[int, RecipeCatalogEntry],
        limit: int,
    ) -> list[RecipeSummaryResponse]:
        recent_tasks = conversation_repository.list_recent_finished_source_recipes(
            user_id=user.id,
            limit=limit,
        )
        summaries: list[RecipeSummaryResponse] = []
        for item in recent_tasks:
            recipe_id = item.get("source_recipe_id")
            if not isinstance(recipe_id, int) or recipe_id not in entry_map:
                continue
            summaries.append(
                self._to_summary_response(
                    entry_map[recipe_id],
                    recent_activity=self._format_recent_activity(item.get("ended_at")),
                )
            )
        return summaries

    def _score_tag_preferences(
        self,
        entry: RecipeCatalogEntry,
        filters: dict[str, list[str]],
    ) -> float:
        score = 0.0
        total_weight = 0.0
        for category, values in filters.items():
            if not values:
                continue
            weight = self.TAG_MATCH_WEIGHTS.get(category, 1.0)
            total_weight += weight
            if category == "difficulty":
                matched = values if entry.difficulty in values else []
            else:
                matched = [value for value in values if value in entry.tags.get(category, [])]
            score += weight * (len(matched) / len(values))
        if total_weight <= 0:
            return 0.0
        return score / total_weight

    def _format_recent_activity(self, ended_at: object) -> str:
        if hasattr(ended_at, "strftime"):
            return f"最近完成于 {ended_at.strftime('%m-%d %H:%M')}"
        return "最近完成"

    def _normalize_tokens(self, keyword: str) -> list[str]:
        return [token for token in keyword.strip().lower().replace("，", " ").replace(",", " ").split() if token]

    def _score_text_match(self, text: str, tokens: list[str], *, weight: float) -> float:
        normalized = text.strip().lower()
        if not normalized:
            return 0.0
        score = 0.0
        for token in tokens:
            if token in normalized:
                score += weight
        return score

    def get_recipe(self, recipe_id: int) -> RecipeDetailResponse | None:
        lookup = recipe_catalog_service.get_recipe_by_id(recipe_id, include=["recipe", "tags", "ingredients", "steps"])
        if lookup is None or lookup.recipe is None:
            return None
        return RecipeDetailResponse(
            id=lookup.recipe.id,
            name=lookup.recipe.name,
            description=lookup.recipe.description,
            difficulty=lookup.recipe.difficulty,
            estimated_minutes=lookup.recipe.estimated_minutes,
            servings=lookup.recipe.servings,
            tags=[tag_name for tags in (lookup.tags or {}).values() for tag_name in tags],
            image_path=lookup.recipe.image_path,
            ingredients=[
                {
                    "ingredient_name": item.ingredient_name,
                    "amount_text": item.amount_text,
                    "amount_value": item.amount_value,
                    "unit": item.unit,
                    "is_optional": item.is_optional,
                    "purpose": item.purpose,
                }
                for item in (lookup.ingredients or [])
            ],
            steps=[
                {
                    "step_no": item.step_no,
                    "title": item.title,
                    "instruction": item.instruction,
                    "timer_seconds": item.timer_seconds,
                    "notes": item.notes,
                }
                for item in (lookup.steps or [])
            ],
            tips=lookup.recipe.tips,
        )


recipe_service = RecipeService()
