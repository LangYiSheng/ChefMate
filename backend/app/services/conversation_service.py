from __future__ import annotations

import asyncio
from collections import defaultdict
import logging
from typing import Any, AsyncIterator

from langchain_core.messages import AIMessage, AIMessageChunk, BaseMessage

from app.agent.graph import build_agent_graph, build_initial_messages
from app.agent.runtime import AgentTurnContext
from app.config import settings
from app.domain.cards import build_cooking_guide_card, build_pantry_status_card
from app.domain.enums import AttachmentKind, CardType, ConversationStage, MessageRole
from app.domain.models import (
    ConversationDetail,
    ConversationMessage,
    ConversationSummary,
    MessageAttachment,
    UserProfileSnapshot,
)
from app.repositories.conversation_repository import conversation_repository
from app.repositories.file_repository import file_repository
from app.schemas.conversation import (
    ConversationBulkDeleteRequest,
    ConversationBulkDeleteResponse,
    ConversationCreateRequest,
    ConversationCreateResponse,
    SendMessageRequest,
    SendMessageResponse,
)
from app.schemas.profile import UpdateProfileRequest
from app.services.profile_service import profile_service
from app.services.recipe_catalog_service import recipe_catalog_service
from app.services.task_service import task_service
from app.infra.llm.clients import build_langchain_chat_model
from app.utils.recipe_snapshot import apply_client_card_state_overlay
from app.utils.time import utc_now

logger = logging.getLogger(__name__)


