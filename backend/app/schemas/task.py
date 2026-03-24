from pydantic import BaseModel

from app.core.semantic_models import TaskSnapshot


class TaskResumeResponse(BaseModel):
    task: TaskSnapshot
    message: str
