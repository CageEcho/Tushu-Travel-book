"""ORM → Schema 序列化。"""
from __future__ import annotations

from .models import Place, Trip
from .schemas import Candidate, PlaceOut, TripOut


def serialize_place(p: Place) -> PlaceOut:
    cands = None
    if p.candidates:
        cands = [Candidate(**c) for c in p.candidates if isinstance(c, dict)]
    return PlaceOut(
        id=p.id,
        day=p.day,
        seq=p.seq,
        name=p.name,
        type=p.type,
        source_text=p.source_text,
        confirmed=p.confirmed,
        skipped=p.skipped,
        poi_name=p.poi_name,
        poi_uid=p.poi_uid,
        poi_address=p.poi_address,
        lat=p.lat,
        lng=p.lng,
        geocode_status=p.geocode_status,
        candidates=cands,
    )


def serialize_trip(t: Trip) -> TripOut:
    return TripOut(
        id=t.id,
        source_link=t.source_link,
        note_id=t.note_id,
        title=t.title,
        city=t.city,
        status=t.status,
        created_at=t.created_at,
    )
