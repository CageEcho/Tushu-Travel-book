"""统一错误结构与业务异常。"""
from __future__ import annotations


class AppError(Exception):
    """业务异常：统一转成 {"error": {"code", "message"}}。"""

    def __init__(self, code: str, message: str, status_code: int = 400) -> None:
        self.code = code
        self.message = message
        self.status_code = status_code
        super().__init__(message)


def error_body(code: str, message: str) -> dict:
    return {"error": {"code": code, "message": message}}
