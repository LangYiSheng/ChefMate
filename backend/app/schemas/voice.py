from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class VoiceWakeupCheckRequest(BaseModel):
    audio_base64: str
    sample_rate: int = Field(default=16000, ge=8000, le=48000)
    format: Literal["pcm_s16le"] = "pcm_s16le"


class VoiceWakeupCheckResponse(BaseModel):
    text: str = ""
    matched: bool = False
    matched_keyword: str | None = None
    remainder_text: str = ""


class VoiceStreamStartRequest(BaseModel):
    type: Literal["start"]
    token: str
    mode: Literal["dictation"] = "dictation"
    sample_rate: int = Field(default=16000, ge=8000, le=48000)
    chunk_ms: int = Field(default=200, ge=50, le=2000)


class VoiceStreamStopRequest(BaseModel):
    type: Literal["stop"]
    reason: Literal["manual_stop", "silence_timeout"] = "manual_stop"


class VoiceSocketEvent(BaseModel):
    event: Literal["ready", "status", "partial", "final", "error"]
    data: dict[str, Any] = Field(default_factory=dict)
