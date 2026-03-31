from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.dependencies import get_current_user_profile
from app.domain.models import UserProfileSnapshot
from app.schemas.recipe import RecipeDetailResponse, RecipeListResponse
from app.services.recipe_service import recipe_service

router = APIRouter()


@router.get("", response_model=RecipeListResponse)
def list_recipes(
    keyword: str | None = Query(default=None),
    tag: str | None = Query(default=None),
    search_fields: list[str] = Query(default=[]),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    profile: UserProfileSnapshot = Depends(get_current_user_profile),
) -> RecipeListResponse:
    try:
        return recipe_service.list_recipes(
            user=profile,
            keyword=keyword,
            tag=tag,
            search_fields=search_fields,
            limit=limit,
            offset=offset,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/{recipe_id}", response_model=RecipeDetailResponse)
def get_recipe(
    recipe_id: int,
    _: UserProfileSnapshot = Depends(get_current_user_profile),
) -> RecipeDetailResponse:
    recipe = recipe_service.get_recipe(recipe_id)
    if recipe is None:
        raise HTTPException(status_code=404, detail="Recipe not found")
    return recipe
