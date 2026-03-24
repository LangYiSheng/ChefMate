from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

from app.core.semantic_models import ConversationStage, SemanticQuery, TaskSnapshot, TaskStatus, WorkflowResult


@dataclass
class TaskState:
    id: str
    conversation_id: str
    current_node: str
    stage: ConversationStage
    status: TaskStatus
    semantic_query: SemanticQuery


class InMemoryTaskManager:
    def __init__(self) -> None:
        self._conversations: dict[str, dict[str, str | None]] = {}
        self._tasks: dict[str, TaskState] = {}

    def create_conversation(self, user_id: str, title: str | None) -> dict[str, str]:
        conversation_id = str(uuid4())
        self._conversations[conversation_id] = {
            "id": conversation_id,
            "user_id": user_id,
            "title": title or "新建对话",
        }
        return {
            "id": conversation_id,
            "title": self._conversations[conversation_id]["title"] or "新建对话",
        }

    def create_or_resume_task(self, conversation_id: str, user_input: str) -> TaskState:
        for task in self._tasks.values():
            if task.conversation_id == conversation_id and task.status != TaskStatus.COMPLETED:
                if task.status == TaskStatus.SUSPENDED:
                    task.status = TaskStatus.RUNNING
                    task.stage = ConversationStage.GENERAL
                return task

        task_id = str(uuid4())
        task = TaskState(
            id=task_id,
            conversation_id=conversation_id,
            current_node="entry",
            stage=ConversationStage.GENERAL,
            status=TaskStatus.RUNNING,
            semantic_query=SemanticQuery(raw_text=user_input),
        )
        self._tasks[task_id] = task
        return task

    def update_task_from_result(self, task_id: str, result: WorkflowResult) -> None:
        task = self._tasks[task_id]
        task.stage = result.next_stage
        task.status = result.status
        task.current_node = result.next_stage.value.lower()
        task.semantic_query = result.semantic_query

    def get_task_snapshot(self, task_id: str) -> TaskSnapshot | None:
        task = self._tasks.get(task_id)
        if task is None:
            return None
        return TaskSnapshot(
            id=task.id,
            conversation_id=task.conversation_id,
            stage=task.stage,
            status=task.status,
            current_node=task.current_node,
            semantic_query=task.semantic_query,
        )

    def resume_task(self, task_id: str) -> TaskSnapshot | None:
        task = self._tasks.get(task_id)
        if task is None:
            return None
        task.status = TaskStatus.RUNNING
        if task.stage == ConversationStage.SUSPENDED:
            task.stage = ConversationStage.GENERAL
        return self.get_task_snapshot(task_id)


task_manager = InMemoryTaskManager()
