from __future__ import annotations

import json
from typing import Any
from uuid import uuid4

from sqlalchemy import bindparam
from sqlalchemy import text

from app.db.connection import engine
from app.domain.enums import MessageRole, TaskStatus


def _dump_json(value: Any) -> str | None:
    if value is None:
        return None
    return json.dumps(value, ensure_ascii=False)


def _load_json(value: Any) -> Any:
    if value in (None, ""):
        return None
    if isinstance(value, (dict, list)):
        return value
    return json.loads(value)


class ConversationRepository:
    def create_conversation(
        self,
        *,
        user_id: int,
        title: str,
        stage: str,
        current_recipe_name: str | None,
        suggestions: list[str],
        summary_text: str = "",
        current_task_id: str | None = None,
    ) -> str:
        conversation_id = str(uuid4())
        query = text(
            """
            INSERT INTO conversation (
                id,
                user_id,
                title,
                stage,
                current_recipe_name,
                suggestions_json,
                summary_text,
                current_task_id
            ) VALUES (
                :id,
                :user_id,
                :title,
                :stage,
                :current_recipe_name,
                :suggestions_json,
                :summary_text,
                :current_task_id
            )
            """
        )
        with engine.begin() as conn:
            conn.execute(
                query,
                {
                    "id": conversation_id,
                    "user_id": user_id,
                    "title": title,
                    "stage": stage,
                    "current_recipe_name": current_recipe_name,
                    "suggestions_json": _dump_json(suggestions),
                    "summary_text": summary_text,
                    "current_task_id": current_task_id,
                },
            )
        return conversation_id

    def get_conversation(self, *, user_id: int, conversation_id: str) -> dict[str, Any] | None:
        query = text(
            """
            SELECT *
            FROM conversation
            WHERE id = :conversation_id
              AND user_id = :user_id
            LIMIT 1
            """
        )
        with engine.connect() as conn:
            row = conn.execute(
                query,
                {
                    "conversation_id": conversation_id,
                    "user_id": user_id,
                },
            ).mappings().first()
        if row is None:
            return None
        payload = dict(row)
        payload["suggestions_json"] = _load_json(payload.get("suggestions_json")) or []
        return payload

    def list_conversations(self, *, user_id: int) -> list[dict[str, Any]]:
        query = text(
            """
            SELECT *
            FROM conversation
            WHERE user_id = :user_id
            ORDER BY updated_at DESC, created_at DESC
            """
        )
        with engine.connect() as conn:
            rows = conn.execute(query, {"user_id": user_id}).mappings().all()
        payloads = []
        for row in rows:
            item = dict(row)
            item["suggestions_json"] = _load_json(item.get("suggestions_json")) or []
            payloads.append(item)
        return payloads

    def update_conversation(self, conversation_id: str, payload: dict[str, Any]) -> None:
        if not payload:
            return
        params = dict(payload)
        if "suggestions_json" in params:
            params["suggestions_json"] = _dump_json(params["suggestions_json"])
        params["conversation_id"] = conversation_id
        assignments = ", ".join(f"{key} = :{key}" for key in params if key != "conversation_id")
        query = text(
            f"""
            UPDATE conversation
            SET {assignments}
            WHERE id = :conversation_id
            """
        )
        with engine.begin() as conn:
            conn.execute(query, params)

    def delete_conversations(self, *, user_id: int, conversation_ids: list[str]) -> list[str]:
        if not conversation_ids:
            return []

        select_query = text(
            """
            SELECT id
            FROM conversation
            WHERE user_id = :user_id
              AND id IN :conversation_ids
            """
        ).bindparams(bindparam("conversation_ids", expanding=True))
        delete_query = text(
            """
            DELETE FROM conversation
            WHERE user_id = :user_id
              AND id IN :conversation_ids
            """
        ).bindparams(bindparam("conversation_ids", expanding=True))

        with engine.begin() as conn:
            rows = conn.execute(
                select_query,
                {
                    "user_id": user_id,
                    "conversation_ids": conversation_ids,
                },
            ).mappings().all()
            deleted_id_set = {str(row["id"]) for row in rows}
            if not deleted_id_set:
                return []

            conn.execute(
                delete_query,
                {
                    "user_id": user_id,
                    "conversation_ids": list(deleted_id_set),
                },
            )

        return [conversation_id for conversation_id in conversation_ids if conversation_id in deleted_id_set]

    def create_task(
        self,
        *,
        task_id: str,
        user_id: int,
        conversation_id: str,
        stage: str,
        status: str = TaskStatus.ACTIVE,
        source_recipe_id: int | None = None,
        recipe_snapshot_json: str | None = None,
    ) -> None:
        query = text(
            """
            INSERT INTO conversation_task (
                id,
                user_id,
                conversation_id,
                stage,
                status,
                source_recipe_id,
                recipe_snapshot_json
            ) VALUES (
                :id,
                :user_id,
                :conversation_id,
                :stage,
                :status,
                :source_recipe_id,
                :recipe_snapshot_json
            )
            """
        )
        with engine.begin() as conn:
            conn.execute(
                query,
                {
                    "id": task_id,
                    "user_id": user_id,
                    "conversation_id": conversation_id,
                    "stage": stage,
                    "status": status,
                    "source_recipe_id": source_recipe_id,
                    "recipe_snapshot_json": recipe_snapshot_json,
                },
            )

    def get_task(self, task_id: str) -> dict[str, Any] | None:
        query = text(
            """
            SELECT *
            FROM conversation_task
            WHERE id = :task_id
            LIMIT 1
            """
        )
        with engine.connect() as conn:
            row = conn.execute(query, {"task_id": task_id}).mappings().first()
        if row is None:
            return None
        payload = dict(row)
        payload["recipe_snapshot_json"] = _load_json(payload.get("recipe_snapshot_json"))
        return payload

    def get_current_task(self, conversation_id: str) -> dict[str, Any] | None:
        query = text(
            """
            SELECT t.*
            FROM conversation c
            JOIN conversation_task t ON t.id = c.current_task_id
            WHERE c.id = :conversation_id
            LIMIT 1
            """
        )
        with engine.connect() as conn:
            row = conn.execute(query, {"conversation_id": conversation_id}).mappings().first()
        if row is None:
            return None
        payload = dict(row)
        payload["recipe_snapshot_json"] = _load_json(payload.get("recipe_snapshot_json"))
        return payload

    def update_task(self, task_id: str, payload: dict[str, Any]) -> None:
        if not payload:
            return
        params = dict(payload)
        if "recipe_snapshot_json" in params:
            params["recipe_snapshot_json"] = _dump_json(params["recipe_snapshot_json"])
        params["task_id"] = task_id
        assignments = ", ".join(f"{key} = :{key}" for key in params if key != "task_id")
        query = text(
            f"""
            UPDATE conversation_task
            SET {assignments}
            WHERE id = :task_id
            """
        )
        with engine.begin() as conn:
            conn.execute(query, params)

    def list_recent_finished_tasks(self, *, user_id: int, limit: int) -> list[dict[str, Any]]:
        query = text(
            """
            SELECT id, stage, status, outcome, recipe_snapshot_json, ended_at
            FROM conversation_task
            WHERE user_id = :user_id
              AND status <> 'active'
              AND record_in_history = 1
            ORDER BY ended_at DESC, updated_at DESC
            LIMIT :limit
            """
        )
        with engine.connect() as conn:
            rows = conn.execute(query, {"user_id": user_id, "limit": limit}).mappings().all()
        payloads = []
        for row in rows:
            item = dict(row)
            item["recipe_snapshot_json"] = _load_json(item.get("recipe_snapshot_json"))
            payloads.append(item)
        return payloads

    def list_recent_finished_source_recipes(self, *, user_id: int, limit: int) -> list[dict[str, Any]]:
        query = text(
            """
            SELECT source_recipe_id, ended_at
            FROM conversation_task
            WHERE user_id = :user_id
              AND status <> 'active'
              AND record_in_history = 1
              AND source_recipe_id IS NOT NULL
            ORDER BY ended_at DESC, updated_at DESC
            LIMIT :limit
            """
        )
        with engine.connect() as conn:
            rows = conn.execute(query, {"user_id": user_id, "limit": limit * 4}).mappings().all()

        payloads: list[dict[str, Any]] = []
        seen_recipe_ids: set[int] = set()
        for row in rows:
            recipe_id = row.get("source_recipe_id")
            if recipe_id is None:
                continue
            resolved_recipe_id = int(recipe_id)
            if resolved_recipe_id in seen_recipe_ids:
                continue
            seen_recipe_ids.add(resolved_recipe_id)
            payloads.append(
                {
                    "source_recipe_id": resolved_recipe_id,
                    "ended_at": row.get("ended_at"),
                }
            )
            if len(payloads) >= limit:
                break
        return payloads

    def create_message(
        self,
        *,
        conversation_id: str,
        task_id: str | None,
        role: MessageRole | str,
        content: str,
        suggestions: list[str] | None = None,
        card_type: str | None = None,
        card_payload: dict[str, Any] | None = None,
    ) -> str:
        message_id = str(uuid4())
        query = text(
            """
            INSERT INTO conversation_message (
                id,
                conversation_id,
                task_id,
                role,
                content_md,
                suggestions_json,
                card_type,
                card_payload_json
            ) VALUES (
                :id,
                :conversation_id,
                :task_id,
                :role,
                :content_md,
                :suggestions_json,
                :card_type,
                :card_payload_json
            )
            """
        )
        with engine.begin() as conn:
            conn.execute(
                query,
                {
                    "id": message_id,
                    "conversation_id": conversation_id,
                    "task_id": task_id,
                    "role": str(role),
                    "content_md": content,
                    "suggestions_json": _dump_json(suggestions),
                    "card_type": card_type,
                    "card_payload_json": _dump_json(card_payload),
                },
            )
        return message_id

    def attach_assets_to_message(self, message_id: str, asset_ids: list[str]) -> None:
        if not asset_ids:
            return
        with engine.begin() as conn:
            for index, asset_id in enumerate(asset_ids):
                conn.execute(
                    text(
                        """
                        INSERT INTO conversation_message_attachment (
                            message_id,
                            asset_id,
                            sort_order
                        ) VALUES (
                            :message_id,
                            :asset_id,
                            :sort_order
                        )
                        """
                    ),
                    {
                        "message_id": message_id,
                        "asset_id": asset_id,
                        "sort_order": index,
                    },
                )

    def list_messages(self, conversation_id: str) -> list[dict[str, Any]]:
        message_query = text(
            """
            SELECT *
            FROM conversation_message
            WHERE conversation_id = :conversation_id
            ORDER BY created_at ASC, id ASC
            """
        )
        attachment_query = text(
            """
            SELECT
                cma.message_id,
                ua.id AS asset_id,
                ua.kind,
                ua.original_name,
                ua.storage_key
            FROM conversation_message_attachment cma
            JOIN uploaded_asset ua ON ua.id = cma.asset_id
            WHERE cma.message_id IN :message_ids
            ORDER BY cma.sort_order ASC
            """
        )
        with engine.connect() as conn:
            messages = conn.execute(message_query, {"conversation_id": conversation_id}).mappings().all()
            message_ids = [row["id"] for row in messages]
        payloads = []
        attachment_map: dict[str, list[dict[str, Any]]] = {message_id: [] for message_id in message_ids}
        if message_ids:
            from sqlalchemy import bindparam

            query = attachment_query.bindparams(bindparam("message_ids", expanding=True))
            with engine.connect() as conn:
                attachment_rows = conn.execute(query, {"message_ids": message_ids}).mappings().all()
            for row in attachment_rows:
                attachment_map[row["message_id"]].append(dict(row))
        for row in messages:
            item = dict(row)
            item["suggestions_json"] = _load_json(item.get("suggestions_json"))
            item["card_payload_json"] = _load_json(item.get("card_payload_json"))
            item["attachments"] = attachment_map.get(item["id"], [])
            payloads.append(item)
        return payloads


conversation_repository = ConversationRepository()
