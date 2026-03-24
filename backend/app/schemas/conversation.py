from pydantic import BaseModel

from app.core.semantic_models import ConversationStage, TaskSnapshot, WorkflowCard


class ConversationCreateRequest(BaseModel):
    user_id: str
    title: str | None = None


class ConversationCreateResponse(BaseModel):
    conversation_id: str
    title: str
    stage: ConversationStage


class MessageRequest(BaseModel):
    content: str


class MessageResponse(BaseModel):
    conversation_id: str
    task: TaskSnapshot
    assistant_message: str
    card: WorkflowCard | None = None
