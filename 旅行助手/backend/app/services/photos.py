"""地点实景图：用百度百科词条卡片取首图，缩略图下载到本地缓存后由本服务提供。

百科图片禁止带外站 Referer 的外链（403），所以不让浏览器直连，而是后端下载一次存到
data/assets/{trip_id}/photos/{place_id}.jpg。同名词条可能是小说、歌曲或外地同名地点，
只接受简介里出现行程城市、且不是作品类词条的结果；首图若是标志 / 站牌这类白底图形也跳过。
找不到就不展示，不拿无关图片凑数。
"""
from __future__ import annotations

import hashlib
import json
import re
import io
import threading
from concurrent.futures import ThreadPoolExecutor

import httpx
from PIL import Image, UnidentifiedImageError

from ..core.config import ASSETS_DIR
from ..core.logging import get_logger

log = get_logger(__name__)

BAIKE_CARD_URL = "https://baike.baidu.com/api/openapi/BaikeLemmaCardApi"
BAIKE_APPID = 379020  # 百科词条卡片接口的公开 appid
# 词条名常见的景点后缀，依次尝试；"站"放最后（如李子坝轻轨站）
SUFFIXES = ("传统风貌区", "风景区", "景区", "站")
WORK_RE = re.compile(r"^《|小说|歌曲|单曲|专辑|电视剧|电影|游戏|综艺|漫画")
THUMB_PROCESS = "image/resize,m_lfit,w_720/format,f_jpg/quality,q_75"
MAX_BYTES = 2 * 1024 * 1024
# 近白像素占比超过该值视为标志 / 站牌等图形（实测：实景图 ≤0.24，标志 ≥0.74）
MAX_WHITE_RATIO = 0.5

_lock = threading.Lock()


def candidate_keys(name: str, poi_name: str | None, city: str | None) -> list[str]:
    city = city or ""
    keys = [f"{city}{name}", name]
    if poi_name:
        keys += [poi_name, f"{city}{poi_name}"]
    keys += [f"{name}{s}" for s in SUFFIXES]
    return [k for k in dict.fromkeys(keys) if k]


def accept(card: dict, city: str | None) -> bool:
    """有图、不是作品类词条、且（有城市时）标题或简介里提到该城市。"""
    abstract = card.get("abstract") or ""
    if not card.get("image") or WORK_RE.search(abstract[:40]):
        return False
    return not city or city in (card.get("title") or "") + abstract


def thumb_url(image: str) -> str:
    return image.split("?", 1)[0] + "?x-bce-process=" + THUMB_PROCESS


def _card(key: str) -> dict:
    try:
        r = httpx.get(
            BAIKE_CARD_URL,
            params={"bk_key": key, "appid": BAIKE_APPID, "scope": 103, "format": "json", "bk_length": 80},
            timeout=10,
            trust_env=False,
        )
        data = r.json()
        return data if isinstance(data, dict) else {}
    except (httpx.HTTPError, ValueError):
        return {}


def lookup(name: str, poi_name: str | None, city: str | None):
    """依次产出可用词条 {title, image, source_url}，调用方拿到合格图片即停。"""
    for key in candidate_keys(name, poi_name, city):
        card = _card(key)
        if accept(card, city):
            yield {"title": card.get("title"), "image": card["image"], "source_url": card.get("url")}


def white_ratio(img: Image.Image) -> float:
    small = img.convert("RGB").resize((64, 64))
    px = small.get_flattened_data() if hasattr(small, "get_flattened_data") else small.getdata()
    return sum(1 for r, g, b in px if r > 235 and g > 235 and b > 235) / (64 * 64)


def _fetch_photo(url: str) -> bytes | None:
    try:
        # 不带 Referer：百科图床对外站 Referer 返回 403
        r = httpx.get(url, timeout=15, trust_env=False, follow_redirects=True)
    except httpx.HTTPError:
        return None
    if r.status_code != 200 or not r.headers.get("content-type", "").startswith("image/") or len(r.content) > MAX_BYTES:
        return None
    try:
        if white_ratio(Image.open(io.BytesIO(r.content))) > MAX_WHITE_RATIO:
            return None
    except (UnidentifiedImageError, OSError):
        return None
    return r.content


def _place_key(p) -> str:
    return f"{p.name}|{p.poi_name or ''}"


def photo_path(trip_id: str, place_id: int):
    return ASSETS_DIR / trip_id / "photos" / f"{place_id}.jpg"


def _resolve(trip_id: str, p, city: str | None) -> dict:
    entry = {"key": _place_key(p), "found": False}
    for hit in lookup(p.name, p.poi_name, city):
        data = _fetch_photo(thumb_url(hit["image"]))
        if data:
            path = photo_path(trip_id, p.id)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
            entry.update(found=True, title=hit["title"], source_url=hit["source_url"])
            break
    return entry


def photos_for_trip(trip_id: str, places: list, city: str | None) -> dict:
    """返回 {place_id: {src, title, source_url}}；只查新增或改名 / 换 POI 的地点，结果（含未找到）缓存。"""
    cache = ASSETS_DIR / trip_id / "photos.json"
    with _lock:
        try:
            known = json.loads(cache.read_text(encoding="utf-8")) if cache.exists() else {}
        except json.JSONDecodeError:
            known = {}
        todo = [p for p in places if known.get(str(p.id), {}).get("key") != _place_key(p)]
        if todo:
            with ThreadPoolExecutor(max_workers=6) as pool:
                for p, entry in zip(todo, pool.map(lambda p: _resolve(trip_id, p, city), todo)):
                    known[str(p.id)] = entry
            cache.parent.mkdir(parents=True, exist_ok=True)
            cache.write_text(json.dumps(known, ensure_ascii=False), encoding="utf-8")
            log.info("地点实景图 %s：新查 %d 个，命中 %d 个", trip_id, len(todo), sum(known[str(p.id)]["found"] for p in todo))
    out = {}
    for p in places:
        entry = known.get(str(p.id))
        if entry and entry.get("found"):
            v = hashlib.sha1(entry["key"].encode()).hexdigest()[:8]
            out[str(p.id)] = {
                "src": f"/api/v1/trips/{trip_id}/photos/{p.id}.jpg?v={v}",
                "title": entry.get("title"),
                "source_url": entry.get("source_url"),
            }
    return out
