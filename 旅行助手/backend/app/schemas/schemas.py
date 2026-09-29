"""Pydantic 输入输出结构。"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class TripCreate(BaseModel):
    source_link: str = Field(min_length=1, max_length=2048)


class TripOut(BaseModel):
    id: str
    source_link: str
    note_id: str | None = None
    title: str | None = None
    city: str | None = None
    status: str
    created_at: Any = None


class TaskOut(BaseModel):
    id: str
    trip_id: str
    kind: str
    status: str
    progress: str | None = None
    error: str | None = None
    result_path: str | None = None


class Candidate(BaseModel):
    name: str
    uid: str | None = None
    address: str | None = None
    lat: float | None = None
    lng: float | None = None


class PlaceOut(BaseModel):
    id: int
    day: int
    seq: int
    name: str
    type: str
    source_text: str | None = None
    confirmed: bool
    skipped: bool
    poi_name: str | None = None
    poi_uid: str | None = None
    poi_address: str | None = None
    lat: float | None = None
    lng: float | None = None
    geocode_status: str
    candidates: list[Candidate] | None = None


class PlaceUpdate(BaseModel):
    name: str | None = None
    day: int | None = None
    seq: int | None = None
    type: str | None = None
    confirmed: bool | None = None
    skipped: bool | None = None
    poi_uid: str | None = None
    poi_name: str | None = None
    poi_address: str | None = None
    lat: float | None = None
    lng: float | None = None


class RouteSegment(BaseModel):
    from_place: str
    to_place: str
    mode: str
    distance_m: int
    duration_s: int
    duration_text: str


class RouteDay(BaseModel):
    day: int
    places: list[PlaceOut]
    segments: list[RouteSegment]
    map_url: str | None = None


class RouteOut(BaseModel):
    trip_id: str
    days: list[RouteDay]


class NavLeg(BaseModel):
    leg: int
    from_place: str
    to_place: str
    via: list[str]
    uri: str  # baidumap:// 唤起 App，含途经点
    web_uri: str  # 网页版 map.baidu.com，含途经点（非官方格式）
    web_basic_uri: str  # 网页版官方 URI，仅起终点（兑底）


class NavLink(BaseModel):
    uri: str  # baidumap:// 唤起 App
    web_uri: str  # 网页版


class NavSegment(BaseModel):
    """公交 / 步行 / 骑行逐段链接（百度这三种方式不支持途经点）。"""

    from_place: str
    to_place: str
    transit: NavLink
    walking: NavLink
    riding: NavLink


class NavDay(BaseModel):
    day: int
    legs: list[NavLeg]  # 驾车，含途经点
    segments: list[NavSegment]


class AppNavOut(BaseModel):
    max_via: int
    uris: list[str]  # 所有段按天、按段展开，兼容旧调用
    days: list[NavDay]


class ShareOut(BaseModel):
    trip: TripOut
    places: list[PlaceOut]
    route: RouteOut | None = None
