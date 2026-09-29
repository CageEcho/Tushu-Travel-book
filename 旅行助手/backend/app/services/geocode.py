"""百度地图地理编码 / 消歧。"""
from __future__ import annotations

import httpx

from ..core.config import settings
from ..core.errors import AppError
from ..core.logging import get_logger

log = get_logger(__name__)

PLACE_SEARCH_URL = "https://api.map.baidu.com/place/v2/search"
GEOCODE_URL = "https://api.map.baidu.com/geocoding/v3"


def _ak() -> str:
    if not settings.baidu_map_ak:
        raise AppError("NO_MAP_AK", "未配置百度地图 AK", status_code=503)
    return settings.baidu_map_ak


def search_candidates(query: str, region: str, page_size: int = 5) -> list[dict]:
    """地点检索，返回候选 [{name, uid, address, lat, lng}]。"""
    r = httpx.get(
        PLACE_SEARCH_URL,
        params={
            "query": query,
            "region": region,
            "output": "json",
            "ak": _ak(),
            "page_size": page_size,
            "scope": 2,
        },
        timeout=15,
        trust_env=False,
    )
    data = r.json()
    if data.get("status") != 0:
        raise AppError("BAIDU_ERROR", f"地点检索失败：{data.get('message')}", status_code=502)
    out: list[dict] = []
    for it in data.get("results") or []:
        loc = it.get("location") or {}
        out.append(
            {
                "name": it.get("name"),
                "uid": it.get("uid"),
                "address": it.get("address"),
                "lat": loc.get("lat"),
                "lng": loc.get("lng"),
            }
        )
    return out


def geocode_place(name: str, city: str) -> tuple[dict | None, list[dict]]:
    """返回 (首选 POI, 候选列表)。首选为 None 表示失败。"""
    cands: list[dict] = []
    try:
        cands = search_candidates(name, city)
    except AppError as e:
        log.warning("地点检索失败 %s：%s", name, e)
    if cands:
        top = dict(cands[0])
        top["name"] = top.get("name") or name
        return top, cands
    # 兜底：地址转坐标
    r = httpx.get(
        GEOCODE_URL,
        params={"address": f"{city}{name}", "output": "json", "ak": _ak()},
        timeout=15,
        trust_env=False,
    )
    data = r.json()
    if data.get("status") == 0 and data.get("result"):
        loc = data["result"]["location"]
        return {"name": name, "uid": None, "address": city, "lat": loc["lat"], "lng": loc["lng"]}, []
    return None, []
