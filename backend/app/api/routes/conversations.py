from fastapi import APIRouter

from app.core.semantic_models import ConversationStage, TaskSnapshot
from app.core.task_manager import task_manager
from app.core.workflow import workflow
from app.schemas.conversation import (
    ConversationCreateRequest,
    ConversationCreateResponse,
    MessageRequest,
    MessageResponse,
)

router = APIRouter()


@router.post("", response_model=ConversationCreateResponse)
def create_conversation(payload: ConversationCreateRequest) -> ConversationCreateResponse:
    conversation = task_manager.create_conversation(payload.user_id, payload.title)
    return ConversationCreateResponse(
        conversation_id=conversation["id"],
        title=conversation["title"],
        stage=ConversationStage.GENERAL,
    )


@router.post("/{conversation_id}/messages", response_model=MessageResponse)
def post_message(conversation_id: str, payload: MessageRequest) -> MessageResponse:
    task = task_manager.create_or_resume_task(conversation_id=conversation_id, user_input=payload.content)
    workflow_result = workflow.route(task, payload.content)
    task_manager.update_task_from_result(task.id, workflow_result)
    snapshot: TaskSnapshot = task_manager.get_task_snapshot(task.id)
    return MessageResponse(
        conversation_id=conversation_id,
        task=snapshot,
        assistant_message=workflow_result.user_facing_message,
        card=workflow_result.card,
    )
