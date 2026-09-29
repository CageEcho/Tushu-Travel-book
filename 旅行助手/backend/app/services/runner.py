"""后台任务执行器：线程 + DB 持久化状态（重启可恢复）。"""
from __future__ import annotations

import threading
import uuid

from sqlalchemy import update

from ..core.db import SessionLocal
from ..core.logging import get_logger
from ..models import Task, Trip

log = get_logger(__name__)


def start_task(trip_id: str, kind: str) -> str:
    """创建任务并启动后台线程，返回 task_id。"""
    db = SessionLocal()
    try:
        task = Task(id=str(uuid.uuid4()), trip_id=trip_id, kind=kind, status="pending", progress="排队中")
        db.add(task)
        db.commit()
        db.refresh(task)
        task_id = task.id
    finally:
        db.close()

    threading.Thread(target=_run, args=(task_id,), daemon=True).start()
    return task_id


def _run(task_id: str) -> None:
    from . import pipeline  # noqa: PLC0415

    db = SessionLocal()
    try:
        task = db.get(Task, task_id)
        if not task:
            return
        trip = db.get(Trip, task.trip_id)
        if not trip:
            return
        task.status = "running"
        if task.kind == "parse":
            trip.status = "parsing"
        elif task.kind == "route":
            trip.status = "routing"
        db.commit()

        if task.kind == "parse":
            pipeline.run_parse(db, trip, task)
        elif task.kind == "route":
            pipeline.run_route(db, trip, task)
        elif task.kind == "export":
            pipeline.run_export(db, trip, task)
        else:
            raise ValueError(f"未知任务类型 {task.kind}")

        task.status = "done"
        db.commit()
    except Exception as e:  # noqa: BLE001
        log.exception("任务失败 task=%s", task_id)
        try:
            task = db.get(Task, task_id)
            if task:
                task.status = "failed"
                task.error = str(e)[:500]
                trip = db.get(Trip, task.trip_id)
                if trip and trip.status in ("parsing", "routing"):
                    trip.status = "failed"
                db.commit()
        except Exception:  # noqa: BLE001
            pass
    finally:
        db.close()


def recover_stale_tasks() -> None:
    """启动时：把遗留 running/pending 任务置失败（可重新提交）。"""
    db = SessionLocal()
    try:
        db.execute(
            update(Task)
            .where(Task.status.in_(["running", "pending"]))
            .values(status="failed", error="服务重启，任务中断")
        )
        db.commit()
    finally:
        db.close()
