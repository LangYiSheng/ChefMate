from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import uuid4

from sqlalchemy import text

from app.config import settings
from app.db.connection import engine
from app.domain.enums import AttachmentKind, ConversationStage, MessageRole, TaskStatus
from app.repositories.account_repository import account_repository
from app.repositories.conversation_repository import conversation_repository
from app.schemas.conversation import SendMessageRequest, UploadedAttachmentInput
from app.schemas.profile import UpdateProfileRequest
from app.services.auth_service import auth_service
from app.services.conversation_service import conversation_service
from app.services.file_service import file_service
from app.services.profile_service import profile_service
from app.services.recipe_catalog_service import recipe_catalog_service
from app.utils.recipe_snapshot import (
    apply_recipe_patch,
    build_task_recipe_snapshot_from_catalog,
    build_task_recipe_snapshot_from_generated,
)
from app.utils.security import hash_password
from test.case_schema import AgentEvalCase, AttachmentFixtureInput, TaskSeed
from test.fixtures import build_recipe_preset, resolve_dynamic_value, resolve_fixture_path, resolve_mime_type


TOOL_START_RE = re.compile(r"tool_start conversation=(?P<conversation>[^ ]+) tool=(?P<tool>[^ ]+) stage=(?P<stage>[^ ]+)")


class InMemoryLogHandler(logging.Handler):
    def __init__(self) -> None:
        super().__init__()
        self.setLevel(logging.DEBUG)
        self.records: list[dict[str, Any]] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(
            {
                "logger": record.name,
                "level": record.levelname,
                "message": record.getMessage(),
            }
        )


@dataclass
class HarnessContext:
    run_id: str
    user_id: int


