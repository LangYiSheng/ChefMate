from __future__ import annotations

import json
import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from app.api.dependencies import get_current_user_profile
from app.domain.models import ConversationSummary
from app.domain.models import UserProfileSnapshot
from app.schemas.conversation import (
    ConversationCreateRequest,
    ConversationCreateResponse,
    SendMessageRequest,
    SendMessageResponse,
)
from app.services.conversation_service import conversation_service

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("", response_model=list[ConversationSummary])
def list_conversations(profile: UserProfileSnapshot = Depends(get_current_user_profile)):
    return conversation_service.list_conversations(profile)


@router.get("/{conversation_id}")
def get_conversation(
    conversation_id: str,
    profile: UserProfileSnapshot = Depends(get_current_user_profile),
):
    try:
        return conversation_service.get_conversation_detail(user=profile, conversation_id=conversation_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("", response_model=ConversationCreateResponse)
def create_conversation(
    payload: ConversationCreateRequest,
    profile: UserProfileSnapshot = Depends(get_current_user_profile),
) -> ConversationCreateResponse:
    try:
        return conversation_service.create_conversation(user=profile, payload=payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{conversation_id}/messages", response_model=SendMessageResponse)
async def send_message(
    conversation_id: str,
    payload: SendMessageRequest,
    profile: UserProfileSnapshot = Depends(get_current_user_profile),
) -> SendMessageResponse:
    try:
        return await conversation_service.send_message(
            user=profile,
            conversation_id=conversation_id,
            payload=payload,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{conversation_id}/messages/stream")
async def stream_message(
    conversation_id: str,
    payload: SendMessageRequest,
    profile: UserProfileSnapshot = Depends(get_current_user_profile),
):
    async def event_stream():
        try:
            async for event in conversation_service.stream_message(
                user=profile,
                conversation_id=conversation_id,
                payload=payload,
            ):
                yield f"event: {event['event']}\n"
                yield "data: " + json.dumps(event["data"], ensure_ascii=False) + "\n\n"
        except ValueError as exc:
            yield "event: error\n"
            yield "data: " + json.dumps({"detail": str(exc)}, ensure_ascii=False) + "\n\n"
        except Exception as exc:
            logger.exception("[api] stream_message failed conversation=%s user_id=%s", conversation_id, profile.id)
            yield "event: error\n"
            yield "data: " + json.dumps({"detail": str(exc) or "后端处理失败，请查看日志。"}, ensure_ascii=False) + "\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
