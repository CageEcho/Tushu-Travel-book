"""百度地图 App 唤起链接（途经点 viaPoints / 分段）纯函数测试。"""
import json
from types import SimpleNamespace
from urllib.parse import parse_qs, unquote, urlsplit

from app.services.nav import build_day_legs, build_day_segments, ll2mc

SRC = "webapp.tripflow.tripflow"


def _place(i, uid=True, lat=None, lng=None):
    return SimpleNamespace(
        name=f"景点{i}",
        lat=29.5 + i * 0.01 if lat is None else lat,
        lng=106.5 + i * 0.01 if lng is None else lng,
        poi_uid=f"uid{i}" if uid else None,
        poi_address=None,
    )


def _query(uri):
    return parse_qs(urlsplit(uri).query)


def _via(uri):
    raw = _query(uri).get("viaPoints")
    return json.loads(raw[0])["viaPoints"] if raw else []


def test_waypoints_use_viapoints_json():
    legs = build_day_legs([_place(i) for i in range(8)], "重庆", 15, SRC)
    assert len(legs) == 1
    uri = legs[0]["uri"]
    assert uri.startswith("baidumap://map/direction?")
    assert "viaPoints=" in uri and "&via=" not in uri
    via = _via(uri)
    assert [v["name"] for v in via] == [f"景点{i}" for i in range(1, 7)]
    assert via[0]["uid"] == "uid1"
    q = _query(uri)
    assert q["origin"] == ["name:景点0|latlng:29.500000,106.500000"]
    assert q["destination_uid"] == ["uid7"]
    assert q["mode"] == ["driving"] and q["coord_type"] == ["bd09ll"]
    assert q["region"] == ["重庆"] and q["src"] == [SRC]


def test_split_into_legs_when_over_limit():
    pts = [_place(i) for i in range(8)]
    legs = build_day_legs(pts, "重庆", 3, SRC)
    assert [(l["from_place"], l["to_place"], len(l["via"])) for l in legs] == [
        ("景点0", "景点4", 3),
        ("景点4", "景点7", 2),
    ]
    assert all(len(_via(l["uri"])) <= 3 for l in legs)


def test_exact_limit_is_single_leg():
    assert len(build_day_legs([_place(i) for i in range(17)], None, 15, SRC)) == 1
    legs = build_day_legs([_place(i) for i in range(18)], None, 15, SRC)
    assert len(legs) == 2 and legs[1]["from_place"] == "景点16" and legs[1]["via"] == []


def test_two_points_no_viapoints():
    uri = build_day_legs([_place(0), _place(1)], "重庆", 15, SRC)[0]["uri"]
    assert "viaPoints" not in uri


def test_single_point_uses_marker():
    legs = build_day_legs([_place(0)], "重庆", 15, SRC)
    assert legs[0]["uri"].startswith("baidumap://map/marker?")
    assert _query(legs[0]["uri"])["title"] == ["景点0"]


def test_missing_uid_omitted():
    uri = build_day_legs([_place(0, uid=False), _place(1, uid=False), _place(2, uid=False)], None, 15, SRC)[0]["uri"]
    q = _query(uri)
    assert "origin_uid" not in q and "destination_uid" not in q
    assert "uid" not in _via(uri)[0]


def test_special_chars_roundtrip():
    p = _place(1)
    p.name = "李子坝&轻轨|穿楼"
    uri = build_day_legs([_place(0), p, _place(2)], None, 15, SRC)[0]["uri"]
    assert _via(uri)[0]["name"] == "李子坝&轻轨|穿楼"
    assert "李子坝" not in uri  # 中文已编码
    assert unquote(uri).count("viaPoints") == 2  # 参数名 + JSON 键


def test_skip_no_coords_and_dedupe():
    pts = [_place(0), _place(1), _place(1), SimpleNamespace(name="无坐标", lat=None, lng=None, poi_uid=None), _place(2)]
    legs = build_day_legs(pts, None, 15, SRC)
    assert legs[0]["via"] == ["景点1"]
    assert build_day_legs([], None, 15, SRC) == []


