"""百度地图 App 唤起链接（含途经点 viaPoints）。

格式依据百度 URI API（Android / iOS 一致）：
- 路线规划 baidumap://map/direction：origin/destination 写成 name:xx|latlng:纬度,经度，
  途经点用 viaPoints，值为 {"viaPoints":[{name,lat,lng,uid}]} 的 JSON 再整体 URL 编码。
- 单点 baidumap://map/marker。
一段途经点超过上限时拆成多段，前一段终点即下一段起点。纯函数，便于单测。
"""
from __future__ import annotations

import json
from urllib.parse import quote

DIRECTION_URI = "baidumap://map/direction"
MARKER_URI = "baidumap://map/marker"
# 网页版（电脑端）：
# - map.baidu.com/dir 路线页支持途经点，但格式非官方公开（从网页版分享链接反推），可能随百度改版失效；
# - 官方 Web 端 URI api.map.baidu.com/direction 稳定，但只含起终点，作兜底。
WEB_ROUTE_URI = "https://map.baidu.com/dir"
WEB_DIRECTION_URI = "https://api.map.baidu.com/direction"
WEB_MARKER_URI = "https://api.map.baidu.com/marker"

# bd09ll → bd09mc（百度墨卡托）分段多项式系数，取自百度 JSAPI
_LLBAND = (75, 60, 45, 30, 15, 0)
_LL2MC = (
    (-0.0015702102444, 111320.7020616939, 1704480524535203, -10338987376042340, 26112667856603880,
     -35149669176653700, 26595700718403920, -10725012454188240, 1800819912950474, 82.5),
    (0.0008277824516172526, 111320.7020463578, 647795574.6671607, -4082003173.641316, 10774905663.51142,
     -15171875531.51559, 12053065338.62167, -5124939663.577472, 913311935.9512032, 67.5),
    (0.00337398766765, 111320.7020202162, 4481351.045890365, -23393751.19931662, 79682215.47186455,
     -115964993.2797253, 97236711.15602145, -43661946.33752821, 8477230.501135234, 52.5),
    (0.00220636496208, 111320.7020209128, 51751.86112841131, 3796837.749470245, 992013.7397791013,
     -1221952.21711287, 1340652.697009075, -620943.6990984312, 144416.9293806241, 37.5),
    (-0.0003441963504368392, 111320.7020576856, 278.2353980772752, 2485758.690035394, 6070.750963243378,
     54821.18345352118, 9540.606633304236, -2710.55326746645, 1405.483844121726, 22.5),
    (-0.0003218135878613132, 111320.7020701615, 0.00369383431289, 823725.6402795718, 0.46104986909093,
     2351.343141331292, 1.58060784298199, 8.77738589078284, 0.37238884252424, 7.45),
)


def ll2mc(lng: float, lat: float) -> tuple[float, float]:
    lat = max(min(lat, 74.0), -74.0)
    c = next(_LL2MC[i] for i, band in enumerate(_LLBAND) if abs(lat) >= band)
    x = c[0] + c[1] * abs(lng)
    cc = abs(lat) / c[9]
    y = sum(c[2 + k] * cc**k for k in range(7))
    return (x if lng >= 0 else -x), (y if lat >= 0 else -y)


def _endpoint(p) -> str:
    return quote(f"name:{p.name}|latlng:{p.lat:.6f},{p.lng:.6f}", safe=":|,.")


def _via_json(points) -> str:
    items = []
    for p in points:
        it = {"name": p.name, "lat": round(p.lat, 6), "lng": round(p.lng, 6)}
        if getattr(p, "poi_uid", None):
            it["uid"] = p.poi_uid
        items.append(it)
    return json.dumps({"viaPoints": items}, ensure_ascii=False, separators=(",", ":"))


def build_direction_uri(points, city: str | None, src: str, mode: str = "driving") -> str:
    """points ≥ 2：首为起点、末为终点、中间为途经点（仅驾车带途经点）。"""
    a, b, via = points[0], points[-1], points[1:-1]
    q = [f"origin={_endpoint(a)}"]
    if getattr(a, "poi_uid", None):
        q.append(f"origin_uid={quote(a.poi_uid, safe='')}")
    q.append(f"destination={_endpoint(b)}")
    if getattr(b, "poi_uid", None):
        q.append(f"destination_uid={quote(b.poi_uid, safe='')}")
    if via and mode == "driving":  # viaPoints 仅驾车生效
        q.append(f"viaPoints={quote(_via_json(via), safe='')}")
    q.append(f"mode={mode}")
    q.append("coord_type=bd09ll")
    if city:
        q.append(f"region={quote(city, safe='')}")
    q.append(f"src={quote(src, safe='.')}")
    return f"{DIRECTION_URI}?{'&'.join(q)}"


def build_marker_uri(p, src: str) -> str:
    q = [
        f"location={p.lat:.6f},{p.lng:.6f}",
        f"title={quote(p.name, safe='')}",
        f"content={quote(getattr(p, 'poi_address', None) or p.name, safe='')}",
        "coord_type=bd09ll",
        f"src={quote(src, safe='.')}",
    ]
    return f"{MARKER_URI}?{'&'.join(q)}"


def _web_name(p) -> str:
    # 名称进路径和 $$ 分隔字段，去掉会破坏格式的字符
    return p.name.replace("/", " ").replace("$", "")