class AgentEvaluationHarness:
    def __init__(self, *, run_id: str, keep_data: bool = False) -> None:
        self.run_id = run_id
        self.keep_data = keep_data
        self.context = HarnessContext(run_id=run_id, user_id=self._create_run_user())

    def _create_run_user(self) -> int:
        suffix = self.run_id.replace("-", "")[-8:]
        username = f"eval{suffix}"
        existing = account_repository.get_user_by_username(username)
        if existing is not None:
            return int(existing["id"])
        return account_repository.create_user(
            username=username,
            email=None,
            password_hash=hash_password("EvalPass123"),
            display_name=f"评测用户 {suffix}",
        )

    def reset_user_state(self) -> None:
        user_id = self.context.user_id
        asset_rows = self._list_user_assets(user_id)
        with engine.begin() as conn:
            conn.execute(
                text(
                    """
                    DELETE FROM conversation_message_attachment
                    WHERE message_id IN (
                        SELECT id FROM conversation_message
                        WHERE conversation_id IN (
                            SELECT id FROM conversation WHERE user_id = :user_id
                        )
                    )
                    """
                ),
                {"user_id": user_id},
            )
            conn.execute(
                text(
                    """
                    DELETE FROM conversation_message
                    WHERE conversation_id IN (
                        SELECT id FROM conversation WHERE user_id = :user_id
                    )
                    """
                ),
                {"user_id": user_id},
            )
            conn.execute(text("DELETE FROM conversation_task WHERE user_id = :user_id"), {"user_id": user_id})
            conn.execute(text("DELETE FROM conversation WHERE user_id = :user_id"), {"user_id": user_id})
            conn.execute(text("DELETE FROM uploaded_asset WHERE user_id = :user_id"), {"user_id": user_id})
            conn.execute(text("DELETE FROM user_preference_tag WHERE user_id = :user_id"), {"user_id": user_id})
        for row in asset_rows:
            storage_key = row.get("storage_key")
            if not storage_key:
                continue
            path = settings.upload_path / storage_key
            if path.exists():
                path.unlink()
        account_repository.update_user_profile(
            user_id,
            {
                "display_name": f"评测用户 {self.run_id[-8:]}",
                "allow_auto_update": 1,
                "auto_start_step_timer": 0,
                "cooking_preference_text": "",
                "has_completed_workspace_onboarding": 1,
                "is_first_workspace_visit": 0,
            },
        )

    def _list_user_assets(self, user_id: int) -> list[dict[str, Any]]:
        query = text("SELECT id, storage_key FROM uploaded_asset WHERE user_id = :user_id")
        with engine.connect() as conn:
            rows = conn.execute(query, {"user_id": user_id}).mappings().all()
        return [dict(row) for row in rows]

    def cleanup(self) -> None:
        if self.keep_data:
            return
        self.reset_user_state()

    def _build_task_snapshot(self, seed: TaskSeed | None) -> tuple[int | None, dict[str, Any] | None]:
        if seed is None:
            return None, None

        source_recipe_id = resolve_dynamic_value(seed.source_recipe_id)
        if source_recipe_id is None and seed.source_recipe_selector:
            selector = seed.source_recipe_selector
            if selector == "first_published":
                source_recipe_id = recipe_catalog_service.list_entries()[0].id
            elif selector == "second_published":
                source_recipe_id = recipe_catalog_service.list_entries()[1].id
            else:
                raise ValueError(f"不支持的 source_recipe_selector：{selector}")

        if source_recipe_id is not None and seed.recipe_snapshot is None and seed.recipe_snapshot_preset is None:
            lookup = recipe_catalog_service.get_recipe_by_id(int(source_recipe_id), include=["recipe", "tags", "ingredients", "steps"])
            snapshot = build_task_recipe_snapshot_from_catalog(lookup)
        elif seed.recipe_snapshot_preset:
            snapshot = build_task_recipe_snapshot_from_generated(
                build_recipe_preset(seed.recipe_snapshot_preset)
            )
        elif seed.recipe_snapshot is not None:
            snapshot = build_task_recipe_snapshot_from_generated(
                resolve_dynamic_value(seed.recipe_snapshot)
            )
        else:
            raise ValueError("TaskSeed 需要 recipe_snapshot_preset、recipe_snapshot 或 source_recipe_id。")

        patch: dict[str, Any] = {}
        if seed.ingredient_overrides:
            patch["ingredients"] = [item.model_dump(mode="json", exclude_none=True) for item in seed.ingredient_overrides]
        if seed.step_overrides:
            patch["steps"] = [item.model_dump(mode="json", exclude_none=True) for item in seed.step_overrides]
        if patch:
            snapshot = apply_recipe_patch(snapshot, patch, mode="planning")

        return int(source_recipe_id) if source_recipe_id is not None else None, snapshot.model_dump(mode="json")

    def prepare_case(self, case: AgentEvalCase) -> tuple[dict[str, Any], str]:
        self.reset_user_state()

        profile_service.update_profile(
            self.context.user_id,
            UpdateProfileRequest(
                display_name=case.initial_state.user_profile.display_name,
                cooking_preference_text=case.initial_state.user_profile.cooking_preference_text,
                tag_selections=case.initial_state.user_profile.tag_selections,
                allow_auto_update=case.initial_state.user_profile.allow_auto_update,
                auto_start_step_timer=case.initial_state.user_profile.auto_start_step_timer,
                complete_workspace_onboarding=case.initial_state.user_profile.complete_workspace_onboarding,
            ),
        )
        user = auth_service.get_user_profile(self.context.user_id)

        source_recipe_id, recipe_snapshot = self._build_task_snapshot(case.initial_state.current_task)
        task_id = str(uuid4()) if case.initial_state.current_task else None
        conversation_stage = (
            case.initial_state.current_task.stage
            if case.initial_state.current_task
            else case.initial_state.conversation_stage
        )
        current_recipe_name = recipe_snapshot.get("name") if isinstance(recipe_snapshot, dict) else None
        conversation_id = conversation_repository.create_conversation(
            user_id=user.id,
            title=case.initial_state.conversation_title or case.title,
            stage=conversation_stage,
            current_recipe_name=current_recipe_name,
            suggestions=[],
            summary_text=case.initial_state.conversation_summary,
            current_task_id=task_id,
        )
        if task_id is not None and case.initial_state.current_task is not None:
            conversation_repository.create_task(
                task_id=task_id,
                user_id=user.id,
                conversation_id=conversation_id,
                stage=case.initial_state.current_task.stage,
                status=TaskStatus.ACTIVE,
                source_recipe_id=source_recipe_id,
                recipe_snapshot_json=json.dumps(recipe_snapshot, ensure_ascii=False) if recipe_snapshot else None,
            )
            conversation_repository.update_conversation(
                conversation_id,
                {
                    "current_task_id": task_id,
                    "current_recipe_name": current_recipe_name,
                },
            )
        for message in case.initial_state.recent_messages:
            conversation_repository.create_message(
                conversation_id=conversation_id,
                task_id=task_id,
                role=MessageRole(message.role),
                content=resolve_dynamic_value(message.content),
            )
        return user.model_dump(mode="json"), conversation_id

    def _save_attachment(self, user_id: int, attachment: AttachmentFixtureInput) -> UploadedAttachmentInput:
        path = resolve_fixture_path(attachment.path)
        response = file_service.save_image(
            user_id=user_id,
            payload=path.read_bytes(),
            filename=attachment.name or path.name,
            mime_type=resolve_mime_type(path, attachment.mime_type),
        )
        return UploadedAttachmentInput(
            kind=AttachmentKind.IMAGE,
            file_id=response.id,
            file_url=response.file_url,
            name=response.name,
        )

    async def run_case(self, case: AgentEvalCase) -> dict[str, Any]:
        user_payload, conversation_id = self.prepare_case(case)
        user = auth_service.get_user_profile(int(user_payload["id"]))
        logger_handler = InMemoryLogHandler()
        logger = logging.getLogger()
        original_level = logger.level
        if original_level > logging.INFO:
            logger.setLevel(logging.INFO)
        logger.addHandler(logger_handler)
        raw_trace: dict[str, Any] = {
            "case_id": case.case_id,
            "suite": case.suite,
            "title": case.title,
            "goal": case.goal,
            "conversation_id": conversation_id,
            "run_id": self.run_id,
            "turns": [],
        }

        try:
            for turn in case.turns:
                attachments = [
                    self._save_attachment(user.id, attachment)
                    for attachment in turn.attachments
                ]
                payload = SendMessageRequest(
                    content=resolve_dynamic_value(turn.content),
                    attachments=attachments,
                    action=resolve_dynamic_value(turn.action.model_dump(mode="json")) if turn.action else None,
                    client_card_state=resolve_dynamic_value(turn.client_card_state),
                )
                statuses: list[dict[str, Any]] = []
                tokens: list[str] = []
                final_event: dict[str, Any] | None = None
                error_detail: str | None = None
                log_offset = len(logger_handler.records)
                try:
                    async for event in conversation_service.stream_message(
                        user=user,
                        conversation_id=conversation_id,
                        payload=payload,
                    ):
                        if event["event"] == "status":
                            statuses.append(event["data"])
                        elif event["event"] == "token":
                            tokens.append(event["data"].get("text") or "")
                        elif event["event"] == "final":
                            final_event = event["data"]
                except Exception as exc:  # noqa: BLE001
                    error_detail = str(exc)

                turn_logs = logger_handler.records[log_offset:]
                tool_sequence = [
                    match.group("tool")
                    for record in turn_logs
                    if (match := TOOL_START_RE.search(record["message"]))
                ]
                current_conversation = conversation_repository.get_conversation(
                    user_id=user.id,
                    conversation_id=conversation_id,
                )
                current_task = conversation_repository.get_current_task(conversation_id)
                raw_trace["turns"].append(
                    {
                        "user_input": payload.model_dump(mode="json", exclude_none=True),
                        "status_events": statuses,
                        "token_text": "".join(tokens),
                        "final_event": final_event,
                        "assistant_content": (
                            final_event["message"]["content"]
                            if isinstance(final_event, dict)
                            else "".join(tokens).strip()
                        ),
                        "error_detail": error_detail,
                        "log_records": turn_logs,
                        "tool_sequence": tool_sequence,
                        "conversation_stage_after_turn": current_conversation.get("stage") if current_conversation else None,
                        "task_after_turn": current_task,
                    }
                )
                if error_detail:
                    raw_trace["unexpected_error"] = error_detail
                    break
        finally:
            logger.removeHandler(logger_handler)
            logger.setLevel(original_level)

        raw_trace["final_conversation"] = conversation_repository.get_conversation(
            user_id=user.id,
            conversation_id=conversation_id,
        )
        raw_trace["final_task"] = conversation_repository.get_current_task(conversation_id)
        raw_trace["messages"] = conversation_repository.list_messages(conversation_id)
        return raw_trace
