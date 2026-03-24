from pydantic import BaseModel, Field


class IngredientDetectionItem(BaseModel):
    name: str


class IngredientDetectionResponse(BaseModel):
    backend: str
    model: str
    ingredients: list[IngredientDetectionItem] = Field(default_factory=list)
    raw_text: str | None = None
