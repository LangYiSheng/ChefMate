from __future__ import annotations

import gzip
import json
import struct
import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any

import aiohttp
from aiohttp.client_exceptions import WSServerHandshakeError


class VolcengineAsrError(RuntimeError):
    pass


class ProtocolVersion:
    V1 = 0b0001


class MessageType:
    CLIENT_FULL_REQUEST = 0b0001
    CLIENT_AUDIO_ONLY_REQUEST = 0b0010
    SERVER_FULL_RESPONSE = 0b1001
    SERVER_ERROR_RESPONSE = 0b1111


class MessageTypeSpecificFlags:
    POS_SEQUENCE = 0b0001
    NEG_WITH_SEQUENCE = 0b0011


class SerializationType:
    JSON = 0b0001


class CompressionType:
    GZIP = 0b0001


def gzip_compress(data: bytes) -> bytes:
    return gzip.compress(data)


def gzip_decompress(data: bytes) -> bytes:
    return gzip.decompress(data)


def build_wav_header(
    data_length: int | None,
    *,
    sample_rate: int,
    channels: int = 1,
    bits: int = 16,
) -> bytes:
    normalized_length = 0xFFFFFFFF if data_length is None else max(0, data_length)
    byte_rate = sample_rate * channels * bits // 8
    block_align = channels * bits // 8
    chunk_size = 36 + normalized_length if data_length is not None else 0xFFFFFFFF
    return (
        b"RIFF"
        + struct.pack("<I", chunk_size)
        + b"WAVE"
        + b"fmt "
        + struct.pack("<IHHIIHH", 16, 1, channels, sample_rate, byte_rate, block_align, bits)
        + b"data"
        + struct.pack("<I", normalized_length)
    )


def extract_transcript(payload: Any) -> str:
    candidates: list[str] = []

    def visit(value: Any, *, key: str | None = None) -> None:
        if value is None:
            return
        if isinstance(value, str):
            text = value.strip()
            if key in {"text", "utterance", "transcript", "sentence", "result", "payload_msg"} and text:
                candidates.append(text)
            return
        if isinstance(value, dict):
            for child_key in ("text", "utterance", "transcript", "sentence", "result"):
                child = value.get(child_key)
                if isinstance(child, str) and child.strip():
                    candidates.append(child.strip())
            for child_key, child_value in value.items():
                visit(child_value, key=str(child_key))
            return
        if isinstance(value, list):
            for item in value:
                visit(item, key=key)

    visit(payload)

    seen: set[str] = set()
    ordered: list[str] = []
    for item in candidates:
        if item not in seen:
            seen.add(item)
            ordered.append(item)
    if not ordered:
        return ""
    return max(ordered, key=lambda item: (len(item), ordered.index(item)))


@dataclass(slots=True)
class VolcengineAsrEvent:
    event: str
    text: str = ""
    payload: Any = None
    is_last: bool = False


@dataclass(slots=True)
class ParsedAsrResponse:
    code: int = 0
    event: int = 0
    is_last_package: bool = False
    payload_sequence: int = 0
    payload_size: int = 0
    payload_msg: Any = None


class AsrRequestHeader:
    def __init__(self) -> None:
        self.message_type = MessageType.CLIENT_FULL_REQUEST
        self.message_type_specific_flags = MessageTypeSpecificFlags.POS_SEQUENCE
        self.serialization_type = SerializationType.JSON
        self.compression_type = CompressionType.GZIP
        self.reserved_data = bytes([0x00])

    def with_message_type(self, message_type: int) -> "AsrRequestHeader":
        self.message_type = message_type
        return self

    def with_message_type_specific_flags(self, flags: int) -> "AsrRequestHeader":
        self.message_type_specific_flags = flags
        return self

    def to_bytes(self) -> bytes:
        header = bytearray()
        header.append((ProtocolVersion.V1 << 4) | 1)
        header.append((self.message_type << 4) | self.message_type_specific_flags)
        header.append((self.serialization_type << 4) | self.compression_type)
        header.extend(self.reserved_data)
        return bytes(header)


