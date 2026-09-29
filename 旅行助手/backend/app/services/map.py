"""百度地图静态图（长图/网页地图渲染用，服务端 AK 即可）。"""
from __future__ import annotations

import httpx

from ..core.config import settings
from ..core.errors import AppError

STATIC_IMAGE_URL = "https://api.map.baidu.com/staticimage/v2"


def _ak() -> str:
    if not settings.baidu_map_ak:
        raise AppError("NO_MAP_AK", "未配置百度地图 AK", status_code=503)
    return settings.baidu_map_ak


def build_static_map_png(places: list[dict], width: int = 640, height: int = 400) -> bytes:
    """places: [{lat, lng}]，按顺序画标记点 + 连线，返回 PNG bytes。"""
    pts = [(p["lng"], p["lat"]) for p in places if p.get("lng") is not None and p.get("lat") is not None]
    if not pts:
        raise AppError("NO_POINTS", "无坐标可绘制", status_code=422)

    markers = "|".join(f"{lng:.6f},{lat:.6f}" for lng, lat in pts)
    path = ";".join(f"{lng:.6f},{lat:.6f}" for lng, lat in pts)
    clng = sum(x for x, _ in pts) / len(pts)
    clat = sum(y for _, y in pts) / len(pts)

    r = httpx.get(
        STATIC_IMAGE_URL,
        params={
            "ak": _ak(),
            "width": width,
            "height": height,
            "center": f"{clng:.6f},{clat:.6f}",
            "zoom": 13,
            "markers": markers,
            "path": path,
        },
        timeout=20,
        trust_env=False,
    )
    if r.status_code != 200 or not r.content.startswith(b"\x89PNG"):
        raise AppError("MAP_RENDER_FAILED", f"静态地图生成失败（HTTP {r.status_code}）", status_code=502)
    return r.content
