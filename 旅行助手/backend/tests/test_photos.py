"""地点实景图纯函数测试。"""
from PIL import Image

from app.services.photos import MAX_WHITE_RATIO, accept, candidate_keys, thumb_url, white_ratio


def test_candidate_keys_city_first_and_deduped():
    keys = candidate_keys("十八梯", "十八梯", "重庆")
    assert keys[:3] == ["重庆十八梯", "十八梯", "十八梯传统风貌区"]
    assert keys[-1] == "十八梯站"
    assert len(keys) == len(set(keys))


def test_accept_rejects_works_and_other_cities():
    img = "https://bkimg.cdn.bcebos.com/pic/x?x-bce-process=image/format,f_auto"
    assert accept({"image": img, "title": "白象居", "abstract": "白象居位于重庆市渝中区"}, "重庆")
    assert not accept({"image": img, "title": "十八梯", "abstract": "《十八梯》是王雨创作的小说集"}, "重庆")
    assert not accept({"image": img, "title": "李子坝", "abstract": "《李子坝》是张可儿演唱的歌曲，重庆"}, "重庆")
    assert not accept({"image": img, "title": "江滩公园", "abstract": "位于四川省成都市高新区"}, "重庆")
    assert not accept({"title": "白象居", "abstract": "重庆"}, "重庆")


def test_thumb_url_replaces_process():
    assert thumb_url("https://bkimg.cdn.bcebos.com/pic/abc?x-bce-process=image/format,f_auto") == (
        "https://bkimg.cdn.bcebos.com/pic/abc?x-bce-process=image/resize,m_lfit,w_720/format,f_jpg/quality,q_75"
    )


def test_white_ratio_flags_logo_like_images():
    logo = Image.new("RGB", (100, 100), "white")
    logo.paste((200, 150, 60), (40, 40, 60, 60))
    photo = Image.new("RGB", (100, 100), (90, 120, 150))
    assert white_ratio(logo) > MAX_WHITE_RATIO
    assert white_ratio(photo) < MAX_WHITE_RATIO
