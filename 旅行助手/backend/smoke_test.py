"""真实冒烟脚本：demo 链接 → 解析 → 确认 → 动线 → 分享/地图/导航（真实 DeepSeek + 百度 API）。"""
import time

import httpx

BASE = "http://127.0.0.1:8000"
c = httpx.Client(base_url=BASE, trust_env=False, timeout=60)


def poll(task_id, label, max_wait=120):
    for _ in range(int(max_wait / 2)):
        t = c.get(f"/api/v1/tasks/{task_id}").json()
        print(f"  [{label}] {t['status']} {t.get('progress') or ''}")
        if t["status"] == "done":
            return True
        if t["status"] == "failed":
            print("  !! 失败：", t.get("error"))
            return False
        time.sleep(2)
    return False


def main():
    r = c.post("/api/v1/trips", json={"source_link": "https://xhslink.cn/o/10vTPLjLXy7"})
    print("POST /trips ->", r.status_code)
    data = r.json()
    trip_id, task_id = data["trip_id"], data["task_id"]
    print("trip_id =", trip_id)

    if not poll(task_id, "解析"):
        return
    print("--- 地点确认清单 ---")
    pl = c.get(f"/api/v1/trips/{trip_id}/places").json()
    places = pl["places"]
    ok = [p for p in places if p["geocode_status"] == "ok"]
    bad = [p for p in places if p["geocode_status"] != "ok"]
    print(f"地点总数 {len(places)}，已定位 {len(ok)}，待处理 {len(bad)}")
    for d in (1, 2):
        names = [p["name"] for p in places if p["day"] == d]
        print(f"  Day{d}({len(names)}): {' → '.join(names)}")
    if bad:
        print("  待处理：", [p["name"] for p in bad])

    print("--- 生成动线 ---")
    r = c.post(f"/api/v1/trips/{trip_id}/route")
    print("POST /route ->", r.status_code, r.json())
    if r.status_code != 200:
        return
    if not poll(r.json()["task_id"], "路线"):
        return
    rt = c.get(f"/api/v1/trips/{trip_id}/route").json()
    for d in rt["days"]:
        print(f"  Day{d['day']}: {len(d['places'])} 个点，{len(d['segments'])} 段")
        for s in d["segments"][:3]:
            print(f"    {s['from_place']} → {s['to_place']} [{s['mode']}] {s['duration_text']}")

    print("--- 跳转 App ---")
    nav = c.get(f"/api/v1/trips/{trip_id}/app-nav").json()
    print("  URIs:", len(nav["uris"]), "| 每段途经点上限:", nav["max_via"], "| 示例:", nav["uris"][0][:90])
    for d in nav["days"]:
        for leg in d["legs"]:
            print(f"    Day{d['day']} 段{leg['leg']}: {leg['from_place']} → {leg['to_place']}，途经 {len(leg['via'])} 个")
    assert all("&via=" not in u for u in nav["uris"]), "途经点须用 viaPoints"
    assert any("viaPoints=" in u for u in nav["uris"]), "未生成途经点"

    print("--- 分享（只读）---")
    sh = c.get(f"/api/v1/share/{trip_id}").json()
    print("  trip.status =", sh["trip"]["status"], "| places =", len(sh["places"]), "| route days =", len(sh["route"]["days"]) if sh["route"] else 0)

    print("--- 静态地图 ---")
    img = c.get(f"/api/v1/trips/{trip_id}/map?day=1")
    print("  HTTP", img.status_code, img.headers.get("content-type"), len(img.content), "bytes")

    print("SMOKE_OK trip_id =", trip_id)


if __name__ == "__main__":
    main()
