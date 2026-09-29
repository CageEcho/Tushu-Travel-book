"""路线编排纯函数测试。"""
from app.services.route import fmt_duration


def test_fmt_duration():
    assert fmt_duration(30) == "30秒"
    assert fmt_duration(90) == "1分钟"
    assert fmt_duration(3600) == "1小时"
    assert fmt_duration(3700) == "1小时1分钟"
