"""演示快照数据完整性测试。"""
from app.services import snapshot


def test_16_places():
    assert len(snapshot.DEMO_PLACES) == 16


def test_day_grouping_and_seq():
    day1 = [p for p in snapshot.DEMO_PLACES if p["day"] == 1]
    day2 = [p for p in snapshot.DEMO_PLACES if p["day"] == 2]
    assert len(day1) == 8
    assert len(day2) == 8
    assert [p["seq"] for p in day1] == list(range(1, 9))
    assert [p["seq"] for p in day2] == list(range(1, 9))


def test_order_is_preserved():
    day1_names = [p["name"] for p in snapshot.DEMO_PLACES if p["day"] == 1]
    assert day1_names[0] == "解放碑"
    assert day1_names[-1] == "江滩公园"
    day2_names = [p["name"] for p in snapshot.DEMO_PLACES if p["day"] == 2]
    assert day2_names[2] == "李子坝"


def test_is_demo_link():
    assert snapshot.is_demo_link("https://xhslink.cn/o/10vTPLjLXy7")
    assert not snapshot.is_demo_link("https://xhslink.cn/o/somethingelse")
