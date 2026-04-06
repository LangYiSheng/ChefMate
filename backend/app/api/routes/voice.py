from __future__ import annotations

import asyncio
import json
import logging

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, status

from app.api.dependencies import get_current_user_profile
from app.schemas.voice import (
    VoiceSocketEvent,
    VoiceStreamStartRequest,
    VoiceStreamStopRequest,
    VoiceWakeupCheckRequest,
    VoiceWakeupCheckResponse,
)
from app.services.auth_service import auth_service
from app.services.voice_service import voice_service

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/wakeup/check", response_model=VoiceWakeupCheckResponse)
async def check_wakeup(
    payload: VoiceWakeupCheckRequest,
    profile=Depends(get_current_user_profile),
) -> VoiceWakeupCheckResponse:
    try:
        return await voice_service.check_wakeup(
            audio_base64=payload.audio_base64,
            uid=str(profile.id),
            sample_rate=payload.sample_rate,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - integration path
        logger.exception("[voice] wakeup check failed user_id=%s", profile.id)
        raise HTTPException(status_code=502, detail=str(exc) or "语音唤醒检测失败。") from exc


@router.websocket("/stream")
async def voice_stream(websocket: WebSocket):
    await websocket.accept()

    try:
        start_request = VoiceStreamStartRequest.model_validate(await websocket.receive_json())
        profile = auth_service.get_user_profile_by_token(start_request.token)
        if profile is None:
            await _send_socket_event(
                websocket,
                "error",
                {"detail": "登录态已失效，请重新登录。"},
            )
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        async with voice_service.create_stream_session(
            uid=str(profile.id),
            sample_rate=start_request.sample_rate,
            chunk_ms=start_request.chunk_ms,
        ) as session:
            await _send_socket_event(
                websocket,
                "ready",
                {
                    "sample_rate": start_request.sample_rate,
                    "chunk_ms": start_request.chunk_ms,
                },
            )
            await _send_socket_event(
                websocket,
                "status",
                {
                    "text": "语音连接已建立，开始接收音频...",
                },
            )

            stop_event = asyncio.Event()
            relay_error: Exception | None = None

            async def relay_events() -> None:
                nonlocal relay_error
                try:
                    async for event in session.iter_events():
                        await _send_socket_event(
                            websocket,
                            event.event,
                            {
                                "text": event.text,
                                "payload": event.payload,
                            },
                        )
                except Exception as exc:  # pragma: no cover - integration path
                    relay_error = exc
                    stop_event.set()

            relay_task = asyncio.create_task(relay_events())
            client_disconnected = False

            try:
                while not stop_event.is_set():
                    receive_task = asyncio.create_task(websocket.receive())
                    stop_wait_task = asyncio.create_task(stop_event.wait())
                    done, pending = await asyncio.wait(
                        {receive_task, stop_wait_task},
                        return_when=asyncio.FIRST_COMPLETED,
                    )
                    for task in pending:
                        task.cancel()
                    if stop_wait_task in done and stop_event.is_set():
                        break
                    message = await receive_task
                    if message["type"] == "websocket.disconnect":
                        client_disconnected = True
                        stop_event.set()
                        break

                    if message.get("bytes") is not None:
                        await session.send_audio(message["bytes"])
                        continue

                    text_payload = message.get("text")
                    if text_payload is None:
                        continue

                    stop_request = VoiceStreamStopRequest.model_validate(json.loads(text_payload))
                    await _send_socket_event(
                        websocket,
                        "status",
                        {
                            "text": "正在结束录音并生成结果...",
                        },
                    )
                    await session.finish()
                    stop_event.set()
                    logger.info(
                        "[voice] stop stream user_id=%s reason=%s",
                        profile.id,
                        stop_request.reason,
                    )

                if client_disconnected:
                    if not relay_task.done():
                        relay_task.cancel()
                        try:
                            await relay_task
                        except asyncio.CancelledError:
                            pass
                    return

                await relay_task

                if relay_error is not None:
                    raise relay_error
            finally:
                if not relay_task.done():
                    relay_task.cancel()
                    try:
                        await relay_task
                    except asyncio.CancelledError:
                        pass
    except WebSocketDisconnect:
        logger.info("[voice] client disconnected before stream finished")
    except Exception as exc:  # pragma: no cover - integration path
        logger.exception("[voice] stream failed")
        try:
            await _send_socket_event(websocket, "error", {"detail": str(exc) or "语音识别失败。"})
        except Exception:
            pass
        try:
            await websocket.close(code=status.WS_1011_INTERNAL_ERROR)
        except Exception:
            pass


async def _send_socket_event(websocket: WebSocket, event: str, data: dict) -> None:
    payload = VoiceSocketEvent(event=event, data=data)
    await websocket.send_json(payload.model_dump(mode="json"))
