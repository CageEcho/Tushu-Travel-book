"""解析与路线编排流水线（后台执行，状态持久化）。"""
from __future__ import annotations

import json

from ..core.config import ASSETS_DIR
from ..core.errors import AppError
from ..core.logging import get_logger
from ..models import Place, Task, Trip
from . import geocode, ocr, route, snapshot, xhs
from .extract import extract_places

log = get_logger(__name__)

CITIES = ("北京", "上海", "广州", "深圳", "重庆", "成都")


def run_parse(db, trip: Trip, task: Task) -> None:
    link = trip.source_link
    title = city = ocr_text = None
    note_id = None

    if snapshot.is_demo_link(link):
        note_id = snapshot.DEMO_NOTE_ID
        title = snapshot.DEMO_TITLE
        city = snapshot.DEMO_CITY
        ocr_text = snapshot.DEMO_OCR_TEXT
        task.progress = "使用预抓取快照"
        db.commit()
        try:
            note = xhs.resolve_note(link)
            note_id = note["note_id"] or note_id
            title = note["title"] or title
            task.progress = "实时抓取成功，正在 OCR"
            db.commit()
            live_ocr = ocr.ocr_images(note["image_list"])
            if live_ocr:
                ocr_text = live_ocr
        except Exception as e:  # noqa: BLE001
            log.info("实时抓取/OCR 不可用，用快照兜底：%s", e)
    else:
        note = xhs.resolve_note(link)
        note_id = note["note_id"]
        title = note["title"]
        task.progress = "抓取成功，正在 OCR"
        db.commit()
        live_ocr = ocr.ocr_images(note["image_list"])
        if not live_ocr:
            raise AppError("OCR_UNAVAILABLE", "OCR 不可用且非 demo 链接，无快照可兜底", status_code=422)
        ocr_text = live_ocr
        city = _guess_city(f"{note['title']} {note['desc']}") or "重庆"

    trip.note_id = note_id
    trip.title = title
    trip.city = city

    task.progress = "DeepSeek 抽取地点"
    db.commit()
    places, _meta = extract_places(city, ocr_text)
    if not places and snapshot.is_demo_link(link):
        log.warning("抽取结果为空，回退快照地点")
        places = [dict(p) for p in snapshot.DEMO_PLACES]
    if not places:
        raise AppError("EXTRACT_EMPTY", "未抽取到地点", status_code=422)

    task.progress = "百度地图地理编码"
    db.commit()
    objs: list[Place] = []
    for p in places:
        poi, cands = geocode.geocode_place(p["name"], city)
        place = Place(
            trip_id=trip.id,
            day=int(p["day"]),
            seq=int(p["seq"]),
            name=p["name"],
            type=p.get("type", "景点"),
            confirmed=False,
            candidates=cands or None,
        )
        if poi:
            place.poi_name = poi.get("name")
            place.poi_uid = poi.get("uid")
            place.poi_address = poi.get("address")
            place.lat = poi.get("lat")
            place.lng = poi.get("lng")
            place.geocode_status = "ok"
        else:
            place.geocode_status = "failed"
        objs.append(place)
    db.add_all(objs)
    trip.status = "awaiting_confirm"
    db.commit()
    log.info("解析完成 trip=%s places=%s", trip.id, len(objs))


def run_route(db, trip: Trip, task: Task) -> None:
    places = sorted(
        (p for p in trip.places if not p.skipped and p.lat and p.lng),
        key=lambda p: (p.day, p.seq),
    )
    days: dict[int, list[Place]] = {}
    for p in places:
        days.setdefault(p.day, []).append(p)

    result_days = []
    for day in sorted(days):
        plist = days[day]
        plist.sort(key=lambda p: p.seq)
        segments = []
        for i in range(len(plist) - 1):
            a, b = plist[i], plist[i + 1]
            seg = route.plan_segment(f"{a.lat:.6f},{a.lng:.6f}", f"{b.lat:.6f},{b.lng:.6f}")
            segments.append(
                {
                    "from_place": a.name,
                    "to_place": b.name,
                    "mode": seg["mode"],
                    "distance_m": seg["distance_m"],
                    "duration_s": seg["duration_s"],
                    "duration_text": route.fmt_duration(seg["duration_s"]),
                }
            )
            task.progress = f"路线编排 Day{day} {i + 1}/{max(len(plist) - 1, 1)}"
            db.commit()
        result_days.append({"day": day, "place_ids": [p.id for p in plist], "segments": segments})

    payload = {"schema_version": 1, "trip_id": trip.id, "days": result_days}
    path = ASSETS_DIR / trip.id / "route.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    trip.status = "done"
    task.result_path = str(path)
    db.commit()


def run_export(db, trip: Trip, task: Task) -> None:
    from . import export  # noqa: PLC0415

    route_data = load_route_json(trip.id)
    if not route_data:
        raise AppError("NO_ROUTE", "请先生成动线", status_code=409)
    place_by_id = {p.id: p for p in trip.places}
    task.progress = "渲染长图"
    db.commit()
    path = export.export_long_image(trip, route_data["days"], place_by_id)
    task.result_path = path


def load_route_json(trip_id: str) -> dict | None:
    path = ASSETS_DIR / trip_id / "route.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def validate_route_ready(status: str, places) -> None:
    """生成动线前的确定性校验（确认前不生成动线）。纯函数，便于单测。"""
    if status not in ("awaiting_confirm", "done"):
        raise AppError("INVALID_STATE", f"当前状态不可生成动线（{status}）", status_code=409)
    active = [p for p in places if not p.skipped]
    incomplete = [p.name for p in active if p.lat is None or p.lng is None]
    if incomplete:
        raise AppError("INCOMPLETE_PLACES", f"以下地点缺少坐标，请先处理或跳过：{'、'.join(incomplete)}", status_code=409)
    if not active:
        raise AppError("EMPTY", "没有可生成动线的地点", status_code=409)


def _guess_city(text: str) -> str | None:
    for c in CITIES:
        if c in text:
            return c
    return None