def build_init_request(
    *,
    seq: int,
    sample_rate: int,
    app_uid: str,
) -> bytes:
    header = AsrRequestHeader().with_message_type_specific_flags(MessageTypeSpecificFlags.POS_SEQUENCE)
    payload = {
        "user": {
            "uid": app_uid,
        },
        "audio": {
            "format": "wav",
            "codec": "raw",
            "rate": sample_rate,
            "bits": 16,
            "channel": 1,
        },
        "request": {
            "model_name": "bigmodel",
            "enable_itn": True,
            "enable_punc": True,
            "enable_ddc": True,
            "show_utterances": True,
            "enable_nonstream": False,
        },
    }
    compressed_payload = gzip_compress(json.dumps(payload).encode("utf-8"))
    request = bytearray()
    request.extend(header.to_bytes())
    request.extend(struct.pack(">i", seq))
    request.extend(struct.pack(">I", len(compressed_payload)))
    request.extend(compressed_payload)
    return bytes(request)


def build_audio_request(seq: int, payload: bytes, *, is_last: bool) -> bytes:
    header = AsrRequestHeader().with_message_type(MessageType.CLIENT_AUDIO_ONLY_REQUEST)
    next_seq = seq
    if is_last:
        header.with_message_type_specific_flags(MessageTypeSpecificFlags.NEG_WITH_SEQUENCE)
        next_seq = -seq
    else:
        header.with_message_type_specific_flags(MessageTypeSpecificFlags.POS_SEQUENCE)
    compressed_payload = gzip_compress(payload)
    request = bytearray()
    request.extend(header.to_bytes())
    request.extend(struct.pack(">i", next_seq))
    request.extend(struct.pack(">I", len(compressed_payload)))
    request.extend(compressed_payload)
    return bytes(request)


def parse_response(message: bytes) -> ParsedAsrResponse:
    response = ParsedAsrResponse()
    header_size = message[0] & 0x0F
    message_type = message[1] >> 4
    message_type_specific_flags = message[1] & 0x0F
    serialization_method = message[2] >> 4
    compression_type = message[2] & 0x0F
    payload = message[header_size * 4 :]

    if message_type_specific_flags & 0x01:
        response.payload_sequence = struct.unpack(">i", payload[:4])[0]
        payload = payload[4:]
    if message_type_specific_flags & 0x02:
        response.is_last_package = True
    if message_type_specific_flags & 0x04:
        response.event = struct.unpack(">i", payload[:4])[0]
        payload = payload[4:]

    if message_type == MessageType.SERVER_FULL_RESPONSE:
        response.payload_size = struct.unpack(">I", payload[:4])[0]
        payload = payload[4:]
    elif message_type == MessageType.SERVER_ERROR_RESPONSE:
        response.code = struct.unpack(">i", payload[:4])[0]
        response.payload_size = struct.unpack(">I", payload[4:8])[0]
        payload = payload[8:]

    if payload and compression_type == CompressionType.GZIP:
        payload = gzip_decompress(payload)

    if payload and serialization_method == SerializationType.JSON:
        response.payload_msg = json.loads(payload.decode("utf-8"))
    return response


