from fastapi import APIRouter, HTTPException

from app.core.task_manager import task_manager
from app.schemas.task import TaskResumeResponse

router = APIRouter()


@router.get("/{task_id}")
def get_task(task_id: str):
    snapshot = task_manager.get_task_snapshot(task_id)
    if snapshot is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return snapshot


@router.post("/{task_id}/resume", response_model=TaskResumeResponse)
def resume_task(task_id: str) -> TaskResumeResponse:
    snapshot = task_manager.resume_task(task_id)
    if snapshot is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return TaskResumeResponse(task=snapshot, message="Task resumed")
