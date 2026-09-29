"""FastAPI 入口。"""
from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .api import share, tasks, trips
from .core.config import FRONTEND_DIST, ensure_dirs
from .core.db import Base, engine
from .core.errors import AppError, error_body
from .core.logging import get_logger, setup_logging
from .services import runner

setup_logging()
log = get_logger(__name__)
ensure_dirs()
Base.metadata.create_all(engine)
runner.recover_stale_tasks()

app = FastAPI(title="TripFlow 旅行全流程助手", version="0.1.0")

app.include_router(trips.router, prefix="/api/v1")
app.include_router(tasks.router, prefix="/api/v1")
app.include_router(share.router, prefix="/api/v1")


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError):
    return JSONResponse(status_code=exc.status_code, content=error_body(exc.code, exc.message))


@app.exception_handler(RequestValidationError)
async def validation_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(status_code=422, content=error_body("VALIDATION", "请求参数校验失败"))


@app.exception_handler(Exception)
async def unhandled_handler(request: Request, exc: Exception):
    log.exception("未处理异常 %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content=error_body("INTERNAL", "服务器内部错误"))


@app.middleware("http")
async def no_cache_html(request: Request, call_next):
    response = await call_next(request)
    if not request.url.path.startswith(("/assets", "/api")):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    return response


if FRONTEND_DIST.exists():
    _index_path = FRONTEND_DIST / "index.html"
    app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIST / "assets")), name="assets")
else:
    _index_path = Path(os.path.dirname(__file__)) / "static" / "index.html"


@app.get("/{full_path:path}", include_in_schema=False)
async def spa_fallback(full_path: str):
    if full_path.startswith("api/") or full_path.startswith("assets/"):
        return JSONResponse(status_code=404, content=error_body("NOT_FOUND", "资源不存在"))
    return FileResponse(str(_index_path))
