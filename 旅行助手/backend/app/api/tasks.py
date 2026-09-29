"""任务轮询 API。"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..core.db import get_db
from ..core.errors import AppError
from ..models import Task
from ..schemas import TaskOut

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("/{task_id}")
def get_task(task_id: str, db: Session = Depends(get_db)):
    task = db.get(Task, task_id)
    if not task:
        raise AppError("NOT_FOUND", "任务不存在", status_code=404)
    return TaskOut(
        id=task.id,
        trip_id=task.trip_id,
        kind=task.kind,
        status=task.status,
        progress=task.progress,
        error=task.error,
        result_path=task.result_path,
    )
