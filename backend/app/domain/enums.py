from enum import StrEnum


class ConversationStage(StrEnum):
    IDLE = "idea"
    RECOMMENDING = "planning"
    PREPARING = "shopping"
    COOKING = "cooking"


class TaskStatus(StrEnum):
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class TaskOutcome(StrEnum):
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class MessageRole(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class AttachmentKind(StrEnum):
    IMAGE = "image"


class CardType(StrEnum):
    RECIPE_RECOMMENDATIONS = "recipe-recommendations"
    RECIPE_DETAIL = "recipe-detail"
    PANTRY_STATUS = "pantry-status"
    COOKING_GUIDE = "cooking-guide"


class CardActionType(StrEnum):
    VIEW_RECIPE = "view_recipe"
    TRY_RECIPE = "try_recipe"
    INGREDIENTS_READY = "ingredients_ready"
    OPEN_TIMER = "open_timer"


class TaskRecipeSourceType(StrEnum):
    CATALOG = "catalog"
    GENERATED = "generated"


class IngredientStatus(StrEnum):
    PENDING = "pending"
    READY = "ready"
    SKIPPED = "skipped"


class StepStatus(StrEnum):
    PENDING = "pending"
    CURRENT = "current"
    DONE = "done"
