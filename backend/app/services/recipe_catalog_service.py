from __future__ import annotations

import difflib
from typing import Any

from pydantic import BaseModel, Field

from app.db.contracts import RecipeIngredientRecord, RecipeRecord, RecipeStepRecord
from app.repositories.recipe_repository import recipe_repository
from app.schemas.recipe import (
    RecipeIngredientResponse,
    RecipeLookupResponse,
    RecipeMetaResponse,
    RecipeStepResponse,
)


class RecipeCatalogEntry(BaseModel):
    id: int
    name: str
    aliases: list[str] = Field(default_factory=list)
    image_path: str | None = None
    description: str | None = None
    difficulty: str
    estimated_minutes: int
    servings: int
    tips: str | None = None
    tags: dict[str, list[str]] = Field(default_factory=dict)
    ingredients: list[RecipeIngredientResponse] = Field(default_factory=list)
    steps: list[RecipeStepResponse] = Field(default_factory=list)


class RecipeCatalogService:
    DEFAULT_RECIPE_INCLUDE = ("recipe", "tags", "ingredients", "steps")
    TAG_CATEGORY_LABELS = {
        "flavor": "口味",
        "method": "做法",
        "scene": "场景",
        "health": "健康",
        "time": "时间",
        "tool": "工具",
        "difficulty": "难度",
    }
    TAG_ALIASES = {
        "health": {
            "减脂": "减脂友好",
            "清淡": "清淡饮食",
        },
        "time": {
            "10-20分钟": "10到20分钟",
            "10 到 20 分钟": "10到20分钟",
            "20-30分钟": "20到30分钟",
        },
    }

    INGREDIENT_ALIASES = {
        "西红柿": "番茄",
        "番茄": "番茄",
        "蛋": "鸡蛋",
        "鸡蛋": "鸡蛋",
        "鸡翅": "鸡翅中",
        "鸡翅中": "鸡翅中",
        "米饭": "米饭",
        "剩饭": "米饭",
    }

    TEXT_ALIASES = {
        "西红柿": "番茄",
        "鸡蛋": "蛋",
    }

    def list_entries(self) -> list[RecipeCatalogEntry]:
        recipes = recipe_repository.list_published_recipes()
        recipe_ids = [item.id for item in recipes]
        ingredients_map = recipe_repository.get_ingredients_by_recipe_ids(recipe_ids)
        steps_map = recipe_repository.get_steps_by_recipe_ids(recipe_ids)
        tags_map = recipe_repository.get_tags_by_recipe_ids(recipe_ids)
        return [
            self._build_entry(
                recipe=recipe,
                ingredients=ingredients_map.get(recipe.id, []),
                steps=steps_map.get(recipe.id, []),
                tags=tags_map.get(recipe.id, {}),
            )
            for recipe in recipes
        ]

    def get_tag_taxonomy(self) -> dict[str, list[str]]:
        return recipe_repository.get_tag_taxonomy()

    def validate_tag_filters(
        self,
        filters: dict[str, list[str]],
        *,
        categories: list[str] | tuple[str, ...] | set[str] | None = None,
        allow_alias: bool = False,
    ) -> dict[str, list[str]]:
        taxonomy = self.get_tag_taxonomy()
        target_categories = list(categories or filters.keys())
        normalized: dict[str, list[str]] = {}
        invalid: dict[str, list[str]] = {}

        for category in target_categories:
            values = filters.get(category, [])
            if not values:
                continue
            allowed_values = taxonomy.get(category, [])
            if not allowed_values:
                invalid[category] = [value.strip() for value in values if isinstance(value, str) and value.strip()]
                continue

            alias_map = self.TAG_ALIASES.get(category, {}) if allow_alias else {}
            seen: set[str] = set()
            resolved_values: list[str] = []
            invalid_values: list[str] = []

            for raw_value in values:
                if not isinstance(raw_value, str):
                    continue
                value = raw_value.strip()
                if not value:
                    continue
                candidate = alias_map.get(value, value)
                if candidate in allowed_values:
                    if candidate not in seen:
                        resolved_values.append(candidate)
                        seen.add(candidate)
                    continue
                invalid_values.append(value)

            if resolved_values:
                normalized[category] = resolved_values
            if invalid_values:
                invalid[category] = invalid_values

        if invalid:
            raise ValueError(
                self._build_invalid_tag_message(
                    invalid=invalid,
                    taxonomy=taxonomy,
                    categories=target_categories,
                )
            )
        return normalized

    def get_recipe_by_id(self, recipe_id: int, include: list[str] | None = None) -> RecipeLookupResponse | None:
        resolved_include = self._resolve_recipe_include(include)
        recipe = recipe_repository.get_recipe(recipe_id)
        if recipe is None:
            return None

        ingredients = (
            recipe_repository.get_ingredients_by_recipe_ids([recipe_id]).get(recipe_id, [])
            if "ingredients" in resolved_include
            else []
        )
        steps = (
            recipe_repository.get_steps_by_recipe_ids([recipe_id]).get(recipe_id, [])
            if "steps" in resolved_include
            else []
        )
        tags = (
            recipe_repository.get_tags_by_recipe_ids([recipe_id]).get(recipe_id, {})
            if "tags" in resolved_include
            else {}
        )
        entry = self._build_entry(recipe=recipe, ingredients=ingredients, steps=steps, tags=tags)
        return RecipeLookupResponse(
            id=entry.id,
            recipe=(
                RecipeMetaResponse(
                    id=entry.id,
                    name=entry.name,
                    aliases=entry.aliases,
                    image_path=entry.image_path,
                    description=entry.description,
                    difficulty=entry.difficulty,
                    estimated_minutes=entry.estimated_minutes,
                    servings=entry.servings,
                    tips=entry.tips,
                )
                if "recipe" in resolved_include
                else None
            ),
            tags=entry.tags if "tags" in resolved_include else None,
            ingredients=entry.ingredients if "ingredients" in resolved_include else None,
            steps=entry.steps if "steps" in resolved_include else None,
        )

    def search_recipes_by_name(self, query: str, exact: bool = False, limit: int = 10) -> dict[str, Any]:
        normalized_query = self._normalize_text(query)
        db_candidates = recipe_repository.search_published_recipes_by_name(query_text=query, exact=exact, limit=max(limit * 3, 20))
        if db_candidates:
            return {
                "query": query,
                "match_mode": "exact" if exact else "fuzzy",
                "candidates": [
                    {
                        "id": recipe.id,
                        "name": recipe.name,
                        "description": recipe.description,
                        "difficulty": recipe.difficulty,
                        "estimated_minutes": recipe.estimated_minutes,
                        "score": 1.0 if exact else 0.96,
                    }
                    for recipe in db_candidates[:limit]
                ],
            }

        entries = self.list_entries()
        candidates: list[dict[str, Any]] = []

        for entry in entries:
            names = [entry.name, *entry.aliases]
            score = self._score_name_query(normalized_query, names, exact=exact)
            if score <= 0:
                continue

            candidates.append(
                {
                    "id": entry.id,
                    "name": entry.name,
                    "description": entry.description,
                    "difficulty": entry.difficulty,
                    "estimated_minutes": entry.estimated_minutes,
                    "score": round(score, 4),
                }
            )

        candidates.sort(key=lambda item: (-item["score"], item["estimated_minutes"], item["id"]))
        return {
            "query": query,
            "match_mode": "exact" if exact else "fuzzy",
            "candidates": candidates[:limit],
        }

    def filter_recipes_by_tags(
        self,
        *,
        flavor: list[str] | None = None,
        method: list[str] | None = None,
        scene: list[str] | None = None,
        health: list[str] | None = None,
        time: list[str] | None = None,
        tool: list[str] | None = None,
        difficulty: list[str] | None = None,
        match_mode: str = "fuzzy",
        limit: int = 10,
    ) -> dict[str, Any]:
        filters = {
            "flavor": flavor or [],
            "method": method or [],
            "scene": scene or [],
            "health": health or [],
            "time": time or [],
            "tool": tool or [],
            "difficulty": difficulty or [],
        }
        resolved = {
            category: self._resolve_requested_values(category, values, fuzzy=(match_mode != "exact"))
            for category, values in filters.items()
            if values
        }
        entries = self.list_entries()

        candidates: list[dict[str, Any]] = []
        for entry in entries:
            if match_mode == "exact":
                if not self._matches_exact(entry, resolved):
                    continue
                score = 1.0
                matched_tags = {category: values for category, values in resolved.items()}
                missing_tags: dict[str, list[str]] = {}
            else:
                score, matched_tags, missing_tags = self._score_tag_filter(entry, resolved)
                if score <= 0:
                    continue

            candidates.append(
                {
                    "id": entry.id,
                    "name": entry.name,
                    "description": entry.description,
                    "difficulty": entry.difficulty,
                    "estimated_minutes": entry.estimated_minutes,
                    "matched_tags": matched_tags,
                    "missing_tags": missing_tags,
                    "score": round(score, 4),
                }
            )

        candidates.sort(key=lambda item: (-item["score"], item["estimated_minutes"], item["id"]))
        return {
            "filters": resolved,
            "match_mode": match_mode,
            "candidates": candidates[:limit],
        }

    def find_recipes_by_ingredients(
        self,
        ingredients: list[str],
        *,
        exact_only: bool = False,
        limit: int = 10,
    ) -> dict[str, Any]:
        normalized_inputs = {self._normalize_ingredient_name(item) for item in ingredients if item.strip()}
        entries = self.list_entries()
        candidates: list[dict[str, Any]] = []

        for entry in entries:
            required = [
                self._normalize_ingredient_name(item.ingredient_name)
                for item in entry.ingredients
                if not item.is_optional
            ]
            optional = [
                self._normalize_ingredient_name(item.ingredient_name)
                for item in entry.ingredients
                if item.is_optional
            ]

            required_matches = sorted({name for name in required if name in normalized_inputs})
            optional_matches = sorted({name for name in optional if name in normalized_inputs})
            missing_required = sorted({name for name in required if name not in normalized_inputs})

            required_ratio = len(required_matches) / len(required) if required else 1.0
            optional_ratio = len(optional_matches) / len(optional) if optional else 1.0
            exact_makeable = not missing_required
            if exact_only and not exact_makeable:
                continue

            score = required_ratio * 0.85 + optional_ratio * 0.15
            if not exact_makeable:
                score -= min(len(missing_required) * 0.08, 0.32)
            if score <= 0:
                continue

            candidates.append(
                {
                    "id": entry.id,
                    "name": entry.name,
                    "description": entry.description,
                    "difficulty": entry.difficulty,
                    "estimated_minutes": entry.estimated_minutes,
                    "score": round(max(score, 0.0), 4),
                    "exact_makeable": exact_makeable,
                    "matched_ingredients": required_matches + optional_matches,
                    "missing_required_ingredients": missing_required,
                }
            )

        candidates.sort(
            key=lambda item: (
                not item["exact_makeable"],
                -item["score"],
                len(item["missing_required_ingredients"]),
                item["estimated_minutes"],
            )
        )
        return {
            "ingredients": sorted(normalized_inputs),
            "exact_only": exact_only,
            "candidates": candidates[:limit],
        }

    def search_recipes_by_step_text(self, query: str, limit: int = 10) -> dict[str, Any]:
        normalized_query = self._normalize_text(query)
        if not normalized_query:
            return {"query": query, "match_mode": "step_text", "candidates": []}

        candidates: list[dict[str, Any]] = []
        for entry in self.list_entries():
            best_score = 0.0
            matched_steps: list[dict[str, Any]] = []

            for step in entry.steps:
                step_text = " ".join(
                    item
                    for item in [step.title or "", step.instruction or "", step.notes or ""]
                    if item
                )
                normalized_step_text = self._normalize_text(step_text)
                if not normalized_step_text:
                    continue
                if normalized_query in normalized_step_text:
                    score = 0.95
                else:
                    score = difflib.SequenceMatcher(a=normalized_query, b=normalized_step_text).ratio()
                if score < 0.35:
                    continue
                best_score = max(best_score, score)
                matched_steps.append(
                    {
                        "step_no": step.step_no,
                        "title": step.title,
                        "score": round(score, 4),
                    }
                )

            if best_score <= 0:
                continue

            candidates.append(
                {
                    "id": entry.id,
                    "name": entry.name,
                    "description": entry.description,
                    "difficulty": entry.difficulty,
                    "estimated_minutes": entry.estimated_minutes,
                    "score": round(best_score, 4),
                    "matched_steps": sorted(matched_steps, key=lambda item: (-item["score"], item["step_no"]))[:3],
                }
            )

        candidates.sort(key=lambda item: (-item["score"], item["estimated_minutes"], item["id"]))
        return {
            "query": query,
            "match_mode": "step_text",
            "candidates": candidates[:limit],
        }

    def extract_ingredient_terms_from_text(self, text: str, *, limit: int = 8) -> list[str]:
        normalized_text = self._normalize_text(text)
        if not normalized_text:
            return []

        known_terms: set[str] = set(self.INGREDIENT_ALIASES)
        for entry in self.list_entries():
            known_terms.update(
                item.ingredient_name.strip()
                for item in entry.ingredients
                if item.ingredient_name and item.ingredient_name.strip()
            )

        matches: list[tuple[int, int, str]] = []
        seen: set[str] = set()
        for raw_term in known_terms:
            canonical = self.INGREDIENT_ALIASES.get(raw_term, raw_term).strip()
            normalized_term = self._normalize_ingredient_name(raw_term)
            if not canonical or not normalized_term:
                continue
            index = normalized_text.find(normalized_term)
            if index < 0 or canonical in seen:
                continue
            matches.append((index, -len(normalized_term), canonical))
            seen.add(canonical)

        matches.sort()
        return [item[2] for item in matches[:limit]]

    def infer_tag_filters_from_text(self, user_input: str) -> dict[str, list[str]]:
        normalized = self._normalize_text(user_input)
        taxonomy = recipe_repository.get_tag_taxonomy()
        inferred: dict[str, list[str]] = {}
        for category, values in taxonomy.items():
            if category == "difficulty":
                continue
            matched = [value for value in values if self._normalize_text(value) in normalized]
            if matched:
                inferred[category] = matched

        for difficulty in taxonomy.get("difficulty", []):
            if self._normalize_text(difficulty) in normalized:
                inferred["difficulty"] = [difficulty]
                break
        return inferred

    def default_recommendations(self, limit: int = 10) -> dict[str, Any]:
        candidates = sorted(self.list_entries(), key=lambda item: (item.estimated_minutes, item.id))
        return {
            "query": None,
            "candidates": [
                {
                    "id": entry.id,
                    "name": entry.name,
                    "description": entry.description,
                    "difficulty": entry.difficulty,
                    "estimated_minutes": entry.estimated_minutes,
                    "score": round(max(0.3, 1 - entry.estimated_minutes / 60), 4),
                }
                for entry in candidates[:limit]
            ],
        }

    def _build_entry(
        self,
        *,
        recipe: RecipeRecord,
        ingredients: list[RecipeIngredientRecord],
        steps: list[RecipeStepRecord],
        tags: dict[str, list[str]],
    ) -> RecipeCatalogEntry:
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
            ingredients=[
                RecipeIngredientResponse(
                    ingredient_name=item.ingredient_name,
                    amount_value=float(item.amount_value) if item.amount_value is not None else None,
                    amount_text=item.amount_text,
                    unit=item.unit,
                    is_optional=item.is_optional,
                    purpose=item.purpose,
                )
                for item in ingredients
            ],
            steps=[
                RecipeStepResponse(
                    step_no=item.step_no,
                    title=item.title,
                    instruction=item.instruction,
                    timer_seconds=item.timer_seconds,
                    notes=item.notes,
                )
                for item in steps
            ],
        )

    def _resolve_requested_values(self, category: str, values: list[str], *, fuzzy: bool) -> list[str]:
        category_values = recipe_repository.get_tag_taxonomy().get(category, [])
        resolved: list[str] = []
        for value in values:
            canonical = self.TAG_ALIASES.get(category, {}).get(value, value)
            if canonical in category_values:
                if canonical not in resolved:
                    resolved.append(canonical)
                continue
            if not fuzzy:
                continue

            normalized_target = self._normalize_text(canonical)
            best_match = None
            best_score = 0.0
            for candidate in category_values:
                candidate_normalized = self._normalize_text(candidate)
                if normalized_target in candidate_normalized or candidate_normalized in normalized_target:
                    score = 0.95
                else:
                    score = difflib.SequenceMatcher(a=normalized_target, b=candidate_normalized).ratio()
                if score > best_score:
                    best_score = score
                    best_match = candidate
            if best_match and best_score >= 0.55 and best_match not in resolved:
                resolved.append(best_match)
        return resolved

    def _matches_exact(self, entry: RecipeCatalogEntry, resolved: dict[str, list[str]]) -> bool:
        for category, values in resolved.items():
            if category == "difficulty":
                if entry.difficulty not in values:
                    return False
                continue
            entry_values = set(entry.tags.get(category, []))
            if not set(values).issubset(entry_values):
                return False
        return True

    def _score_tag_filter(
        self,
        entry: RecipeCatalogEntry,
        resolved: dict[str, list[str]],
    ) -> tuple[float, dict[str, list[str]], dict[str, list[str]]]:
        weights = {
            "flavor": 2.0,
            "method": 1.2,
            "scene": 1.5,
            "health": 1.7,
            "time": 1.5,
            "tool": 1.4,
            "difficulty": 1.0,
        }
        score = 0.0
        total_weight = 0.0
        matched_tags: dict[str, list[str]] = {}
        missing_tags: dict[str, list[str]] = {}

        for category, values in resolved.items():
            weight = weights.get(category, 1.0)
            total_weight += weight
            if category == "difficulty":
                matched = values if entry.difficulty in values else []
            else:
                matched = [value for value in values if value in entry.tags.get(category, [])]

            missing = [value for value in values if value not in matched]
            if matched:
                matched_tags[category] = matched
            if missing:
                missing_tags[category] = missing
            score += weight * (len(matched) / len(values))

        if total_weight == 0:
            return 0.0, {}, {}
        normalized_score = score / total_weight
        return normalized_score, matched_tags, missing_tags

    def _score_name_query(self, normalized_query: str, names: list[str], *, exact: bool) -> float:
        best_score = 0.0
        for raw_name in names:
            candidate = self._normalize_text(raw_name)
            if exact:
                if candidate == normalized_query:
                    return 1.0
                continue
            if candidate == normalized_query:
                score = 1.0
            elif normalized_query in candidate or candidate in normalized_query:
                score = 0.93
            else:
                score = difflib.SequenceMatcher(a=normalized_query, b=candidate).ratio()
            best_score = max(best_score, score)
        return best_score if best_score >= 0.55 else 0.0

    def _normalize_text(self, value: str) -> str:
        normalized = (
            value.strip()
            .lower()
            .replace(" ", "")
            .replace("　", "")
            .replace("-", "")
            .replace("_", "")
        )
        for source, target in self.TEXT_ALIASES.items():
            normalized = normalized.replace(source, target)
        return normalized

    def _normalize_ingredient_name(self, value: str) -> str:
        canonical = self.INGREDIENT_ALIASES.get(value.strip(), value.strip())
        return self._normalize_text(canonical)

    def _resolve_recipe_include(self, include: list[str] | None) -> set[str]:
        if not include:
            return set(self.DEFAULT_RECIPE_INCLUDE)

        resolved: set[str] = set()
        alias_map = {
            "all": set(self.DEFAULT_RECIPE_INCLUDE),
            "detail": {"recipe"},
            "details": {"recipe"},
            "recipe": {"recipe"},
            "tags": {"tags"},
            "ingredients": {"ingredients"},
            "steps": {"steps"},
        }
        for item in include:
            key = self._normalize_text(item)
            resolved.update(alias_map.get(key, set()))

        return resolved or set(self.DEFAULT_RECIPE_INCLUDE)

    def _build_invalid_tag_message(
        self,
        *,
        invalid: dict[str, list[str]],
        taxonomy: dict[str, list[str]],
        categories: list[str],
    ) -> str:
        ordered_categories = [category for category in self.TAG_CATEGORY_LABELS if category in categories]
        invalid_text = "；".join(
            f"{self.TAG_CATEGORY_LABELS.get(category, category)}：{'、'.join(values)}"
            for category, values in invalid.items()
            if values
        )
        available_text = "；".join(
            f"{self.TAG_CATEGORY_LABELS.get(category, category)}可选：{'、'.join(taxonomy.get(category, []))}"
            for category in ordered_categories
            if taxonomy.get(category)
        )
        return f"输入了无效的标签。错误项：{invalid_text}。可选的标签有：{available_text}"


recipe_catalog_service = RecipeCatalogService()
