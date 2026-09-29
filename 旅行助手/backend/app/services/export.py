"""长图导出：无头浏览器整页合成 ≥2x 高清 PNG（FR-1.8 高审美）。"""
from __future__ import annotations

import base64

from ..core.config import ASSETS_DIR
from ..core.errors import AppError
from ..core.logging import get_logger
from . import map as map_svc

log = get_logger(__name__)


def render_export_html(trip, days: list[dict], place_by_id: dict) -> str:
    """生成设计稿级排版 HTML（封面 + 逐天动线 + 地点卡片 + 交通耗时）。"""
    sections = []
    for d in days:
        pts = []
        for pid in d["place_ids"]:
            p = place_by_id.get(pid)
            if p and p.lat and p.lng:
                pts.append({"lat": p.lat, "lng": p.lng})
        img = ""
        if pts:
            png = map_svc.build_static_map_png(pts, width=640, height=400)
            img = f'<img class="map" src="data:image/png;base64,{base64.b64encode(png).decode()}"/>'
        cards = "".join(_card(place_by_id[pid]) for pid in d["place_ids"] if pid in place_by_id)
        segs = "".join(_seg(s) for s in d["segments"])
        sections.append(
            f'<section class="day"><h2>Day {d["day"]}</h2>{img}<div class="cards">{cards}</div>'
            f'<div class="segs">{segs}</div></section>'
        )

    title = (trip.title or "旅行动线")[:60]
    return f"""<!doctype html>
<html><head><meta charset="utf-8"><style>
*{{margin:0;padding:0;box-sizing:border-box;}}
body{{font-family:-apple-system,"PingFang SC","Microsoft YaHei",sans-serif;background:#f5f6f8;color:#1f2329;width:750px;}}
header{{background:linear-gradient(135deg,#3d6bff,#6a3dff);color:#fff;padding:48px 40px;}}
header h1{{font-size:30px;line-height:1.4;}}
header .meta{{margin-top:12px;font-size:15px;opacity:.9;}}
.day{{background:#fff;margin:20px;border-radius:16px;overflow:hidden;box-shadow:0 2px 12px rgba(0,0,0,.06);}}
.day h2{{font-size:22px;padding:20px 24px 0;}}
.map{{width:100%;display:block;margin:16px 0 0;}}
.cards{{padding:8px 24px;}}
.card{{display:flex;align-items:center;padding:10px 0;border-bottom:1px solid #f0f1f3;}}
.card:last-child{{border-bottom:none;}}
.card .idx{{width:24px;height:24px;border-radius:50%;background:#eef1ff;color:#3d6bff;font-size:13px;display:flex;align-items:center;justify-content:center;flex-shrink:0;}}
.card .info{{margin-left:12px;}}
.card .name{{font-size:16px;font-weight:600;}}
.card .addr{{font-size:12px;color:#8a919f;margin-top:2px;}}
.segs{{padding:8px 24px 24px;font-size:13px;color:#4e5969;}}
.seg{{display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px dashed #e5e6eb;}}
.seg:last-child{{border-bottom:none;}}
</style></head>
<body><header><h1>{title}</h1><div class="meta">城市：{trip.city or "-"}　·　共 {sum(len(d["place_ids"]) for d in days)} 个地点</div></header>
{''.join(sections)}
</body></html>"""


def _card(p) -> str:
    addr = p.poi_address or ""
    return (
        f'<div class="card"><div class="idx">{p.seq}</div>'
        f'<div class="info"><div class="name">{p.name}</div>'
        f'<div class="addr">{addr}</div></div></div>'
    )


def _seg(s) -> str:
    return (
        f'<div class="seg"><span>{s["from_place"]} → {s["to_place"]}</span>'
        f'<span>{s["mode"]} · {s["duration_text"]}</span></div>'
    )


def export_long_image(trip, days: list[dict], place_by_id: dict) -> str:
    html = render_export_html(trip, days, place_by_id)
    try:
        from playwright.sync_api import sync_playwright  # noqa: PLC0415
    except ImportError as e:  # noqa: BLE001
        raise AppError("EXPORT_UNAVAILABLE", "Playwright 未安装，长图导出不可用", status_code=503) from e

    out = ASSETS_DIR / trip.id / f"export-{trip.id}.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 750, "height": 1200}, device_scale_factor=2)
        page.set_content(html)
        page.screenshot(path=str(out), full_page=True)
        browser.close()
    return str(out)
