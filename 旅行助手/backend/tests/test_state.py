"""状态机与「确认前不生成动线」确定性校验测试。"""
from types import SimpleNamespace

import pytest

from app.core.errors import AppError
from app.services.pipeline import validate_route_ready


def _place(name, lat=1.0, lng=1.0, skipped=False):
    return SimpleNamespace(name=name, lat=lat, lng=lng, skipped=skipped)


def test_not_ready_when_parsing():
    with pytest.raises(AppError) as e:
        validate_route_ready("parsing", [_place("解放碑")])
    assert e.value.code == "INVALID_STATE"


def test_incomplete_places_blocked():
    places = [_place("解放碑"), _place("洪崖洞", lat=None, lng=None)]
    with pytest.raises(AppError) as e:
        validate_route_ready("awaiting_confirm", places)
    assert e.value.code == "INCOMPLETE_PLACES"
    assert "洪崖洞" in e.value.message


def test_empty_blocked():
    with pytest.raises(AppError) as e:
        validate_route_ready("awaiting_confirm", [])
    assert e.value.code == "EMPTY"


def test_ready_when_all_geocoded():
    validate_route_ready("awaiting_confirm", [_place("解放碑"), _place("洪崖洞")])  # 不抛异常


def test_skipped_places_ignored():
    places = [_place("解放碑"), _place("洪崖洞", lat=None, lng=None, skipped=True)]
    validate_route_ready("awaiting_confirm", places)  # 跳过的缺坐标点不阻塞
