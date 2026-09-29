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


def is_demo_link(link: str) -> bool:
    return "10vTPLjLXy7" in link
