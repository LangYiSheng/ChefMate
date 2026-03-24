from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class ConversationStage(StrEnum):
    GENERAL = "GENERAL"
    RECOMMEND = "RECOMMEND"
    PREPARATION = "PREPARATION"
    COOKING = "COOKING"
    SUSPENDED = "SUSPENDED"
    COMPLETED = "COMPLETED"


class TaskStatus(StrEnum):
    RUNNING = "RUNNING"
    SUSPENDED = "SUSPENDED"
    COMPLETED = "COMPLETED"


class SemanticQuery(BaseModel):
    raw_text: str
    target_recipe_name: str | None = None
    available_ingredients: list[str] = Field(default_factory=list)
    health_goal: str | None = None
    max_cook_time: int | None = None
    available_tools: list[str] = Field(default_factory=list)


class WorkflowCard(BaseModel):
    card_type: str
    payload: dict[str, Any]


class WorkflowResult(BaseModel):
    next_stage: ConversationStage
    status: TaskStatus = TaskStatus.RUNNING
    semantic_query: SemanticQuery
    user_facing_message: str
    card: WorkflowCard | None = None


class TaskSnapshot(BaseModel):
    id: str
    conversation_id: str
    stage: ConversationStage
    status: TaskStatus
    current_node: str
    semantic_query: SemanticQuery