def test_same_coords_different_names_kept():
    # 地理编码兜底到城市中心时多个景点坐标相同，不能被合并掉
    pts = [_place(0)] + [SimpleNamespace(name=n, lat=29.57, lng=106.55, poi_uid=None) for n in ("湖广会馆", "来福士", "洪崖洞")] + [_place(9)]
    assert build_day_legs(pts, None, 15, SRC)[0]["via"] == ["湖广会馆", "来福士", "洪崖洞"]


def test_ll2mc_matches_baidu():
    # 百度网页版返回的真实换算结果
    x, y = ll2mc(106.583439, 29.563326)
    assert abs(x - 11864943.26) < 0.05 and abs(y - 3426267.49) < 0.05


def test_web_uri_with_waypoints():
    legs = build_day_legs([_place(i) for i in range(5)], "重庆", 15, SRC)
    web = legs[0]["web_uri"]
    assert web.startswith("https://map.baidu.com/dir/")
    path = unquote(urlsplit(web).path)
    assert path.startswith("/dir/景点0/景点1/景点2/景点3/景点4/@")
    q = _query(web)
    assert q["sn"][0].startswith("1$$uid0$$") and q["sn"][0].endswith("$$景点0$$0$$$$")
    en = q["en"][0].split(" to:")
    assert len(en) == 4  # 3 个途经点 + 终点
    assert all(e.endswith("$$1$$") for e in en[:3]) and "$$景点4$$" in en[3]


def test_web_uri_escapes_slash_and_dollar():
    p = _place(1)
    p.name = "A/B$C"
    web = build_day_legs([_place(0), p, _place(2)], None, 15, SRC)[0]["web_uri"]
    assert unquote(urlsplit(web).path).startswith("/dir/景点0/A BC/景点2/@")  # "/" 变空格、"$" 去掉
    assert "$$A BC$$" in _query(web)["en"][0]


def test_web_basic_uri_origin_destination_only():
    legs = build_day_legs([_place(i) for i in range(5)], "重庆", 15, SRC)
    web = legs[0]["web_basic_uri"]
    assert web.startswith("https://api.map.baidu.com/direction?")
    q = _query(web)
    assert q["origin"] == ["name:景点0|latlng:29.500000,106.500000"]
    assert q["destination"] == ["name:景点4|latlng:29.540000,106.540000"]
    assert q["output"] == ["html"] and q["region"] == ["重庆"] and q["src"] == [SRC]


def test_web_uri_single_point_marker():
    web = build_day_legs([_place(0)], "重庆", 15, SRC)[0]["web_uri"]
    assert web.startswith("https://api.map.baidu.com/marker?")
    assert _query(web)["output"] == ["html"]


def test_segments_pairwise_all_modes():
    segs = build_day_segments([_place(i) for i in range(4)], "重庆", SRC)
    assert [(s["from_place"], s["to_place"]) for s in segs] == [("景点0", "景点1"), ("景点1", "景点2"), ("景点2", "景点3")]
    for mode in ("transit", "walking", "riding"):
        uri = segs[0][mode]["uri"]
        assert uri.startswith("baidumap://map/direction?") and "viaPoints" not in uri
        assert _query(uri)["mode"] == [mode]
        assert _query(uri)["origin_uid"] == ["uid0"] and _query(uri)["destination_uid"] == ["uid1"]


def test_segments_web_links():
    seg = build_day_segments([_place(0), _place(1)], "重庆", SRC)[0]
    for mode in ("transit", "walking"):
        web = seg[mode]["web_uri"]
        assert web.startswith("https://api.map.baidu.com/direction?") and _query(web)["mode"] == [mode]
    ride = seg["riding"]["web_uri"]  # 官方 Web URI 不支持骑行
    assert ride.startswith("https://map.baidu.com/dir/") and _query(ride)["querytype"] == ["cycle"]


def test_segments_need_two_points():
    assert build_day_segments([_place(0)], None, SRC) == []
    assert build_day_segments([], None, SRC) == []


def test_driving_leg_unchanged_by_mode_param():
    uri = build_day_legs([_place(i) for i in range(3)], None, 15, SRC)[0]["uri"]
    assert _query(uri)["mode"] == ["driving"] and "viaPoints=" in uri
    web = build_day_legs([_place(i) for i in range(3)], None, 15, SRC)[0]["web_uri"]
    assert _query(web)["querytype"] == ["nav"] and "route_traffic=1" in web
