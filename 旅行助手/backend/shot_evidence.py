"""用 Playwright 走一遍验收界面并截图（证据包用）。"""
from playwright.sync_api import sync_playwright

DEMO = "https://xhslink.cn/o/10vTPLjLXy7"
OUT = "../docs/evidence/阶段2/"


def main():
    with sync_playwright() as p:
        b = p.chromium.launch()
        page = b.new_page(viewport={"width": 900, "height": 900})
        page.goto("http://127.0.0.1:8000/", wait_until="networkidle")
        page.fill("#link", DEMO)
        page.click("#btnGo")
        page.wait_for_selector("#placesCard", state="visible", timeout=90000)
        page.wait_for_timeout(1500)
        page.screenshot(path=OUT + "01-地点确认界面.png", full_page=True)
        page.click("#btnRoute")
        page.wait_for_selector("#routeCard", state="visible", timeout=90000)
        page.wait_for_timeout(2500)
        page.screenshot(path=OUT + "02-动线结果界面.png", full_page=True)
        b.close()
        print("截图完成")


if __name__ == "__main__":
    main()
