from fastapi import APIRouter, HTTPException, Query

from app.schemas.recipe import RecipeLookupResponse
from app.services.recipe_service import recipe_service

router = APIRouter()


@router.get("/{recipe_id}", response_model=RecipeLookupResponse)
def get_recipe(
    recipe_id: int,
    include: list[str] = Query(default=["recipe", "tags", "ingredients", "steps"]),
) -> RecipeLookupResponse:
    recipe = recipe_service.get_recipe(recipe_id, include=include)
    if recipe is None:
        raise HTTPException(status_code=404, detail="Recipe not found")
    return recipe
