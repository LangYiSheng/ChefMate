from pydantic import BaseModel, Field


class RecipeIngredientResponse(BaseModel):
    ingredient_name: str
    amount_value: float | None = None
    amount_text: str
    unit: str | None = None
    is_optional: bool = False
    purpose: str | None = None


class RecipeStepResponse(BaseModel):
    step_no: int
    title: str | None = None
    instruction: str
    timer_seconds: int | None = None
    notes: str | None = None


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
