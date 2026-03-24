from __future__ import annotations

from app.services.recipe_catalog_service import recipe_catalog_service


class RecommendationSkill:
    name = "recommendation"

    def search_recipes_by_name(self, query: str, *, exact: bool = False, limit: int = 10) -> dict:
        return recipe_catalog_service.search_recipes_by_name(query=query, exact=exact, limit=limit)

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
    ) -> dict:
        return recipe_catalog_service.filter_recipes_by_tags(
            flavor=flavor,
            method=method,
            scene=scene,
            health=health,
            time=time,
            tool=tool,
            difficulty=difficulty,
            match_mode=match_mode,
            limit=limit,
        )

    def find_recipes_by_ingredients(
        self,
        ingredients: list[str],
        *,
        exact_only: bool = False,
        limit: int = 10,
    ) -> dict:
        return recipe_catalog_service.find_recipes_by_ingredients(
            ingredients=ingredients,
            exact_only=exact_only,
            limit=limit,
        )

    def get_recipe_by_id(self, recipe_id: int, include: list[str] | None = None):
        return recipe_catalog_service.get_recipe_by_id(recipe_id, include=include)

    def recommend_from_query(self, user_input: str) -> dict:
        inferred_filters = recipe_catalog_service.infer_tag_filters_from_text(user_input)
        name_search = self.search_recipes_by_name(user_input, exact=False, limit=5)
        if name_search["candidates"]:
            return {
                "query": user_input,
                "route": "name_search",
                "candidates": name_search["candidates"],
            }

        if inferred_filters:
            filtered = self.filter_recipes_by_tags(match_mode="fuzzy", limit=5, **inferred_filters)
            return {
                "query": user_input,
                "route": "tag_filter",
                "filters": filtered["filters"],
                "candidates": filtered["candidates"],
            }

        default_result = recipe_catalog_service.default_recommendations(limit=5)
        return {
            "query": user_input,
            "route": "default",
            "candidates": default_result["candidates"],
        }

    def recommend_from_ingredients(self, ingredients: list[str]) -> dict:
        result = self.find_recipes_by_ingredients(ingredients, exact_only=False, limit=5)
        return {
            "ingredients": ingredients,
            "route": "ingredient_search",
            "candidates": result["candidates"],
        }


recommendation_skill = RecommendationSkill()
