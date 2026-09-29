"""SQLAlchemy 数据模型：Trip / Place / Task。"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..core.db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Trip(Base):
    __tablename__ = "trips"

    id: Mapped[str] = mapped_column(String(16), primary_key=True)  # 短码，兼分享码
    source_link: Mapped[str] = mapped_column(Text)
    note_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    title: Mapped[str | None] = mapped_column(String(256), nullable=True)
    city: Mapped[str | None] = mapped_column(String(32), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="created", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    places: Mapped[list["Place"]] = relationship(back_populates="trip", cascade="all, delete-orphan")
    tasks: Mapped[list["Task"]] = relationship(back_populates="trip", cascade="all, delete-orphan")


class Place(Base):
    __tablename__ = "places"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    trip_id: Mapped[str] = mapped_column(String(16), ForeignKey("trips.id"), index=True)
    day: Mapped[int] = mapped_column(Integer, default=1)
    seq: Mapped[int] = mapped_column(Integer, default=0)
    name: Mapped[str] = mapped_column(String(128))
    type: Mapped[str] = mapped_column(String(32), default="景点")
    source_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    confirmed: Mapped[bool] = mapped_column(Boolean, default=False)
    skipped: Mapped[bool] = mapped_column(Boolean, default=False)
    poi_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    poi_uid: Mapped[str | None] = mapped_column(String(64), nullable=True)
    poi_address: Mapped[str | None] = mapped_column(String(256), nullable=True)
    lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    lng: Mapped[float | None] = mapped_column(Float, nullable=True)
    geocode_status: Mapped[str] = mapped_column(String(32), default="pending")  # pending/ok/failed
    candidates: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    trip: Mapped["Trip"] = relationship(back_populates="places")


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    trip_id: Mapped[str] = mapped_column(String(16), ForeignKey("trips.id"), index=True)
    kind: Mapped[str] = mapped_column(String(32))  # parse/route/export
    status: Mapped[str] = mapped_column(String(32), default="pending")  # pending/running/done/failed
    progress: Mapped[str | None] = mapped_column(String(256), nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    result_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    trip: Mapped["Trip"] = relationship(back_populates="tasks")
