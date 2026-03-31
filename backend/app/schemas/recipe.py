from __future__ import annotations

from pydantic import BaseModel, Field


class RecipeIngredientResponse(BaseModel):
    id: int | None = None
    ingredient_name: str
    amount_text: str
    amount_value: float | None = None
    unit: str | None = None
    is_optional: bool = False
    purpose: str | None = None
    sort_order: int = 0


class RecipeStepResponse(BaseModel):
    id: int | None = None
    step_no: int
    title: str | None = None
    instruction: str
    timer_seconds: int | None = None
    notes: str | None = None


class RecipeSummaryResponse(BaseModel):
    id: int
    name: str
    description: str | None = None
    difficulty: str
    estimated_minutes: int
    servings: int
    tags: list[str] = Field(default_factory=list)
    image_path: str | None = None
    recent_activity: str | None = None


class RecipeDetailResponse(RecipeSummaryResponse):
    ingredients: list[RecipeIngredientResponse] = Field(default_factory=list)
    steps: list[RecipeStepResponse] = Field(default_factory=list)
    tips: str | None = None


class RecipeMetaResponse(BaseModel):
    id: int
    name: str
    aliases: list[str] = Field(default_factory=list)
    image_path: str | None = None
    description: str | None = None
    difficulty: str
    estimated_minutes: int
    servings: int
    tips: str | None = None


class RecipeLookupResponse(BaseModel):
    id: int
    recipe: RecipeMetaResponse | None = None
    tags: dict[str, list[str]] | None = None
    ingredients: list[RecipeIngredientResponse] | None = None
    steps: list[RecipeStepResponse] | None = None


class RecipeListResponse(BaseModel):
    items: list[RecipeSummaryResponse] = Field(default_factory=list)
    recent_items: list[RecipeSummaryResponse] = Field(default_factory=list)
    total: int
    limit: int
    offset: int
