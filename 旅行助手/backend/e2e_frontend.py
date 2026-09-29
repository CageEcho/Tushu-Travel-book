"""前端完整闭环 E2E（Playwright，走真实后端）。"""
import time

from playwright.sync_api import sync_playwright

FRONT = "http://localhost:5173/"


def main():
    with sync_playwright() as p:
        b = p.chromium.launch()
        page = b.new_page(viewport={"width": 1280, "height": 900})
        errors = []
        page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
        page.on("pageerror", lambda e: errors.append(str(e)))

        page.goto(FRONT, wait_until="networkidle")
        print("① 打开首页 OK")

        page.click("text=试试这篇重庆攻略")
        print("② 已点演示链接，等待解析…")
        page.wait_for_selector("text=确认并生成动线", timeout=90000)
        print("③ 地点确认加载完成")
        print("   Day1 可见:", page.is_visible("text=Day 1"))
        print("   Day2 可见:", page.is_visible("text=Day 2"))

        # 测试编辑：勾选跳过第一个地点
        page.locator("input[type=checkbox]").first.click()
        page.wait_for_selector("text=已跳过", timeout=10000)
        page.wait_for_timeout(800)
        print("④ 已勾选跳过第一个地点（已跳过徽章出现）")

        page.click("text=确认并生成动线")
        print("⑤ 已点生成动线，等待路线…")
        page.wait_for_selector("text=动线结果", timeout=120000)
        print("⑥ 动线结果加载完成")

        maps = page.query_selector_all("img[alt=动线地图]")
        print("   地图图片数量:", len(maps))

        page.once("dialog", lambda d: (print("   分享弹窗:", d.message[:60]), d.accept()))
        page.click("text=分享")
        page.wait_for_timeout(500)
        print("⑦ 分享 OK")

        page.click("text=导出长图")
        page.wait_for_timeout(4000)
        print("⑧ 导出已触发（后台合成长图）")

        page.screenshot(path="../docs/evidence/阶段3/04-完整闭环.png", full_page=True)
        print("console 错误:", errors if errors else "无")
        b.close()
        print("E2E DONE")


if __name__ == "__main__":
    main()
