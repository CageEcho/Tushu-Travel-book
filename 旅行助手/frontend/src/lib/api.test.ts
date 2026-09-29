import { describe, expect, it, vi } from "vitest";
import { api } from "./api";

function mockFetch(ok: boolean, body: unknown, status = ok ? 200 : 400) {
  return vi.fn().mockResolvedValue({
    ok,
    status,
    json: async () => body,
  }) as unknown as typeof fetch;
}

describe("api 层", () => {
  it("成功时返回数据", async () => {
    vi.stubGlobal("fetch", mockFetch(true, { trip_id: "abc", task_id: "def" }));
    const res = await api.createTrip("https://example.com");
    expect(res.trip_id).toBe("abc");
    vi.unstubAllGlobals();
  });

  it("失败时抛出统一错误消息", async () => {
    vi.stubGlobal(
      "fetch",
      mockFetch(false, { error: { code: "X", message: "服务器坏了" } }),
    );
    await expect(api.getTask("task1")).rejects.toThrow("服务器坏了");
    vi.unstubAllGlobals();
  });

  it("无 error 字段时回退 HTTP 状态码", async () => {
    vi.stubGlobal("fetch", mockFetch(false, {}));
    await expect(api.getTask("task1")).rejects.toThrow("HTTP 400");
    vi.unstubAllGlobals();
  });
});
