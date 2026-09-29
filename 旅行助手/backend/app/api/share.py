"""分享（只读）API。"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..core.db import get_db
from ..core.errors import AppError
from ..models import Trip
from ..serializers import serialize_place, serialize_trip
from ..services import pipeline

router = APIRouter(prefix="/share", tags=["share"])


@router.get("/{trip_id}")
def share_view(trip_id: str, db: Session = Depends(get_db)):
    trip = db.get(Trip, trip_id)
    if not trip:
        raise AppError("NOT_FOUND", "分享不存在或已失效", status_code=404)
    places = sorted(trip.places, key=lambda p: (p.day, p.seq))
    route = None
    data = pipeline.load_route_json(trip_id)
    if data:
        place_by_id = {p.id: p for p in trip.places}
        days = []
        for d in data["days"]:
            days.append(
                {
                    "day": d["day"],
                    "places": [serialize_place(place_by_id[pid]) for pid in d["place_ids"] if pid in place_by_id],
                    "segments": d["segments"],
                    "map_url": f"/api/v1/trips/{trip_id}/map?day={d['day']}",
                }
            )
        route = {"trip_id": trip_id, "days": days}
    return {
        "trip": serialize_trip(trip),
        "places": [serialize_place(p) for p in places],
        "route": route,
    }
