from __future__ import annotations

from uuid import uuid4

from app.domain.enums import ConversationStage, TaskOutcome, TaskStatus
from app.repositories.conversation_repository import conversation_repository
from app.services.recipe_catalog_service import recipe_catalog_service
from app.utils.recipe_snapshot import (
    apply_recipe_patch,
    build_task_recipe_snapshot_from_catalog,
    build_task_recipe_snapshot_from_generated,
    dump_task_recipe_snapshot,
    ensure_can_complete,
    ensure_can_enter_cooking,
    ensure_can_enter_preparation,
    load_task_recipe_snapshot,
)
from app.utils.time import utc_now


class TaskService:
    def start_recommendation_task(self, *, user_id: int, conversation_id: str) -> dict:
        current = conversation_repository.get_current_task(conversation_id)
        if current is not None and current["status"] == TaskStatus.ACTIVE:
            return current

        task_id = str(uuid4())
        conversation_repository.create_task(
            task_id=task_id,
            user_id=user_id,
            conversation_id=conversation_id,
            stage=ConversationStage.RECOMMENDING,
            status=TaskStatus.ACTIVE,
        )
        conversation_repository.update_conversation(
            conversation_id,
            {
                "stage": ConversationStage.RECOMMENDING,
                "current_task_id": task_id,
                "current_recipe_name": None,
                "updated_at": utc_now(),
            },
        )
        return conversation_repository.get_task(task_id) or {}

    def create_task_from_recipe(self, *, user_id: int, conversation_id: str, recipe_id: int) -> dict:
        lookup = recipe_catalog_service.get_recipe_by_id(
            recipe_id,
            include=["recipe", "tags", "ingredients", "steps"],
        )
        snapshot = build_task_recipe_snapshot_from_catalog(lookup)
        task_id = str(uuid4())
        conversation_repository.create_task(
            task_id=task_id,
            user_id=user_id,
            conversation_id=conversation_id,
            stage=ConversationStage.PREPARING,
            status=TaskStatus.ACTIVE,
            source_recipe_id=recipe_id,
            recipe_snapshot_json=dump_task_recipe_snapshot(snapshot),
        )
        conversation_repository.update_conversation(
            conversation_id,
            {
                "stage": ConversationStage.PREPARING,
                "current_task_id": task_id,
                "current_recipe_name": snapshot.name,
                "updated_at": utc_now(),
            },
        )
        return conversation_repository.get_task(task_id) or {}

    def overwrite_recipe_from_catalog(self, *, task_id: str, recipe_id: int) -> dict:
        lookup = recipe_catalog_service.get_recipe_by_id(
            recipe_id,
            include=["recipe", "tags", "ingredients", "steps"],
        )
        snapshot = build_task_recipe_snapshot_from_catalog(lookup)
        conversation_repository.update_task(
            task_id,
            {
                "source_recipe_id": recipe_id,
                "recipe_snapshot_json": snapshot.model_dump(mode="json"),
                "updated_at": utc_now(),
            },
        )
        return {"recipe_snapshot": snapshot, "source_recipe_id": recipe_id}

    def overwrite_recipe_from_generated(self, *, task_id: str, recipe_payload: dict) -> dict:
        snapshot = build_task_recipe_snapshot_from_generated(recipe_payload)
        conversation_repository.update_task(
            task_id,
            {
                "source_recipe_id": None,
                "recipe_snapshot_json": snapshot.model_dump(mode="json"),
                "updated_at": utc_now(),
            },
        )
        return {"recipe_snapshot": snapshot, "source_recipe_id": None}

    def patch_recipe(self, *, task_id: str, patch: dict, mode: str) -> dict:
        task = conversation_repository.get_task(task_id)
        if task is None:
            raise ValueError("当前任务不存在。")
        snapshot = load_task_recipe_snapshot(task.get("recipe_snapshot_json"))
        if snapshot is None:
            raise ValueError("当前任务还没有菜谱。")
        updated = apply_recipe_patch(snapshot, patch, mode=mode)
        conversation_repository.update_task(
            task_id,
            {
                "recipe_snapshot_json": updated.model_dump(mode="json"),
                "updated_at": utc_now(),
            },
        )
        return {"recipe_snapshot": updated, "source_recipe_id": task.get("source_recipe_id")}

    def transition_to_preparation(self, conversation_id: str) -> dict:
        task = self._require_current_task(conversation_id)
        snapshot = load_task_recipe_snapshot(task.get("recipe_snapshot_json"))
        ensure_can_enter_preparation(snapshot)
        conversation_repository.update_task(
            task["id"],
            {
                "stage": ConversationStage.PREPARING,
                "updated_at": utc_now(),
            },
        )
        conversation_repository.update_conversation(
            conversation_id,
            {
                "stage": ConversationStage.PREPARING,
                "current_recipe_name": snapshot.name if snapshot else None,
                "updated_at": utc_now(),
            },
        )
        return {"task": conversation_repository.get_task(task["id"]), "recipe_snapshot": snapshot}

    def transition_to_cooking(self, conversation_id: str) -> dict:
        task = self._require_current_task(conversation_id)
        snapshot = load_task_recipe_snapshot(task.get("recipe_snapshot_json"))
        ensure_can_enter_cooking(snapshot)
        conversation_repository.update_task(
            task["id"],
            {
                "stage": ConversationStage.COOKING,
                "updated_at": utc_now(),
            },
        )
        conversation_repository.update_conversation(
            conversation_id,
            {
                "stage": ConversationStage.COOKING,
                "current_recipe_name": snapshot.name if snapshot else None,
                "updated_at": utc_now(),
            },
        )
        return {"task": conversation_repository.get_task(task["id"]), "recipe_snapshot": snapshot}

    def rollback_to_recommendation(self, conversation_id: str) -> dict:
        task = self._require_current_task(conversation_id)
        snapshot = load_task_recipe_snapshot(task.get("recipe_snapshot_json"))
        conversation_repository.update_task(
            task["id"],
            {
                "stage": ConversationStage.RECOMMENDING,
                "updated_at": utc_now(),
            },
        )
        conversation_repository.update_conversation(
            conversation_id,
            {
                "stage": ConversationStage.RECOMMENDING,
                "current_recipe_name": snapshot.name if snapshot else None,
                "updated_at": utc_now(),
            },
        )
        return {"task": conversation_repository.get_task(task["id"]), "recipe_snapshot": snapshot}

    def rollback_to_preparation(self, conversation_id: str) -> dict:
        task = self._require_current_task(conversation_id)
        snapshot = load_task_recipe_snapshot(task.get("recipe_snapshot_json"))
        conversation_repository.update_task(
            task["id"],
            {
                "stage": ConversationStage.PREPARING,
                "updated_at": utc_now(),
            },
        )
        conversation_repository.update_conversation(
            conversation_id,
            {
                "stage": ConversationStage.PREPARING,
                "current_recipe_name": snapshot.name if snapshot else None,
                "updated_at": utc_now(),
            },
        )
        return {"task": conversation_repository.get_task(task["id"]), "recipe_snapshot": snapshot}

    def complete_task(self, conversation_id: str) -> dict:
        task = self._require_current_task(conversation_id)
        snapshot = load_task_recipe_snapshot(task.get("recipe_snapshot_json"))
        ensure_can_complete(snapshot)
        self._finish_task(
            conversation_id=conversation_id,
            task_id=task["id"],
            outcome=TaskOutcome.COMPLETED,
            record_in_history=True,
        )
        return {"recipe_snapshot": snapshot}

    def cancel_task(self, conversation_id: str, *, record_in_history: bool) -> dict:
        task = self._require_current_task(conversation_id)
        snapshot = load_task_recipe_snapshot(task.get("recipe_snapshot_json"))
        self._finish_task(
            conversation_id=conversation_id,
            task_id=task["id"],
            outcome=TaskOutcome.CANCELLED,
            record_in_history=record_in_history,
        )
        return {"recipe_snapshot": snapshot}

    def _finish_task(
        self,
        *,
        conversation_id: str,
        task_id: str,
        outcome: TaskOutcome,
        record_in_history: bool,
    ) -> None:
        now = utc_now()
        conversation_repository.update_task(
            task_id,
            {
                "status": TaskStatus.COMPLETED if outcome == TaskOutcome.COMPLETED else TaskStatus.CANCELLED,
                "outcome": outcome,
                "record_in_history": int(record_in_history),
                "ended_at": now,
                "updated_at": now,
            },
        )
        conversation_repository.update_conversation(
            conversation_id,
            {
                "stage": ConversationStage.IDLE,
                "current_task_id": None,
                "current_recipe_name": None,
                "updated_at": now,
            },
        )

    def _require_current_task(self, conversation_id: str) -> dict:
        task = conversation_repository.get_current_task(conversation_id)
        if task is None:
            raise ValueError("当前会话没有活动中的任务。")
        return task


task_service = TaskService()
