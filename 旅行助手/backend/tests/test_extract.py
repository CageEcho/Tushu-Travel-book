"""地点抽取解析器纯函数测试。"""
from app.services.extract import parse_extraction


def test_parse_valid_json():
    out = parse_extraction('{"places":[{"day":1,"seq":1,"name":"解放碑","type":"景点"}]}')
    assert len(out) == 1
    assert out[0]["name"] == "解放碑"
    assert out[0]["day"] == 1


def test_parse_code_fence():
    content = '```json\n{"places":[{"day":1,"seq":1,"name":"解放碑","type":"景点"}]}\n```'
    assert parse_extraction(content)[0]["name"] == "解放碑"


def test_parse_extra_text_before_json():
    content = '以下是结果：{"places":[{"day":1,"seq":1,"name":"解放碑","type":"景点"}]}'
    assert len(parse_extraction(content)) == 1


def test_parse_garbage_returns_empty():
    assert parse_extraction("") == []
    assert parse_extraction("没有 JSON") == []
    assert parse_extraction("```json\n{broken") == []


def test_parse_skips_invalid_entries():
    content = '{"places":[{"day":1,"seq":1,"name":"解放碑"},{"day":1,"seq":2}]}'
    out = parse_extraction(content)
    assert len(out) == 1  # 缺 name 的条目被跳过


def test_parse_top_level_list():
    out = parse_extraction('[{"day":1,"seq":1,"name":"解放碑"}]')
    assert len(out) == 1
