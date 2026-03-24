from app.schemas.recipe import RecipeLookupResponse
from app.services.recipe_catalog_service import recipe_catalog_service


class RecipeService:
    def get_recipe(self, recipe_id: int, include: list[str] | None = None) -> RecipeLookupResponse | None:
        return recipe_catalog_service.get_recipe_by_id(recipe_id, include=include)


recipe_service = RecipeService()