class ConversationService:
    def __init__(self) -> None:
        self._conversation_locks: dict[str, asyncio.Lock] = {}

    def list_conversations(self, user: UserProfileSnapshot) -> list[ConversationSummary]:
        return [self._row_to_summary(item) for item in conversation_repository.list_conversations(user_id=user.id)]

    def delete_conversations(
        self,
        *,
        user: UserProfileSnapshot,
        payload: ConversationBulkDeleteRequest,
    ) -> ConversationBulkDeleteResponse:
        seen_ids: set[str] = set()
        conversation_ids = []
        for conversation_id in payload.conversation_ids:
            normalized_id = conversation_id.strip()
            if not normalized_id or normalized_id in seen_ids:
                continue
            seen_ids.add(normalized_id)
            conversation_ids.append(normalized_id)

        deleted_ids = conversation_repository.delete_conversations(
            user_id=user.id,
            conversation_ids=conversation_ids,
        )
        return ConversationBulkDeleteResponse(
            deleted_ids=deleted_ids,
            deleted_count=len(deleted_ids),
        )

    def get_conversation_detail(self, *, user: UserProfileSnapshot, conversation_id: str) -> ConversationDetail:
        conversation = conversation_repository.get_conversation(user_id=user.id, conversation_id=conversation_id)
        if conversation is None:
            raise ValueError("对话不存在。")
        stage, snapshot = self._get_live_task_stage_snapshot(conversation_id, ConversationStage(conversation["stage"]))
        messages = self._load_message_models(conversation_id)
        messages = self._refresh_live_stage_card(messages, stage=stage, snapshot=snapshot)
        messages = self._normalize_card_history(messages)
        return ConversationDetail(
            **self._row_to_summary(conversation).model_dump(mode="json"),
            messages=messages,
        )

    def create_conversation(
        self,
        *,
        user: UserProfileSnapshot,
        payload: ConversationCreateRequest,
    ) -> ConversationCreateResponse:
        conversation_id = conversation_repository.create_conversation(
            user_id=user.id,
            title="等你说一句想吃什么",
            stage=ConversationStage.IDLE,
            current_recipe_name=None,
            suggestions=self._build_suggestions(ConversationStage.IDLE, None),
        )
        if payload.source == "recipe":
            if payload.recipe_id is None:
                raise ValueError("缺少 recipe_id，无法从菜谱开启对话。")
            task = task_service.create_task_from_recipe(
                user_id=user.id,
                conversation_id=conversation_id,
                recipe_id=payload.recipe_id,
            )
            recipe_snapshot = task.get("recipe_snapshot_json")
            task_recipe_name = recipe_snapshot.get("name") if isinstance(recipe_snapshot, dict) else None
            card = None
            if task_recipe_name:
                from app.utils.recipe_snapshot import load_task_recipe_snapshot
                from app.domain.cards import build_pantry_status_card

                snapshot = load_task_recipe_snapshot(recipe_snapshot)
                card = build_pantry_status_card(snapshot).model_dump(mode="json") if snapshot else None
            conversation_repository.update_conversation(
                conversation_id,
                {
                    "title": f"{task_recipe_name or '这道菜'} 的备料检查已经展开",
                    "stage": ConversationStage.PREPARING,
                    "current_recipe_name": task_recipe_name,
                    "suggestions_json": self._build_suggestions(ConversationStage.PREPARING, task_recipe_name),
                    "updated_at": utc_now(),
                },
            )
            conversation_repository.create_message(
                conversation_id=conversation_id,
                task_id=task["id"],
                role=MessageRole.ASSISTANT,
                content=f"已经为你打开 {task_recipe_name or '这道菜'} 的专属对话，我们直接从备料开始。",
                suggestions=self._build_suggestions(ConversationStage.PREPARING, task_recipe_name),
                card_type=CardType.PANTRY_STATUS,
                card_payload=card,
            )
        detail = self.get_conversation_detail(user=user, conversation_id=conversation_id)
        return ConversationCreateResponse(conversation=detail)

    async def send_message(
        self,
        *,
        user: UserProfileSnapshot,
        conversation_id: str,
        payload: SendMessageRequest,
    ) -> SendMessageResponse:
        final_response: SendMessageResponse | None = None
        async for event in self.stream_message(user=user, conversation_id=conversation_id, payload=payload):
            if event["event"] == "final":
                final_response = SendMessageResponse.model_validate(event["data"])
        if final_response is None:
            raise ValueError("本轮消息处理失败，未生成最终响应。")
        return final_response

    async def stream_message(
        self,
        *,
        user: UserProfileSnapshot,
        conversation_id: str,
        payload: SendMessageRequest,
    ) -> AsyncIterator[dict[str, Any]]:
        conversation_lock = self._conversation_locks.setdefault(conversation_id, asyncio.Lock())
        if conversation_lock.locked():
            raise ValueError("当前这段对话还在处理中，请等待本轮回复完成后再操作。")

        async with conversation_lock:
            try:
                conversation = conversation_repository.get_conversation(user_id=user.id, conversation_id=conversation_id)
                if conversation is None:
                    raise ValueError("对话不存在。")

                asset_ids, current_attachments = self._resolve_input_attachments(user, payload)
                logger.info(
                    "[agent-turn] incoming conversation=%s user_id=%s stage=%s task_id=%s content=%r attachments=%s action=%s client_card_state=%s",
                    conversation_id,
                    user.id,
                    conversation.get("stage"),
                    conversation.get("current_task_id"),
                    self._truncate_text(payload.content or ""),
                    [attachment.file_url or attachment.preview_url for attachment in current_attachments],
                    payload.action.model_dump(mode="json") if payload.action else None,
                    payload.client_card_state.model_dump(mode="json", exclude_none=True) if payload.client_card_state else None,
                )

                user_message_id = conversation_repository.create_message(
                    conversation_id=conversation_id,
                    task_id=conversation.get("current_task_id"),
                    role=MessageRole.USER,
                    content=payload.content or "",
                )
                conversation_repository.attach_assets_to_message(user_message_id, asset_ids)
                conversation_repository.update_conversation(conversation_id, {"updated_at": utc_now()})

                yield {"event": "status", "data": {"text": "正在理解你的需求..."}}

                turn = self._build_turn_context(
                    user=user,
                    conversation=conversation_repository.get_conversation(user_id=user.id, conversation_id=conversation_id),
                    payload=payload,
                    attachments=current_attachments,
                )
                agent_graph = build_agent_graph(turn)
                agent_input = build_initial_messages(turn)

                final_state: dict[str, Any] | None = None
                streamed_text_parts: list[str] = []

                async for event in agent_graph.astream_events(
                    agent_input,
                    version="v2",
                ):
                    event_name = event.get("event")
                    if event_name == "on_tool_start":
                        tool_name = event.get("name")
                        tool_input = event.get("data", {}).get("input")
                        logger.info(
                            "[agent-turn] tool_start conversation=%s tool=%s stage=%s input=%s",
                            conversation_id,
                            tool_name,
                            turn.active_stage.value,
                            self._safe_preview(tool_input),
                        )
                        yield {
                            "event": "status",
                            "data": {
                                "text": self._tool_status_text(tool_name),
                                "tool_name": tool_name,
                            },
                        }
                        continue

                    if event_name == "on_tool_end":
                        logger.info(
                            "[agent-turn] tool_end conversation=%s tool=%s stage=%s output=%s",
                            conversation_id,
                            event.get("name"),
                            turn.active_stage.value,
                            self._safe_preview(event.get("data", {}).get("output")),
                        )
                        continue

                    if event_name == "on_chat_model_start":
                        logger.info(
                            "[agent-turn] llm_start conversation=%s stage=%s",
                            conversation_id,
                            turn.active_stage.value,
                        )
                        continue

                    if event_name == "on_chat_model_stream":
                        chunk_text = self._extract_chunk_text(event.get("data", {}).get("chunk"))
                        if chunk_text:
                            streamed_text_parts.append(chunk_text)
                            yield {"event": "token", "data": {"text": chunk_text}}
                        continue

                    if event_name == "on_chat_model_end":
                        logger.info(
                            "[agent-turn] llm_end conversation=%s stage=%s",
                            conversation_id,
                            turn.active_stage.value,
                        )
                        continue

                    possible_output = event.get("data", {}).get("output")
                    if isinstance(possible_output, dict) and "messages" in possible_output:
                        final_state = possible_output

                final_text = self._extract_final_text(final_state) or "".join(streamed_text_parts).strip()
                if not final_text:
                    final_text = "我已经处理好了，我们继续下一步。"

                logger.info(
                    "[agent-turn] assistant_reply conversation=%s stage=%s card_type=%s reply=%r",
                    conversation_id,
                    turn.active_stage.value,
                    turn.response_card_type,
                    self._truncate_text(final_text),
                )
                response = self._persist_assistant_response(
                    user=user,
                    conversation_id=conversation_id,
                    turn=turn,
                    content=final_text,
                )
                await self._refresh_summary_if_needed(conversation_id)
                yield {"event": "final", "data": response.model_dump(mode="json")}
            except Exception:
                logger.exception("[agent-turn] failed conversation=%s user_id=%s", conversation_id, user.id)
                raise

    def _build_turn_context(
        self,
        *,
        user: UserProfileSnapshot,
        conversation: dict[str, Any] | None,
        payload: SendMessageRequest,
        attachments: list[MessageAttachment],
    ) -> AgentTurnContext:
        if conversation is None:
            raise ValueError("对话不存在。")
        current_task = conversation_repository.get_current_task(conversation["id"])
        from app.utils.recipe_snapshot import load_task_recipe_snapshot

        current_task_stage = ConversationStage(current_task["stage"]) if current_task else None
        current_task_snapshot = load_task_recipe_snapshot(current_task.get("recipe_snapshot_json")) if current_task else None
        client_card_state = (
            payload.client_card_state.model_dump(mode="json", exclude_none=True)
            if payload.client_card_state
            else {}
        )
        view_snapshot = apply_client_card_state_overlay(
            current_task_snapshot,
            client_card_state,
            stage=current_task_stage,
        )

        return AgentTurnContext(
            user=user,
            conversation_id=conversation["id"],
            conversation_title=conversation["title"],
            conversation_stage=ConversationStage(conversation["stage"]),
            conversation_summary=conversation.get("summary_text") or "",
            current_task_id=current_task["id"] if current_task else None,
            current_task_stage=current_task_stage,
            current_task_source_recipe_id=current_task.get("source_recipe_id") if current_task else None,
            current_task_snapshot=view_snapshot,
            latest_user_content=(payload.content or "").strip(),
            latest_user_action=payload.action,
            latest_attachments=attachments,
            client_card_state=client_card_state,
            recent_messages=[
                {
                    "role": message.role,
                    "content": message.content,
                }
                for message in self._load_message_models(conversation["id"])[-settings.conversation_memory_window :]
            ],
            recent_finished_tasks=self._serialize_task_history(
                conversation_repository.list_recent_finished_tasks(
                    user_id=user.id,
                    limit=settings.conversation_history_task_limit,
                )
            ),
            tag_catalog=profile_service.get_tag_catalog().model_dump(mode="json"),
        )

    def _persist_assistant_response(
        self,
        *,
        user: UserProfileSnapshot,
        conversation_id: str,
        turn: AgentTurnContext,
        content: str,
    ) -> SendMessageResponse:
        stage = turn.current_task_stage or turn.conversation_stage
        current_recipe_name = turn.current_task_snapshot.name if turn.current_task_snapshot else None
        suggestions = self._build_suggestions(stage, current_recipe_name)
        title = self._build_conversation_title(stage, current_recipe_name, turn.latest_user_content)
        card_type, card_payload = self._resolve_response_card(
            stage=stage,
            snapshot=turn.current_task_snapshot,
            explicit_card_type=turn.response_card_type,
            explicit_card_payload=turn.response_card,
        )
        conversation_repository.update_conversation(
            conversation_id,
            {
                "title": title,
                "stage": stage,
                "current_recipe_name": current_recipe_name,
                "suggestions_json": suggestions,
                "updated_at": utc_now(),
            },
        )
        message_id = conversation_repository.create_message(
            conversation_id=conversation_id,
            task_id=turn.current_task_id,
            role=MessageRole.ASSISTANT,
            content=content,
            suggestions=suggestions,
            card_type=card_type,
            card_payload=card_payload,
        )
        conversation_summary = ConversationSummary(
            id=conversation_id,
            title=title,
            stage=stage,
            current_recipe_name=current_recipe_name,
            suggestions=suggestions,
        )
        assistant_message = next(
            message
            for message in self._load_message_models(conversation_id)
            if message.id == message_id
        )
        return SendMessageResponse(conversation=conversation_summary, message=assistant_message)

    def _resolve_input_attachments(
        self,
        user: UserProfileSnapshot,
        payload: SendMessageRequest,
    ) -> tuple[list[str], list[MessageAttachment]]:
        asset_ids: list[str] = []
        attachments: list[MessageAttachment] = []
        for attachment in payload.attachments:
            if attachment.file_id is None:
                continue
            asset = file_repository.get_asset(attachment.file_id)
            if asset is None:
                continue
            if int(asset["user_id"]) != user.id:
                continue
            public_url = f"{settings.asset_url_prefix}/{asset['storage_key']}"
            asset_ids.append(asset["id"])
            attachments.append(
                MessageAttachment(
                    id=asset["id"],
                    kind=AttachmentKind(asset["kind"]),
                    name=asset["original_name"],
                    preview_url=public_url,
                    file_url=public_url,
                )
            )
        return asset_ids, attachments

    def _load_message_models(self, conversation_id: str) -> list[ConversationMessage]:
        models: list[ConversationMessage] = []
        for row in conversation_repository.list_messages(conversation_id):
            attachments = [
                MessageAttachment(
                    id=item["asset_id"],
                    kind=AttachmentKind(item["kind"]),
                    name=item["original_name"],
                    preview_url=f"{settings.asset_url_prefix}/{item['storage_key']}",
                    file_url=f"{settings.asset_url_prefix}/{item['storage_key']}",
                )
                for item in row.get("attachments", [])
            ]
            cards = []
            if row.get("card_payload_json"):
                cards.append(row["card_payload_json"])
            models.append(
                ConversationMessage(
                    id=row["id"],
                    role=MessageRole(row["role"]),
                    content=row.get("content_md") or "",
                    created_at=row["created_at"].isoformat() if row.get("created_at") else utc_now().isoformat(),
                    attachments=attachments,
                    suggestions=row.get("suggestions_json"),
                    cards=cards,
                )
            )
        return models

    def _normalize_card_history(self, messages: list[ConversationMessage]) -> list[ConversationMessage]:
        seen_types: set[str] = set()
        normalized = list(messages)
        for message in reversed(normalized):
            if not message.cards:
                continue
            next_cards = []
            for card in reversed(message.cards):
                card_type = self._card_type(card)
                if card_type in seen_types:
                    continue
                seen_types.add(card_type)
                next_cards.append(card)
            message.cards = list(reversed(next_cards))
        return normalized

    def _resolve_response_card(
        self,
        *,
        stage: ConversationStage,
        snapshot: Any,
        explicit_card_type: str | None,
        explicit_card_payload: dict[str, Any] | None,
    ) -> tuple[str | None, dict[str, Any] | None]:
        if snapshot is not None and stage == ConversationStage.PREPARING:
            return CardType.PANTRY_STATUS, build_pantry_status_card(snapshot).model_dump(mode="json")
        if snapshot is not None and stage == ConversationStage.COOKING:
            return CardType.COOKING_GUIDE, build_cooking_guide_card(snapshot).model_dump(mode="json")
        return explicit_card_type, explicit_card_payload

    def _get_live_task_stage_snapshot(
        self,
        conversation_id: str,
        fallback_stage: ConversationStage,
    ) -> tuple[ConversationStage, Any | None]:
        from app.utils.recipe_snapshot import load_task_recipe_snapshot

        current_task = conversation_repository.get_current_task(conversation_id)
        if current_task is None:
            return fallback_stage, None
        return (
            ConversationStage(current_task["stage"]),
            load_task_recipe_snapshot(current_task.get("recipe_snapshot_json")),
        )

    def _refresh_live_stage_card(
        self,
        messages: list[ConversationMessage],
        *,
        stage: ConversationStage,
        snapshot: Any | None,
    ) -> list[ConversationMessage]:
        card_type, card_payload = self._resolve_response_card(
            stage=stage,
            snapshot=snapshot,
            explicit_card_type=None,
            explicit_card_payload=None,
        )
        if card_type is None or card_payload is None:
            return messages
        for message in reversed(messages):
            if message.role != MessageRole.ASSISTANT:
                continue
            if any(self._card_type(card) == card_type for card in (message.cards or [])):
                return messages
            existing_cards = list(message.cards or [])
            existing_cards.append(card_payload)
            message.cards = existing_cards
            return messages
        return messages

    def _card_type(self, card: Any) -> str | None:
        return card["type"] if isinstance(card, dict) else getattr(card, "type", None)

    def _row_to_summary(self, row: dict[str, Any]) -> ConversationSummary:
        return ConversationSummary(
            id=row["id"],
            title=row["title"],
            stage=ConversationStage(row["stage"]),
            current_recipe_name=row.get("current_recipe_name"),
            suggestions=row.get("suggestions_json") or [],
        )

    def _build_suggestions(
        self,
        stage: ConversationStage,
        recipe_name: str | None,
    ) -> list[str]:
        if stage == ConversationStage.IDLE:
            return ["今晚想吃点热乎的", "冰箱里有鸡蛋和番茄", "帮我推荐一道快手菜"]
        if stage == ConversationStage.RECOMMENDING:
            return [
                "给我三道更清淡的",
                "先看看这道菜详情",
                "我想自己描述一道菜让你现写",
            ]
        if stage == ConversationStage.PREPARING:
            base = recipe_name or "这道菜"
            return [f"{base} 还缺什么", "这些都备齐了", "我想换一道菜"]
        base = recipe_name or "这道菜"
        return [f"{base} 下一步做什么", "这一步火候要多大", "帮我确认步骤是否完成"]

    def _build_conversation_title(
        self,
        stage: ConversationStage,
        recipe_name: str | None,
        latest_user_content: str,
    ) -> str:
        if stage == ConversationStage.IDLE:
            if latest_user_content:
                return latest_user_content[: settings.conversation_title_max_length]
            return "等你说一句想吃什么"
        if stage == ConversationStage.RECOMMENDING:
            return f"{recipe_name} 的做法正在确认" if recipe_name else "候选菜已经整理好了，等你拍板"
        if stage == ConversationStage.PREPARING:
            return f"{recipe_name} 的备料检查已经展开" if recipe_name else "备料阶段进行中"
        return f"{recipe_name} 正在烹饪中" if recipe_name else "烹饪阶段进行中"

    def _tool_status_text(self, tool_name: str | None) -> str:
        from app.agent.tools import TOOL_STATUS_LABELS

        return TOOL_STATUS_LABELS.get(tool_name or "", "正在调用工具处理...")

    def _extract_chunk_text(self, chunk: Any) -> str:
        if chunk is None:
            return ""
        if isinstance(chunk, AIMessageChunk):
            return self._extract_chunk_text(chunk.content)
        if isinstance(chunk, str):
            return chunk
        if isinstance(chunk, list):
            texts: list[str] = []
            for item in chunk:
                texts.append(self._extract_chunk_text(item))
            return "".join(texts)
        if isinstance(chunk, dict):
            if chunk.get("type") in {"text", "text_delta", "output_text"} and chunk.get("text"):
                return str(chunk["text"])
            if chunk.get("content"):
                return self._extract_chunk_text(chunk["content"])
        content = getattr(chunk, "content", None)
        if content is not None:
            return self._extract_chunk_text(content)
        return ""

    def _extract_final_text(self, final_state: dict[str, Any] | None) -> str:
        if not final_state:
            return ""
        for message in reversed(final_state.get("messages", [])):
            if isinstance(message, AIMessage):
                return self._extract_chunk_text(message.content).strip()
            if isinstance(message, BaseMessage) and getattr(message, "type", None) == "ai":
                return self._extract_chunk_text(getattr(message, "content", "")).strip()
            if isinstance(message, dict) and message.get("type") == "ai":
                return self._extract_chunk_text(message.get("content")).strip()
        return ""

    async def _refresh_summary_if_needed(self, conversation_id: str) -> None:
        messages = self._load_message_models(conversation_id)
        if len(messages) <= settings.conversation_summary_trigger_messages:
            return
        older_messages = messages[:-settings.conversation_memory_window]
        if not older_messages:
            return
        content = "\n".join(
            f"{message.role}: {message.content}"
            for message in older_messages
            if message.content
        )
        if not content.strip():
            return
        model = build_langchain_chat_model(temperature=0.1)
        summary_message = await model.ainvoke(
            [
                (
                    "system",
                    "请将下面这段 ChefMate 对话压缩成一段后续模型可继续使用的中文摘要。"
                    "重点保留：用户偏好、当前任务的关键决策、还未完成的事项、不要保留寒暄。",
                ),
                ("user", content),
            ]
        )
        summary_text = self._extract_chunk_text(summary_message.content).strip()
        if summary_text:
            conversation_repository.update_conversation(
                conversation_id,
                {
                    "summary_text": summary_text,
                    "updated_at": utc_now(),
                },
            )

    def _serialize_task_history(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        history: list[dict[str, Any]] = []
        for row in rows:
            recipe_name = None
            if isinstance(row.get("recipe_snapshot_json"), dict):
                recipe_name = row["recipe_snapshot_json"].get("name")
            history.append(
                {
                    "task_id": row["id"],
                    "stage": row.get("stage"),
                    "outcome": row.get("outcome"),
                    "recipe_name": recipe_name,
                    "ended_at": row["ended_at"].isoformat() if row.get("ended_at") else None,
                }
            )
        return history

    def _truncate_text(self, value: str, limit: int = 160) -> str:
        if len(value) <= limit:
            return value
        return value[: limit - 3] + "..."

    def _safe_preview(self, value: Any, limit: int = 240) -> str:
        if isinstance(value, dict):
            sanitized = dict(value)
            if "runtime" in sanitized:
                sanitized["runtime"] = "<injected>"
            if "messages" in sanitized and isinstance(sanitized["messages"], list):
                sanitized["messages"] = f"<{len(sanitized['messages'])} messages>"
            value = sanitized
        text = repr(value)
        return self._truncate_text(text, limit)


conversation_service = ConversationService()
