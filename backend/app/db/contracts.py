from pydantic import BaseModel


class RecipeRecord(BaseModel):
    id: int
    name: str
    image_path: str | None = None
    description: str | None = None
    difficulty: str
    estimated_minutes: int
    servings: int
    tips: str | None = None
    status: str


class RecipeIngredientRecord(BaseModel):
    id: int
    recipe_id: int
    ingredient_name: str
    amount_value: float | None = None
    amount_text: str
    unit: str | None = None
    is_optional: bool = False
    purpose: str | None = None
    sort_order: int = 0


class RecipeStepRecord(BaseModel):
    id: int
    recipe_id: int
    step_no: int
    title: str | None = None
    instruction: str
    timer_seconds: int | None = None
    notes: str | None = None


class RecipeTagCategoryRecord(BaseModel):
    id: int
    category_code: str
    category_name: str
    sort_order: int = 0


class RecipeTagRecord(BaseModel):
    id: int
    category_id: int
    bit_position: int
    tag_code: str
    tag_name: str
    is_enabled: bool = True
    sort_order: int = 0


class RecipeTagMapRecord(BaseModel):
    recipe_id: int
    tag_id: int
