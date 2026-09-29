"""推荐住宿：每天以当天最后一站为锚点，用百度地点检索按档次各挑一家酒店。

百度检索结果的价格字段基本为空，这里只用档次标签（classified_poi_tag）、评分和评价数，
不编造价格。结果按行程缓存到 data/assets/{trip_id}/hotels.json，地点坐标变化时重新检索。
"""
from __future__ import annotations

import hashlib
import json
import math
from types import SimpleNamespace

import httpx

from ..core.config import ASSETS_DIR, settings
from ..core.errors import AppError
from ..core.logging import get_logger
from . import nav as nav_svc
from . import pipeline
from .geocode import PLACE_SEARCH_URL, _ak

log = get_logger(__name__)

# (档位 key, 展示名, 百度档次标签)
TIERS = (
    ("budget", "经济实惠", ("经济型", "快捷酒店", "二星级")),
    ("comfort", "舒适品质", ("舒适型", "三星级")),
    ("premium", "高端享受", ("高档型", "豪华型", "四星级", "五星级")),
)
MIN_COMMENTS = 10  # 评价太少的评分不可靠，优先排除


def haversine_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    r = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def _grade(item: dict) -> str | None:
    info = item.get("detail_info") or {}
    tags = (info.get("classified_poi_tag") or info.get("tag") or "").split(";")
    for _, _, grades in TIERS:
        for g in grades:
            if g in tags:
                return g
    return None


def _num(v, cast=float) -> float:
    try:
        return cast(v)
    except (TypeError, ValueError):
        return 0


def pick_hotels(results: list[dict], anchor, src: str) -> list[dict]:
    """每个档位挑评分最高的一家（评价数不足时降级），去重 uid。纯函数，便于单测。"""
    out: list[dict] = []
    seen: set[str] = set()
    for tier, label, grades in TIERS:
        pool = []
        for it in results:
            loc = it.get("location") or {}
            if it.get("uid") in seen or loc.get("lat") is None or _grade(it) not in grades:
                continue
            info = it.get("detail_info") or {}
            rating = _num(info.get("overall_rating"))
            comments = int(_num(info.get("comment_num"), int))
            if rating <= 0:
                continue
            pool.append((comments >= MIN_COMMENTS, rating, comments, it))
        if not pool:
            continue
        _, rating, comments, it = max(pool, key=lambda x: x[:3])
        seen.add(it.get("uid"))
        lat, lng = it["location"]["lat"], it["location"]["lng"]
        point = SimpleNamespace(name=it.get("name"), lat=lat, lng=lng, poi_address=it.get("address"))
        out.append(
            {
                "tier": tier,
                "tier_label": label,
                "grade": _grade(it),
                "name": it.get("name"),
                "uid": it.get("uid"),
                "address": it.get("address"),
                "rating": rating,
                "comment_num": comments,
                "distance_m": round(haversine_m(anchor.lat, anchor.lng, lat, lng)),
                "lat": lat,
                "lng": lng,
                "link": {
                    "uri": nav_svc.build_marker_uri(point, src),
                    "web_uri": nav_svc.build_web_marker_uri(point, src),
                },
            }
        )
    return out


def _search(lat: float, lng: float, radius: int, page_num: int) -> list[dict]:
    r = httpx.get(
        PLACE_SEARCH_URL,
        params={
            "query": "酒店",
            "tag": "酒店",
            "location": f"{lat:.6f},{lng:.6f}",
            "radius": radius,
            "scope": 2,
            "filter": "industry_type:hotel|sort_name:overall_rating|sort_rule:0",
            "page_size": 20,
            "page_num": page_num,
            "output": "json",
            "ak": _ak(),
        },
        timeout=15,
        trust_env=False,
    )
    data = r.json()
    if data.get("status") != 0:
        raise AppError("BAIDU_ERROR", f"酒店检索失败：{data.get('message')}", status_code=502)
    return data.get("results") or []


def _signature(days: list) -> str:
    raw = json.dumps([[day, [[p.id, round(p.lat, 5), round(p.lng, 5)] for p in pts]] for day, pts in days])
    return hashlib.sha1(raw.encode()).hexdigest()[:12]


def _ordered_days(trip_id: str, points: list) -> list:
    """按已生成动线的顺序分天；还没有动线时按地点的天 / 序号。"""
    data = pipeline.load_route_json(trip_id)
    if data:
        by_id = {p.id: p for p in points}
        days = [(d["day"], [by_id[pid] for pid in d["place_ids"] if pid in by_id]) for d in data["days"]]
    else:
        grouped: dict[int, list] = {}
        for p in sorted(points, key=lambda p: (p.day, p.seq)):
            grouped.setdefault(p.day, []).append(p)
        days = sorted(grouped.items())
    return [(day, pts) for day, pts in days if pts]


def _recommend_near(anchor) -> list[dict]:
    results = _search(anchor.lat, anchor.lng, 3000, 0) + _search(anchor.lat, anchor.lng, 3000, 1)
    hotels = pick_hotels(results, anchor, settings.baidu_uri_src)
    if len(hotels) < len(TIERS):
        # 附近某个档位缺货时放宽范围再找一次
        hotels = pick_hotels(results + _search(anchor.lat, anchor.lng, 8000, 0), anchor, settings.baidu_uri_src)
    return hotels


def recommend(trip_id: str, places: list) -> dict:
    points = [p for p in places if not p.skipped and p.lat is not None and p.lng is not None]
    days = _ordered_days(trip_id, points)
    if not days:
        raise AppError("NO_POINTS", "暂无已定位的地点，无法推荐住宿", status_code=422)
    sig = _signature(days)
    cache = ASSETS_DIR / trip_id / "hotels.json"
    if cache.exists():
        try:
            data = json.loads(cache.read_text(encoding="utf-8"))
            if data.get("signature") == sig:
                return data
        except json.JSONDecodeError:
            pass

    out = []
    for day, pts in days:
        anchor = pts[-1]  # 当天最后一站：收尾后就近入住，不折返
        hotels = _recommend_near(anchor)
        log.info("推荐住宿 %s Day%d：锚点 %s，%d 家", trip_id, day, anchor.name, len(hotels))
        out.append({"day": day, "anchor": {"name": anchor.name, "lat": anchor.lat, "lng": anchor.lng}, "hotels": hotels})
    data = {"trip_id": trip_id, "signature": sig, "days": out}
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return data
