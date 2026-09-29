"""小红书取数（稳定性优先：快照兜底 + 公开页面解析，不破解登录/付费墙）。"""
from __future__ import annotations

import json
import re

import requests

from ..core.logging import get_logger

log = get_logger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    )
}


def resolve_note(link: str, timeout: int = 15) -> dict:
    """解析小红书笔记页，返回 {note_id, title, desc, image_list}；失败抛异常。"""
    session = requests.Session()
    session.headers.update(HEADERS)
    session.trust_env = False
    resp = session.get(link, timeout=timeout, allow_redirects=True)
    resp.raise_for_status()
    html = resp.text
    final_url = str(resp.url or "")

    note_id = ""
    m = re.search(r"/(?:explore|discovery/item|note)/([0-9a-f]{24})", final_url)
    if m:
        note_id = m.group(1)
    if not note_id:
        m = re.search(r'"noteId"\s*:\s*"([0-9a-f]{24})"', html)
        if m:
            note_id = m.group(1)

    title = desc = ""
    image_list: list[str] = []

    m = re.search(r"window\.__INITIAL_STATE__\s*=\s*(\{.*?\})\s*</script>", html, re.S)
    if m:
        try:
            state = json.loads(m.group(1))
            note = _find_note(state, note_id)
            if note:
                title = note.get("title") or ""
                desc = note.get("desc") or ""
                for img in note.get("imageList") or []:
                    url = img.get("urlDefault") or img.get("url") or ""
                    if url:
                        image_list.append(url)
        except Exception as e:  # noqa: BLE001
            log.warning("解析 __INITIAL_STATE__ 失败：%s", e)

    if not image_list:
        raise RuntimeError("未解析到图片列表（可能被登录墙/反爬拦截）")

    return {"note_id": note_id, "title": title, "desc": desc, "image_list": image_list}


def _find_note(state, note_id: str):
    def walk(obj):
        if isinstance(obj, dict):
            if isinstance(obj.get("noteDetailMap"), dict):
                nd = obj["noteDetailMap"]
                if note_id and note_id in nd:
                    item = nd[note_id]
                    return item.get("note") if isinstance(item, dict) else item
                for v in nd.values():
                    if isinstance(v, dict) and "note" in v:
                        return v["note"]
            for v in obj.values():
                r = walk(v)
                if r is not None:
                    return r
        elif isinstance(obj, list):
            for v in obj:
                r = walk(v)
                if r is not None:
                    return r
        return None

    return walk(state)
