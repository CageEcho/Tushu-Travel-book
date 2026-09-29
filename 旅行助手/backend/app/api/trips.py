"""行程相关 API。"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse, Response
from sqlalchemy.orm import Session

from ..core.config import settings
from ..core.db import get_db
from ..core.errors import AppError
from ..models import Place, Task, Trip
from ..schemas import AppNavOut, NavDay, NavLeg, NavSegment, PlaceUpdate, TripCreate
from ..serializers import serialize_place, serialize_trip
from ..services import hotels as hotels_svc
from ..services import map as map_svc
from ..services import nav as nav_svc
from ..services import photos as photos_svc
from ..services import pipeline, runner

router = APIRouter(prefix="/trips", tags=["trips"])


def _trip_or_404(db: Session, trip_id: str) -> Trip:
    trip = db.get(Trip, trip_id)
    if not trip:
        raise AppError("NOT_FOUND", "行程不存在", status_code=404)
    return trip


@router.post("", status_code=201)
def create_trip(body: TripCreate, db: Session = Depends(get_db)):
    trip = Trip(id=uuid.uuid4().hex[:8], source_link=body.source_link, status="created")
    db.add(trip)
    db.commit()
    db.refresh(trip)
    task_id = runner.start_task(trip.id, "parse")
    return {"trip_id": trip.id, "task_id": task_id}


@router.get("/{trip_id}")
def get_trip(trip_id: str, db: Session = Depends(get_db)):
    trip = _trip_or_404(db, trip_id)
    return serialize_trip(trip)


@router.get("/{trip_id}/places")
def get_places(trip_id: str, db: Session = Depends(get_db)):
    trip = _trip_or_404(db, trip_id)
    places = sorted(trip.places, key=lambda p: (p.day, p.seq))
    return {
        "trip_id": trip.id,
        "status": trip.status,
        "title": trip.title,
        "city": trip.city,
        "places": [serialize_place(p) for p in places],
    }


@router.patch("/{trip_id}/places/{place_id}")
def update_place(trip_id: str, place_id: int, body: PlaceUpdate, db: Session = Depends(get_db)):
    trip = _trip_or_404(db, trip_id)
    if trip.status != "awaiting_confirm":
        raise AppError("INVALID_STATE", f"当前状态不可编辑（{trip.status}）", status_code=409)
    place = db.get(Place, place_id)
    if not place or place.trip_id != trip_id:
        raise AppError("NOT_FOUND", "地点不存在", status_code=404)
    data = body.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(place, k, v)
    if (body.lat is not None and body.lng is not None) or body.poi_uid:
        place.geocode_status = "ok"
    db.commit()
    db.refresh(place)
    return serialize_place(place)


@router.post("/{trip_id}/route")
def create_route(trip_id: str, db: Session = Depends(get_db)):
    trip = _trip_or_404(db, trip_id)
    pipeline.validate_route_ready(trip.status, trip.places)
    task_id = runner.start_task(trip.id, "route")
    return {"trip_id": trip.id, "task_id": task_id}


@router.get("/{trip_id}/route")
def get_route(trip_id: str, db: Session = Depends(get_db)):
    trip = _trip_or_404(db, trip_id)
    data = pipeline.load_route_json(trip_id)
    if not data:
        raise AppError("NO_ROUTE", "尚未生成动线", status_code=404)
    place_by_id = {p.id: p for p in trip.places}
    days = []
    for d in data["days"]:
        places = [serialize_place(place_by_id[pid]) for pid in d["place_ids"] if pid in place_by_id]
        days.append(
            {
                "day": d["day"],
                "places": places,
                "segments": d["segments"],
                "map_url": f"/api/v1/trips/{trip_id}/map?day={d['day']}",
            }
        )
    return {"trip_id": trip_id, "days": days}


@router.get("/{trip_id}/map")
def get_map(trip_id: str, day: int | None = None, db: Session = Depends(get_db)):
    trip = _trip_or_404(db, trip_id)
    places = [p for p in trip.places if not p.skipped and p.lat is not None and p.lng is not None]
    if day is not None:
        places = [p for p in places if p.day == day]
    places.sort(key=lambda p: (p.day, p.seq))
    if not places:
        raise AppError("NO_POINTS", "无坐标可绘制", status_code=422)
    png = map_svc.build_static_map_png([{"lat": p.lat, "lng": p.lng} for p in places])
    return Response(content=png, media_type="image/png")


@router.get("/{trip_id}/app-nav")
def get_app_nav(trip_id: str, db: Session = Depends(get_db)):
    """唤起百度地图：驾车按天/按段带途经点；公交/步行/骑行逐段。顺序以已生成的动线为准。"""
    trip = _trip_or_404(db, trip_id)
    usable = [p for p in trip.places if not p.skipped and p.lat is not None and p.lng is not None]
    data = pipeline.load_route_json(trip_id)
    if data:
        place_by_id = {p.id: p for p in usable}
        ordered = [(d["day"], [place_by_id[pid] for pid in d["place_ids"] if pid in place_by_id]) for d in data["days"]]
    else:
        by_day: dict[int, list] = {}
        for p in sorted(usable, key=lambda p: (p.day, p.seq)):
            by_day.setdefault(p.day, []).append(p)
        ordered = sorted(by_day.items())
    max_via = settings.baidu_nav_max_via
    days = []
    for day, plist in ordered:
        legs = nav_svc.build_day_legs(plist, trip.city, max_via, settings.baidu_uri_src)
        segments = nav_svc.build_day_segments(plist, trip.city, settings.baidu_uri_src)
        if legs:
            days.append(
                NavDay(
                    day=day,
                    legs=[NavLeg(**leg) for leg in legs],
                    segments=[NavSegment(**s) for s in segments],
                )
            )
    uris = [leg.uri for d in days for leg in d.legs]
    return AppNavOut(max_via=max_via, uris=uris, days=days)


@router.get("/{trip_id}/hotels")
def get_hotels(trip_id: str, db: Session = Depends(get_db)):
    """推荐住宿：每天最后一站附近按经济 / 舒适 / 高端各一家，数据来自百度地点检索。"""
    trip = _trip_or_404(db, trip_id)
    return hotels_svc.recommend(trip_id, trip.places)


@router.get("/{trip_id}/photos")
def get_photos(trip_id: str, db: Session = Depends(get_db)):
    """地点实景图（百度百科词条首图）；没找到可靠图片的地点不返回。"""
    trip = _trip_or_404(db, trip_id)
    return {"trip_id": trip_id, "photos": photos_svc.photos_for_trip(trip_id, trip.places, trip.city)}


@router.get("/{trip_id}/photos/{place_id}.jpg")
def get_photo_file(trip_id: str, place_id: int, db: Session = Depends(get_db)):
    _trip_or_404(db, trip_id)
    path = photos_svc.photo_path(trip_id, place_id)
    if not path.exists():
        raise AppError("NO_PHOTO", "该地点暂无图片", status_code=404)
    return FileResponse(path, media_type="image/jpeg", headers={"Cache-Control": "public, max-age=86400"})


@router.post("/{trip_id}/export")
def create_export(trip_id: str, db: Session = Depends(get_db)):
    trip = _trip_or_404(db, trip_id)
    if not pipeline.load_route_json(trip_id):
        raise AppError("NO_ROUTE", "请先生成动线", status_code=409)
    task_id = runner.start_task(trip.id, "export")
    return {"trip_id": trip.id, "task_id": task_id}


@router.get("/{trip_id}/export.png")
def get_export_file(trip_id: str, db: Session = Depends(get_db)):
    _trip_or_404(db, trip_id)
    task = (
        db.query(Task)
        .filter(Task.trip_id == trip_id, Task.kind == "export", Task.status == "done", Task.result_path.isnot(None))
        .order_by(Task.created_at.desc())
        .first()
    )
    if not task:
        raise AppError("NO_EXPORT", "尚未生成长图", status_code=404)
    return FileResponse(task.result_path, media_type="image/png", filename=f"trip-{trip_id}.png")
