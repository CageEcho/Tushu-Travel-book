"""图片 OCR：本地 PaddleOCR 为主；不可用时返回 None，由调用方用快照兜底。"""
from __future__ import annotations

from ..core.logging import get_logger

log = get_logger(__name__)

_paddle = None


def _get_paddle():
    global _paddle
    if _paddle is None:
        try:
            from paddleocr import PaddleOCR  # noqa: PLC0415

            _paddle = PaddleOCR(use_angle_cls=True, lang="ch", show_log=False)
            log.info("PaddleOCR 已加载")
        except Exception as e:  # noqa: BLE001
            log.warning("PaddleOCR 不可用（将用快照兜底）：%s", e)
            _paddle = False
    return _paddle


def ocr_images(image_urls: list[str], timeout: int = 20) -> str | None:
    """下载图片并 OCR，返回合并文本；PaddleOCR 不可用时返回 None。"""
    paddle = _get_paddle()
    if paddle is False:
        return None

    import requests
    from PIL import Image
    from io import BytesIO

    texts: list[str] = []
    for url in image_urls:
        try:
            r = requests.get(url, timeout=timeout, headers={"User-Agent": "Mozilla/5.0"})
            r.raise_for_status()
            img = Image.open(BytesIO(r.content)).convert("RGB")
            result = paddle.ocr(img, cls=True)
            line_texts = []
            if result:
                for group in result:
                    for line in group or []:
                        if line and len(line) >= 2:
                            line_texts.append(str(line[1][0]))
            texts.append("\n".join(line_texts))
        except Exception as e:  # noqa: BLE001
            log.warning("OCR 图片失败：%s", e)

    merged = "\n".join(t for t in texts if t.strip())
    return merged if merged.strip() else None
