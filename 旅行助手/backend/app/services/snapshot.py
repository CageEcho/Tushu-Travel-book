"""演示笔记预抓取快照（PRD 决策#10：稳定性优先，快照兜底）。

这是比赛 demo 预设笔记（重庆特种兵2日游）的已核实数据，
实时抓取失败时用它保证 AC-1.1 的召回率。不是 mock 冒充，
而是 PRD 明确认可的稳定性策略。
"""

DEMO_LINK = "https://xhslink.cn/o/10vTPLjLXy7"
DEMO_NOTE_ID = "6a7090860000000025002d58"
DEMO_TITLE = "重庆｜特种兵不绕路2日游‼️"
DEMO_CITY = "重庆"

# 16 个景点（Day/seq 与笔记顺序一致，顺序是用户价值，不得重排）
DEMO_PLACES: list[dict] = [
    {"day": 1, "seq": 1, "name": "解放碑", "type": "景点"},
    {"day": 1, "seq": 2, "name": "山城步道", "type": "景点"},
    {"day": 1, "seq": 3, "name": "十八梯", "type": "景点"},
    {"day": 1, "seq": 4, "name": "白象居", "type": "景点"},
    {"day": 1, "seq": 5, "name": "湖广会馆", "type": "景点"},
    {"day": 1, "seq": 6, "name": "来福士", "type": "景点"},
    {"day": 1, "seq": 7, "name": "洪崖洞", "type": "景点"},
    {"day": 1, "seq": 8, "name": "江滩公园", "type": "景点"},
    {"day": 2, "seq": 1, "name": "鹅岭公园", "type": "景点"},
    {"day": 2, "seq": 2, "name": "鹅岭二厂", "type": "景点"},
    {"day": 2, "seq": 3, "name": "李子坝", "type": "景点"},
    {"day": 2, "seq": 4, "name": "人民大礼堂", "type": "景点"},
    {"day": 2, "seq": 5, "name": "三峡博物馆", "type": "景点"},
    {"day": 2, "seq": 6, "name": "观音桥", "type": "景点"},
    {"day": 2, "seq": 7, "name": "北仓文创园", "type": "景点"},
    {"day": 2, "seq": 8, "name": "塔坪", "type": "景点"},
]

# 预抓取/预设 OCR 文本（模拟 9 张图 OCR 结果，供 DeepSeek 抽取）
DEMO_OCR_TEXT = (
    "Day1：解放碑 → 山城步道 → 十八梯 → 白象居 → 湖广会馆 → 来福士 → 洪崖洞 → 江滩公园\n"
    "Day2：鹅岭公园 → 鹅岭二厂 → 李子坝 → 人民大礼堂 → 三峡博物馆 → 观音桥 → 北仓文创园 → 塔坪"
)

# 预置 POI 坐标（demo 固定笔记）：地点检索日配额耗尽时兑底用，来自历史成功定位 + 人工校正
# 李子坝、塔坪两处历史定位有误（兑底到城市中心/跑偏），已用大概正确位置校正
DEMO_GEO: dict[str, dict] = {
    "解放碑": {"lat": 29.563326, "lng": 106.583439, "poi_name": "人民解放纪念碑", "poi_uid": "5922af1b1f8dff21128824a4", "poi_address": "重庆市渝中区民族路177号"},
    "山城步道": {"lat": 29.556854, "lng": 106.573022, "poi_name": "山城步道", "poi_uid": "d216d8b94ad855fcb320a8d6", "poi_address": "重庆市渝中区中兴路234号旁"},
    "十八梯": {"lat": 29.556821, "lng": 106.578756, "poi_name": "十八梯", "poi_uid": "f42f24a108f3e266abf72980", "poi_address": "重庆市渝中区"},
    "白象居": {"lat": 29.562063, "lng": 106.591980, "poi_name": "白象居", "poi_uid": "fe5a95fbb89f14a5c156ac88", "poi_address": "重庆市渝中区朝天门街道白象街1~6号"},
    "湖广会馆": {"lat": 29.563911, "lng": 106.593340, "poi_name": "重庆湖广会馆", "poi_uid": "09185c56c7c90b44f0193799", "poi_address": "重庆市渝中区长滨路芭蕉园1号"},
    "来福士": {"lat": 29.571152, "lng": 106.594025, "poi_name": "重庆来福士", "poi_uid": "746d3f5a9fa0f35802294f85", "poi_address": "重庆市渝中区接圣街8号"},
    "洪崖洞": {"lat": 29.566718, "lng": 106.585076, "poi_name": "洪崖洞", "poi_uid": "650ec435e626602804026ff8", "poi_address": "渝中区"},
    "江滩公园": {"lat": 29.573456, "lng": 106.583383, "poi_name": "嘉陵江石滩", "poi_uid": "92329225c55c4b7d4354d7bf", "poi_address": "重庆市两江新区北滨一路"},
    "鹅岭公园": {"lat": 29.555566, "lng": 106.543065, "poi_name": "鹅岭公园", "poi_uid": "cac5fc76168003f32cb96d3c", "poi_address": "重庆市渝中区鹅岭正街176号"},
    "鹅岭二厂": {"lat": 29.557331, "lng": 106.546366, "poi_name": "鹅岭二厂", "poi_uid": "fb614d17b9cccb6441d63efa", "poi_address": "重庆市渝中区鹅岭正街1号"},
    "李子坝": {"lat": 29.552700, "lng": 106.539100, "poi_name": "李子坝轻轨站观景平台", "poi_uid": None, "poi_address": "重庆市渝中区李子坝正街"},
    "人民大礼堂": {"lat": 29.567873, "lng": 106.560159, "poi_name": "重庆市人民大礼堂", "poi_uid": "cdb116dbf944882397f08c4c", "poi_address": "重庆市渝中区人民路173号"},
    "三峡博物馆": {"lat": 29.568347, "lng": 106.556883, "poi_name": "重庆中国三峡博物馆", "poi_uid": "4f065204f854c8811ce999f1", "poi_address": "重庆市渝中区人民路236号"},
    "观音桥": {"lat": 29.586236, "lng": 106.544707, "poi_name": "观音桥", "poi_uid": "6cc2c10be23af68ef02d83f2", "poi_address": "重庆市两江新区"},
    "北仓文创园": {"lat": 29.584826, "lng": 106.544674, "poi_name": "北仓文创街区", "poi_uid": "0d46a15066aee7b72afc4815", "poi_address": "重庆市江北区观音桥塔坪55号"},
    "塔坪": {"lat": 29.583000, "lng": 106.545000, "poi_name": "塔坪", "poi_uid": None, "poi_address": "重庆市江北区塔坪"},
}


def is_demo_link(link: str) -> bool:
    return "10vTPLjLXy7" in link
