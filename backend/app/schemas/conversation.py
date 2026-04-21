from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from app.domain.enums import AttachmentKind
from app.domain.models import ConversationDetail, ConversationMessage, ConversationSummary, SendMessageAction


class ConversationCreateRequest(BaseModel):
    source: Literal["manual", "recipe"] | None = "manual"
    recipe_id: int | None = None


class ConversationBulkDeleteRequest(BaseModel):
    conversation_ids: list[str] = Field(default_factory=list)


class ConversationBulkDeleteResponse(BaseModel):
    deleted_ids: list[str] = Field(default_factory=list)
    deleted_count: int = 0


class UploadedAttachmentInput(BaseModel):
    kind: AttachmentKind
    file_id: str | None = None
    file_url: str | None = None
    name: str | None = None


class PantryClientCardStateInput(BaseModel):
    ready_ingredient_ids: list[str] = Field(default_factory=list)
    focused_ingredient_id: str | None = None
    flash_mode: bool = False


class CookingGuideClientCardStateInput(BaseModel):
    current_step: int | None = None
    focused_step_id: str | None = None
    flash_mode: bool = False


class ClientCardStateInput(BaseModel):
    pantry_status: PantryClientCardStateInput | None = None
    cooking_guide: CookingGuideClientCardStateInput | None = None


class SendMessageRequest(BaseModel):
    content: str | None = None
    attachments: list[UploadedAttachmentInput] = Field(default_factory=list)
    action: SendMessageAction | None = None
    client_card_state: ClientCardStateInput | None = None


class SendMessageResponse(BaseModel):
    conversation: ConversationSummary
    message: ConversationMessage


class ConversationCreateResponse(BaseModel):
    conversation: ConversationDetail
