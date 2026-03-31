from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.domain.enums import ConversationStage
from app.domain.models import MessageAttachment, SendMessageAction, TaskRecipeSnapshot, UserProfileSnapshot


@dataclass
class AgentTurnContext:
    user: UserProfileSnapshot
    conversation_id: str
    conversation_title: str
    conversation_stage: ConversationStage
    conversation_summary: str
    current_task_id: str | None
    current_task_stage: ConversationStage | None
    current_task_source_recipe_id: int | None
    current_task_snapshot: TaskRecipeSnapshot | None
    latest_user_content: str
    latest_user_action: SendMessageAction | None
    latest_attachments: list[MessageAttachment] = field(default_factory=list)
    recent_messages: list[dict[str, Any]] = field(default_factory=list)
    recent_finished_tasks: list[dict[str, Any]] = field(default_factory=list)
    tag_catalog: dict[str, list[str]] = field(default_factory=dict)
    response_card: dict[str, Any] | None = None
    response_card_type: str | None = None
    response_recipe_name: str | None = None

    @property
    def active_stage(self) -> ConversationStage:
        if self.current_task_id and self.current_task_stage:
            return self.current_task_stage
        return self.conversation_stage
