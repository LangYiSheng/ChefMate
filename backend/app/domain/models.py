from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums import (
    AttachmentKind,
    CardActionType,
    CardType,
    ConversationStage,
    IngredientStatus,
    MessageRole,
    StepStatus,
    TaskRecipeSourceType,
)


class TagSelections(BaseModel):
    flavor: list[str] = Field(default_factory=list)
    method: list[str] = Field(default_factory=list)
    scene: list[str] = Field(default_factory=list)
    health: list[str] = Field(default_factory=list)
    time: list[str] = Field(default_factory=list)
    tool: list[str] = Field(default_factory=list)


class UserProfileSnapshot(BaseModel):
    id: int
    username: str
    email: str | None = None
    display_name: str
    allow_auto_update: bool = True
    auto_start_step_timer: bool = False
    cooking_preference_text: str = ""
    tag_selections: TagSelections = Field(default_factory=TagSelections)
    is_first_workspace_visit: bool = True
    has_completed_workspace_onboarding: bool = False
    profile_completed_at: str | None = None


class TaskRecipeIngredient(BaseModel):
    id: str
    ingredient_name: str
    amount_text: str
    amount_value: float | None = None
    unit: str | None = None
    is_optional: bool = False
    purpose: str | None = None
    sort_order: int = 0
    status: IngredientStatus = IngredientStatus.PENDING
    note: str | None = None


class TaskRecipeStep(BaseModel):
    id: str
    step_no: int
    title: str | None = None
    instruction: str
    timer_seconds: int | None = None
    notes: str | None = None
    status: StepStatus = StepStatus.PENDING
    note: str | None = None


class TaskRecipeSnapshot(BaseModel):
    source_type: TaskRecipeSourceType = TaskRecipeSourceType.CATALOG
    source_recipe_id: int | None = None
    name: str
    description: str = ""
    difficulty: str = "简单"
    estimated_minutes: int = 15
    servings: int = 2
    tags: dict[str, list[str]] = Field(default_factory=dict)
    ingredients: list[TaskRecipeIngredient] = Field(default_factory=list)
    steps: list[TaskRecipeStep] = Field(default_factory=list)
    tips: str | None = None


class MessageAttachment(BaseModel):
    id: str
    kind: AttachmentKind
    name: str
    preview_url: str
    file_url: str | None = None


class CardAction(BaseModel):
    id: str
    label: str
    action_type: CardActionType
    payload: dict[str, Any] = Field(default_factory=dict)


class RecipeRecommendationCardItem(BaseModel):
    recipe_id: int
    name: str
    description: str
    tags: list[str] = Field(default_factory=list)
    difficulty: str
    estimated_minutes: int
    servings: int
    actions: list[CardAction] = Field(default_factory=list)


class RecipeSummaryCardRecipe(BaseModel):
    id: int
    name: str
    description: str
    difficulty: str
    estimated_minutes: int
    servings: int
    tags: list[str] = Field(default_factory=list)
    ingredients: list[TaskRecipeIngredient] = Field(default_factory=list)
    steps: list[TaskRecipeStep] = Field(default_factory=list)
    tips: str | None = None


class PantryChecklistItem(BaseModel):
    id: str
    ingredient: str
    amount: str
    status: IngredientStatus
    note: str | None = None
    is_optional: bool = False


class CookingGuideStep(BaseModel):
    id: str
    title: str
    detail: str
    duration: str
    timer_seconds: int | None = None
    notes: str | None = None
    status: StepStatus


class RecipeRecommendationsCard(BaseModel):
    type: CardType = CardType.RECIPE_RECOMMENDATIONS
    title: str
    recipes: list[RecipeRecommendationCardItem] = Field(default_factory=list)


class RecipeDetailCard(BaseModel):
    type: CardType = CardType.RECIPE_DETAIL
    recipe: RecipeSummaryCardRecipe
    actions: list[CardAction] = Field(default_factory=list)


class PantryStatusCard(BaseModel):
    type: CardType = CardType.PANTRY_STATUS
    title: str
    checklist: list[PantryChecklistItem] = Field(default_factory=list)
    actions: list[CardAction] = Field(default_factory=list)


class CookingGuideCard(BaseModel):
    type: CardType = CardType.COOKING_GUIDE
    title: str
    current_step: int
    total_steps: int
    steps: list[CookingGuideStep] = Field(default_factory=list)


MessageCard = (
    RecipeRecommendationsCard
    | RecipeDetailCard
    | PantryStatusCard
    | CookingGuideCard
)


class ConversationMessage(BaseModel):
    id: str
    role: MessageRole
    content: str
    created_at: str
    attachments: list[MessageAttachment] = Field(default_factory=list)
    suggestions: list[str] | None = None
    cards: list[MessageCard] = Field(default_factory=list)

    model_config = ConfigDict(arbitrary_types_allowed=True)


class ConversationSummary(BaseModel):
    id: str
    title: str
    stage: ConversationStage
    current_recipe_name: str | None = None
    suggestions: list[str] = Field(default_factory=list)


class ConversationDetail(ConversationSummary):
    messages: list[ConversationMessage] = Field(default_factory=list)


class SendMessageAction(BaseModel):
    action_type: CardActionType
    payload: dict[str, Any] = Field(default_factory=dict)
