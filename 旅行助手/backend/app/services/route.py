"""百度地图路线编排。"""
from __future__ import annotations

import httpx
import time

from ..core.config import settings
from ..core.errors import AppError
from ..core.logging import get_logger

log = get_logger(__name__)

# 限速：路线规划 QPS 上限很低（约 3~5），串行调用也要保持最小间隔，避免触发并发预警
_last_call = 0.0
_MIN_INTERVAL = 1.0  # 秒，约 1 QPS；账号并发配额极低，留足安全余量


def _throttle() -> None:
    global _last_call
    now = time.monotonic()
    wait = _last_call + _MIN_INTERVAL - now
    if wait > 0:
        time.sleep(wait)
    _last_call = time.monotonic()


_DIRECTION = {
    "driving": "https://api.map.baidu.com/direction/v2/driving",
    "walking": "https://api.map.baidu.com/direction/v2/walking",
    "riding": "https://api.map.baidu.com/direction/v2/riding",
    "transit": "https://api.map.baidu.com/direction/v2/transit",
}


def _ak() -> str:
    if not settings.baidu_map_ak:
        raise AppError("NO_MAP_AK", "未配置百度地图 AK", status_code=503)
    return settings.baidu_map_ak


def _direction(mode: str, origin: str, destination: str) -> dict:
    _throttle()
    r = httpx.get(
        _DIRECTION[mode],
        params={
            "origin": origin,
            "destination": destination,
            "ak": _ak(),
            "coord_type": "bd09ll",
            "output": "json",
        },
        timeout=15,
        trust_env=False,
    )
    data = r.json()
    if data.get("status") != 0:
        raise AppError("BAIDU_ERROR", f"路线规划失败：{data.get('message')}", status_code=502)
    routes = (data.get("result") or {}).get("routes") or []
    if not routes:
        raise AppError("NO_ROUTE", "无可用路线", status_code=502)
    route = routes[0]
    return {
        "distance_m": int(route.get("distance", 0)),
        "duration_s": int(route.get("duration", 0)),
    }


def plan_segment(origin_latlng: str, dest_latlng: str) -> dict:
    """单段：先驾车测距，短于 1km 建议步行。返回 {mode, distance_m, duration_s}。"""
    driving = _direction("driving", origin_latlng, dest_latlng)
    if driving["distance_m"] < 1000:
        try:
            w = _direction("walking", origin_latlng, dest_latlng)
            return {**w, "mode": "步行"}
        except AppError:
            pass
    return {**driving, "mode": "驾车"}


def fmt_duration(seconds: int) -> str:
    if seconds < 60:
        return f"{seconds}秒"
    if seconds < 3600:
        return f"{seconds // 60}分钟"
    h = seconds // 3600
    m = seconds % 3600 // 60
    if m == 0:
        return f"{h}小时"
    return f"{h}小时{m}分钟"