def _web_point(p, via: bool = False) -> str:
    x, y = ll2mc(p.lng, p.lat)
    uid = (getattr(p, "poi_uid", None) or "").replace("$", "")
    s = f"1$${uid}$${x:.2f},{y:.2f}$${_web_name(p)}$$0$$$$"
    return s + "$$1$$" if via else s


_WEB_DIR_EXTRA = {
    "nav": ("mrs=0", "version=4", "route_traffic=1", "sy=0"),  # 驾车
    "cycle": ("version=6", "vehicle=0", "spath_type=1"),  # 骑行
}


def build_web_route_uri(points, querytype: str = "nav") -> str:
    """网页版路线。points ≥ 2；仅驾车（nav）识别途经点。"""
    a, b, via = points[0], points[-1], points[1:-1]
    path = "/".join(quote(_web_name(p), safe="") for p in points)
    mcs = [ll2mc(p.lng, p.lat) for p in points]
    cx = sum(x for x, _ in mcs) / len(mcs)
    cy = sum(y for _, y in mcs) / len(mcs)
    en = " to:".join([_web_point(p, via=True) for p in via] + [_web_point(b)])
    q = [
        f"querytype={querytype}",
        f"sn={quote(_web_point(a), safe='$,')}",
        f"en={quote(en, safe='$,:')}",
        "pn=0",
        "rn=5",
        *_WEB_DIR_EXTRA[querytype],
        "da_src=shareurl",
    ]
    return f"{WEB_ROUTE_URI}/{path}/@{cx:.2f},{cy:.2f},14z?{'&'.join(q)}"


def build_web_direction_uri(a, b, city: str | None, src: str, mode: str = "driving") -> str:
    """官方 Web 端 URI，mode 支持 driving / transit / walking（不支持骑行）。"""
    q = [
        f"origin={_endpoint(a)}",
        f"destination={_endpoint(b)}",
        f"mode={mode}",
        "coord_type=bd09ll",
    ]
    if city:
        q.append(f"region={quote(city, safe='')}")
    q += ["output=html", f"src={quote(src, safe='.')}"]
    return f"{WEB_DIRECTION_URI}?{'&'.join(q)}"


def build_web_marker_uri(p, src: str) -> str:
    q = [
        f"location={p.lat:.6f},{p.lng:.6f}",
        f"title={quote(p.name, safe='')}",
        f"content={quote(getattr(p, 'poi_address', None) or p.name, safe='')}",
        "coord_type=bd09ll",
        "output=html",
        f"src={quote(src, safe='.')}",
    ]
    return f"{WEB_MARKER_URI}?{'&'.join(q)}"


def _dedupe(points) -> list:
    """只合并相邻的同名同坐标点；不同名但坐标相同（多为地理编码兜底到城市中心）照常保留。"""
    out = []
    for p in points:
        q = out[-1] if out else None
        if q and q.name == p.name and round(q.lat, 6) == round(p.lat, 6) and round(q.lng, 6) == round(p.lng, 6):
            continue
        out.append(p)
    return out


def _usable(points) -> list:
    return _dedupe([p for p in points if p.lat is not None and p.lng is not None])


def build_day_segments(points, city: str | None, src: str) -> list[dict]:
    """公交 / 步行 / 骑行：百度不支持途经点，按相邻两点逐段给链接。
    [{from_place, to_place, transit|walking|riding: {uri, web_uri}}]"""
    pts = _usable(points)
    out = []
    for a, b in zip(pts, pts[1:]):
        out.append(
            {
                "from_place": a.name,
                "to_place": b.name,
                "transit": {
                    "uri": build_direction_uri([a, b], city, src, mode="transit"),
                    "web_uri": build_web_direction_uri(a, b, city, src, mode="transit"),
                },
                "walking": {
                    "uri": build_direction_uri([a, b], city, src, mode="walking"),
                    "web_uri": build_web_direction_uri(a, b, city, src, mode="walking"),
                },
                "riding": {
                    "uri": build_direction_uri([a, b], city, src, mode="riding"),
                    # 官方 Web URI 不支持骑行，走网页版 dir 路线页
                    "web_uri": build_web_route_uri([a, b], querytype="cycle"),
                },
            }
        )
    return out


def build_day_legs(points, city: str | None, max_via: int, src: str) -> list[dict]:
    """驾车：一天的有序地点 → 分段链接 [{leg, from_place, to_place, via, uri, web_uri, web_basic_uri}]。"""
    pts = _usable(points)
    if not pts:
        return []
    if len(pts) == 1:
        p = pts[0]
        return [
            {
                "leg": 1,
                "from_place": p.name,
                "to_place": p.name,
                "via": [],
                "uri": build_marker_uri(p, src),
                "web_uri": build_web_marker_uri(p, src),
                "web_basic_uri": build_web_marker_uri(p, src),
            }
        ]
    max_via = max(int(max_via), 0)
    legs = []
    i = 0
    while i < len(pts) - 1:
        chunk = pts[i : i + max_via + 2]
        legs.append(
            {
                "leg": len(legs) + 1,
                "from_place": chunk[0].name,
                "to_place": chunk[-1].name,
                "via": [p.name for p in chunk[1:-1]],
                "uri": build_direction_uri(chunk, city, src),
                "web_uri": build_web_route_uri(chunk),
                "web_basic_uri": build_web_direction_uri(chunk[0], chunk[-1], city, src),
            }
        )
        i += len(chunk) - 1
    return legs
