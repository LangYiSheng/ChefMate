from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from app.domain.enums import ConversationStage
from app.domain.models import TagSelections


SuiteName = Literal["stage_capability", "transition_decision", "end_to_end"]


class AttachmentFixtureInput(BaseModel):
    path: str
    name: str | None = None
    mime_type: str | None = None


class ActionInput(BaseModel):
    action_type: str
    payload: dict[str, Any] = Field(default_factory=dict)


class IngredientOverride(BaseModel):
    id: str | None = None
    ingredient_name: str | None = None
    status: str | None = None
    note: str | None = None
    amount_text: str | None = None


class StepOverride(BaseModel):
    id: str | None = None
    step_no: int | None = None
    status: str | None = None
    title: str | None = None
    instruction: str | None = None
    notes: str | None = None
    note: str | None = None


class UserProfileSeed(BaseModel):
    display_name: str = "评测用户"
    cooking_preference_text: str = ""
    tag_selections: TagSelections = Field(default_factory=TagSelections)
    allow_auto_update: bool = True
    auto_start_step_timer: bool = False
    complete_workspace_onboarding: bool = True


class SeedMessage(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str


class TaskSeed(BaseModel):
    stage: Literal["planning", "shopping", "cooking"]
    source_recipe_id: int | str | None = None
    source_recipe_selector: str | None = None
    recipe_snapshot_preset: str | None = None
    recipe_snapshot: dict[str, Any] | None = None
    ingredient_overrides: list[IngredientOverride] = Field(default_factory=list)
    step_overrides: list[StepOverride] = Field(default_factory=list)


class InitialState(BaseModel):
    conversation_stage: ConversationStage = ConversationStage.IDLE
    conversation_title: str | None = None
    conversation_summary: str = ""
    user_profile: UserProfileSeed = Field(default_factory=UserProfileSeed)
    current_task: TaskSeed | None = None
    recent_messages: list[SeedMessage] = Field(default_factory=list)


class ResponseConstraints(BaseModel):
    contains_any: list[str] = Field(default_factory=list)
    contains_all: list[str] = Field(default_factory=list)
    not_contains: list[str] = Field(default_factory=list)


class TaskAssertions(BaseModel):
    current_task_exists: bool | None = None
    current_task_stage: ConversationStage | None = None
    source_recipe_id_exists: bool | None = None
    source_recipe_id: int | None = None
    recipe_name: str | None = None
    ingredient_status: list[IngredientOverride] = Field(default_factory=list)
    step_status: list[StepOverride] = Field(default_factory=list)


class Expectations(BaseModel):
    required_tools: list[str] = Field(default_factory=list)
    forbidden_tools: list[str] = Field(default_factory=list)
    tool_order_constraints: list[list[str]] = Field(default_factory=list)
    expected_final_stage: ConversationStage | None = None
    expected_task_assertions: TaskAssertions | None = None
    expected_response_constraints: ResponseConstraints | None = None
    max_turns: int | None = None


class TurnExpectations(BaseModel):
    required_tools: list[str] = Field(default_factory=list)
    forbidden_tools: list[str] = Field(default_factory=list)
    expected_stage_after_turn: ConversationStage | None = None
    expected_response_constraints: ResponseConstraints | None = None


class TurnInput(BaseModel):
    content: str | None = None
    action: ActionInput | None = None
    attachments: list[AttachmentFixtureInput] = Field(default_factory=list)
    client_card_state: dict[str, Any] | None = None
    expectations: TurnExpectations | None = None


class AgentEvalCase(BaseModel):
    case_id: str
    suite: SuiteName
    title: str
    goal: str
    initial_state: InitialState = Field(default_factory=InitialState)
    turns: list[TurnInput] = Field(default_factory=list)
    expectations: Expectations = Field(default_factory=Expectations)
    tags: list[str] = Field(default_factory=list)
    llm_judge_enabled: bool = True
    skip_reason: str | None = None


class DatasetBundle(BaseModel):
    dataset: str
    suite: SuiteName
    construction_method: str = "手工场景集"
    cases: list[AgentEvalCase] = Field(default_factory=list)

