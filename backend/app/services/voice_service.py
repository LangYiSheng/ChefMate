from __future__ import annotations

import base64
import logging
import re

from app.config import settings
from app.infra.voice_volcengine import VolcengineAsrClient
from app.schemas.voice import VoiceWakeupCheckResponse

logger = logging.getLogger(__name__)

WAKE_WORD_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("小厨小厨", re.compile(r"小厨[\s,，。.!！？?、；;：:“”\"'‘’()（）\-]*小厨")),
    ("小厨", re.compile(r"小厨")),
)
TRIM_CHARS = " \t\r\n,，。.!！？?、；;：:\"'‘’()（）-"


class VoiceService:
    def __init__(self) -> None:
        self._client = VolcengineAsrClient(
            url=settings.voice_volcengine_ws_url.strip(),
            app_key=settings.voice_volcengine_app_key.strip(),
            access_key=settings.voice_volcengine_access_key.strip(),
            resource_id=settings.voice_volcengine_resource_id.strip(),
            sample_rate=settings.voice_sample_rate_hz,
            chunk_ms=settings.voice_chunk_ms,
        )

    def create_stream_session(self, *, uid: str, sample_rate: int | None = None, chunk_ms: int | None = None):
        return self._client.create_session(uid=uid, sample_rate=sample_rate, chunk_ms=chunk_ms)

    async def check_wakeup(self, *, audio_base64: str, uid: str, sample_rate: int) -> VoiceWakeupCheckResponse:
        pcm_audio = self._decode_audio(audio_base64)
        transcript = await self.transcribe_short_clip(pcm_audio=pcm_audio, uid=uid, sample_rate=sample_rate)
        matched_keyword, remainder_text = self._match_wake_word(transcript)
        return VoiceWakeupCheckResponse(
            text=transcript,
            matched=matched_keyword is not None,
            matched_keyword=matched_keyword,
            remainder_text=remainder_text,
        )

    async def transcribe_short_clip(self, *, pcm_audio: bytes, uid: str, sample_rate: int) -> str:
        final_text = ""
        async with self._client.create_session(uid=uid, sample_rate=sample_rate) as session:
            await session.finish(last_chunk=pcm_audio)
            async for event in session.iter_events():
                if event.text:
                    final_text = event.text.strip()
        return final_text

    def _decode_audio(self, audio_base64: str) -> bytes:
        try:
            return base64.b64decode(audio_base64.encode("utf-8"), validate=True)
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("[voice] invalid audio payload: %s", exc)
            raise ValueError("音频数据格式不正确。") from exc

    def _match_wake_word(self, transcript: str) -> tuple[str | None, str]:
        text = transcript.strip()
        if not text:
            return None, ""
        for keyword, pattern in WAKE_WORD_PATTERNS:
            match = pattern.search(text)
            if match:
                remainder = f"{text[: match.start()]} {text[match.end() :]}".strip(TRIM_CHARS)
                return keyword, remainder
        normalized = re.sub(r"[\s,，。.!！？?、；;：:\"'‘’()（）\-]+", "", text)
        for keyword, _ in WAKE_WORD_PATTERNS:
            if keyword in normalized:
                remainder = normalized.replace(keyword, "", 1).strip()
                return keyword, remainder
        return None, ""


voice_service = VoiceService()