class VolcengineAsrSession:
    def __init__(
        self,
        *,
        url: str,
        app_key: str,
        access_key: str,
        resource_id: str,
        sample_rate: int,
        chunk_ms: int,
        uid: str,
    ) -> None:
        self._url = url
        self._app_key = app_key
        self._access_key = access_key
        self._resource_id = resource_id
        self._sample_rate = sample_rate
        self._chunk_ms = chunk_ms
        self._uid = uid
        self._seq = 1
        self._sent_audio = False
        self._closed = False
        self._http_session: aiohttp.ClientSession | None = None
        self._ws: aiohttp.ClientWebSocketResponse | None = None
        self._connect_id = str(uuid.uuid4())

    async def __aenter__(self) -> "VolcengineAsrSession":
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.close()

    async def connect(self) -> None:
        if not self._app_key or not self._access_key:
            raise VolcengineAsrError("未配置火山引擎语音识别密钥。")

        self._http_session = aiohttp.ClientSession()
        try:
            self._ws = await self._http_session.ws_connect(
                self._url,
                headers={
                    "X-Api-Resource-Id": self._resource_id,
                    "X-Api-Connect-Id": self._connect_id,
                    "X-Api-Request-Id": self._connect_id,
                    "X-Api-Access-Key": self._access_key,
                    "X-Api-App-Key": self._app_key,
                },
                heartbeat=30,
                max_msg_size=0,
            )
        except WSServerHandshakeError as exc:
            logid = ""
            api_message = ""
            api_status = ""
            if exc.headers is not None:
                logid = exc.headers.get("X-Tt-Logid", "") or exc.headers.get("x-tt-logid", "")
                api_message = exc.headers.get("X-Api-Message", "") or exc.headers.get("x-api-message", "")
                api_status = exc.headers.get("X-Api-Status-Code", "") or exc.headers.get("x-api-status-code", "")
            await self.close()
            detail = (
                "火山引擎 WebSocket 握手失败。"
                " 请检查 APP ID、Access Token、Resource ID 和服务地址是否正确。"
                f" status={exc.status}"
            )
            if api_status:
                detail += f" api_status={api_status}"
            if api_message:
                detail += f" api_message={api_message}"
            if logid:
                detail += f" logid={logid}"
            if exc.message:
                detail += f" message={exc.message}"
            raise VolcengineAsrError(detail) from exc
        except Exception as exc:
            await self.close()
            raise VolcengineAsrError(f"火山引擎连接失败：{exc}") from exc
        await self._send_bytes(
            build_init_request(
                seq=self._seq,
                sample_rate=self._sample_rate,
                app_uid=self._uid,
            )
        )
        self._seq += 1
        response = await self._receive_response()
        if response.code != 0:
            raise VolcengineAsrError(f"火山引擎初始化失败，错误码 {response.code}。")

    async def send_audio(self, chunk: bytes) -> None:
        if not chunk:
            return
        payload = chunk
        if not self._sent_audio:
            payload = build_wav_header(None, sample_rate=self._sample_rate) + payload
            self._sent_audio = True
        await self._send_bytes(build_audio_request(self._seq, payload, is_last=False))
        self._seq += 1

    async def finish(self, last_chunk: bytes = b"") -> None:
        payload = last_chunk
        if not self._sent_audio:
            payload = build_wav_header(len(payload), sample_rate=self._sample_rate) + payload
            self._sent_audio = True
        await self._send_bytes(build_audio_request(self._seq, payload, is_last=True))

    async def iter_events(self) -> AsyncIterator[VolcengineAsrEvent]:
        while True:
            response = await self._receive_response()
            if response.code != 0:
                raise VolcengineAsrError(f"火山引擎识别失败，错误码 {response.code}。")
            text = extract_transcript(response.payload_msg)
            yield VolcengineAsrEvent(
                event="final" if response.is_last_package else "partial",
                text=text,
                payload=response.payload_msg,
                is_last=response.is_last_package,
            )
            if response.is_last_package:
                break

    async def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        if self._ws is not None and not self._ws.closed:
            await self._ws.close()
        if self._http_session is not None and not self._http_session.closed:
            await self._http_session.close()

    async def _send_bytes(self, payload: bytes) -> None:
        if self._ws is None:
            raise VolcengineAsrError("语音会话尚未建立。")
        await self._ws.send_bytes(payload)

    async def _receive_response(self) -> ParsedAsrResponse:
        if self._ws is None:
            raise VolcengineAsrError("语音会话尚未建立。")
        message = await self._ws.receive()
        if message.type == aiohttp.WSMsgType.BINARY:
            return parse_response(message.data)
        if message.type == aiohttp.WSMsgType.TEXT:
            raise VolcengineAsrError(message.data)
        if message.type == aiohttp.WSMsgType.CLOSED:
            raise VolcengineAsrError("火山引擎连接已关闭。")
        if message.type == aiohttp.WSMsgType.ERROR:
            raise VolcengineAsrError("火山引擎连接异常。")
        raise VolcengineAsrError(f"无法识别的火山引擎响应类型：{message.type}")


class VolcengineAsrClient:
    def __init__(
        self,
        *,
        url: str,
        app_key: str,
        access_key: str,
        resource_id: str,
        sample_rate: int,
        chunk_ms: int,
    ) -> None:
        self._url = url
        self._app_key = app_key
        self._access_key = access_key
        self._resource_id = resource_id
        self._sample_rate = sample_rate
        self._chunk_ms = chunk_ms

    def create_session(self, *, uid: str, sample_rate: int | None = None, chunk_ms: int | None = None) -> VolcengineAsrSession:
        return VolcengineAsrSession(
            url=self._url,
            app_key=self._app_key,
            access_key=self._access_key,
            resource_id=self._resource_id,
            sample_rate=sample_rate or self._sample_rate,
            chunk_ms=chunk_ms or self._chunk_ms,
            uid=uid,
        )
