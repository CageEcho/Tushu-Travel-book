import { useCallback, useEffect, useRef, useState } from "react";
import { Loader2, MapPin, Navigation, Share2, Sparkles } from "lucide-react";
import { api } from "./lib/api";
import type { AppNavResponse, NavLeg, NavLink, Place, RouteResponse } from "./lib/types";
import PlaceCard from "./components/PlaceCard";
import RouteView from "./components/RouteView";
import ScanModal from "./components/ScanModal";

const DEMO_LINK = "https://xhslink.cn/o/10vTPLjLXy7";
const BRAND = "#4FA83C";

type Phase = "idle" | "loading" | "confirm" | "routing" | "route";

export default function App() {
  const [link, setLink] = useState("");
  const [phase, setPhase] = useState<Phase>("idle");
  const [progress, setProgress] = useState("");
  const [error, setError] = useState("");
  const [tripId, setTripId] = useState("");
  const [city, setCity] = useState("");
  const [title, setTitle] = useState("");
  const [places, setPlaces] = useState<Place[]>([]);
  const [route, setRoute] = useState<RouteResponse | null>(null);
  const [nav, setNav] = useState<AppNavResponse | null>(null);
  const [scanLeg, setScanLeg] = useState<NavLeg | null>(null);
  const [navHint, setNavHint] = useState("");
  const [exporting, setExporting] = useState(false);
  const [exportProgress, setExportProgress] = useState("");
  const timerRef = useRef<number | null>(null);
  const exportTimerRef = useRef<number | null>(null);

  const stopTimer = useCallback(() => {
    if (timerRef.current !== null) {
      window.clearInterval(timerRef.current);
      timerRef.current = null;
    }
  }, []);

  const stopExportTimer = useCallback(() => {
    if (exportTimerRef.current !== null) {
      window.clearInterval(exportTimerRef.current);
      exportTimerRef.current = null;
    }
  }, []);

  useEffect(
    () => () => {
      stopTimer();
      stopExportTimer();
    },
    [stopTimer, stopExportTimer],
  );

  // 恢复入口：?trip=xxx 或 /share/xxx
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    let trip = params.get("trip");
    if (!trip) {
      const m = window.location.pathname.match(/^\/share\/([A-Za-z0-9]+)/);
      if (m) trip = m[1];
    }
    if (!trip) return;
    (async () => {
      try {
        const data = await api.getPlaces(trip);
        setTripId(trip);
        setCity(data.city ?? "");
        setTitle(data.title ?? "");
        setPlaces(data.places);
        setPhase("confirm");
        try {
          const r = await api.getRoute(trip);
          setRoute(r);
          setPhase("route");
          try {
            setNav(await api.getAppNav(trip));
          } catch {
            /* ignore */
          }
        } catch {
          /* 尚未生成动线 */
        }
      } catch {
        setError("行程不存在或已失效");
        setPhase("idle");
      }
    })();
  }, []);

  const pollTask = useCallback(
    (taskId: string, onDone: () => void, failPhase: Phase) => {
      stopTimer();
      timerRef.current = window.setInterval(async () => {
        try {
          const t = await api.getTask(taskId);
          setProgress(t.progress ?? "");
          if (t.status === "done") {
            stopTimer();
            onDone();
          } else if (t.status === "failed") {
            stopTimer();
            setError(t.error ?? "生成失败");
            setPhase(failPhase);
          }
        } catch (e) {
          stopTimer();
          setError(e instanceof Error ? e.message : "请求失败");
          setPhase(failPhase);
        }
      }, 1200);
    },
    [stopTimer],
  );

  const handleGenerate = async (src?: string) => {
    const value = (src ?? link).trim();
    if (!value) return;
    setError("");
    setProgress("提交中…");
    setPhase("loading");
    setPlaces([]);
    setRoute(null);
    try {
      const { trip_id, task_id } = await api.createTrip(value);
      setTripId(trip_id);
      window.history.replaceState(null, "", `?trip=${trip_id}`);
      pollTask(
        task_id,
        async () => {
          const data = await api.getPlaces(trip_id);
          setCity(data.city ?? "");
          setTitle(data.title ?? "");
          setPlaces(data.places);
          setPhase("confirm");
        },
        "idle",
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : "请求失败");
      setPhase("idle");
    }
  };

  const handleGenerateRoute = async () => {
    if (!tripId) return;
    setError("");
    setProgress("路线编排中…");
    setPhase("routing");
    try {
      const { task_id } = await api.createRoute(tripId);
      pollTask(
        task_id,
        async () => {
          const r = await api.getRoute(tripId);
          setRoute(r);
          setPhase("route");
          setNav(null);
          api
            .getAppNav(tripId)
            .then(setNav)
            .catch(() => {});
        },
        "confirm",
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : "请求失败");
      setPhase("confirm");
    }
  };

  const isMobile = () => {
    const ua = navigator.userAgent;
    return (
      /Android|iPhone|iPad|iPod/i.test(ua) ||
      (/Macintosh/.test(ua) && navigator.maxTouchPoints > 1) // iPadOS 伪装成 Mac
    );
  };

  const openInApp = (uri: string) => {
    // 微信 / QQ 等内置浏览器可能拦截 baidumap://（部分版本会弹确认框放行），先尝试再提示
    const inApp = /MicroMessenger|QQ\/|Weibo|DingTalk|AliApp/i.test(navigator.userAgent);
    setNavHint("");
    window.location.href = uri;
    // 3 秒后页面仍在前台，多半是没唤起（未安装百度地图或浏览器拦截）
    window.setTimeout(() => {
      if (document.visibilityState === "visible") {
        setNavHint(
          inApp
            ? "没有打开百度地图？当前在微信 / QQ 等 App 内置浏览器里，可能被拦截。请点右上角「…」，选择「在浏览器打开」后再点按钮。"
            : "没有打开百度地图？请确认手机已安装百度地图 App；若仍无反应，换用系统自带浏览器（Safari / Chrome）打开本页再试。",
        );
      }
    }, 3000);
  };

  // 驾车（含途经点）：电脑上没有 App，弹二维码 + 网页版
  const handleAppNav = (leg: NavLeg) => {
    if (!isMobile()) {
      setScanLeg(leg);
      return;
    }
    openInApp(leg.uri);
  };

  // 公交 / 步行 / 骑行单段：电脑上直接开网页版
  const handleSegmentNav = (link: NavLink) => {
    if (!isMobile()) {
      window.open(link.web_uri, "_blank", "noopener");
      return;
    }
    openInApp(link.uri);
  };

  const handleShare = async () => {
    if (!tripId) return;
    const url = `${window.location.origin}/share/${tripId}`;
    try {
      await navigator.clipboard.writeText(url);
      window.alert(`分享链接已复制：${url}`);
    } catch {
      window.prompt("复制分享链接：", url);
    }
  };

  const handleExport = async () => {
    if (!tripId) return;
    setExporting(true);
    setExportProgress("");
    try {
      const { task_id } = await api.createExport(tripId);
      stopExportTimer();
      exportTimerRef.current = window.setInterval(async () => {
        try {
          const t = await api.getTask(task_id);
          setExportProgress(t.progress ?? "");
          if (t.status === "done") {
            stopExportTimer();
            setExporting(false);
            window.open(`/api/v1/trips/${tripId}/export.png`);
          } else if (t.status === "failed") {
            stopExportTimer();
            setExporting(false);
            setExportProgress(`导出失败：${t.error ?? ""}`);
          }
        } catch (e) {
          stopExportTimer();
          setExporting(false);
          setExportProgress(e instanceof Error ? e.message : "导出失败");
        }
      }, 1500);
    } catch (e) {
      setExporting(false);
      setExportProgress(e instanceof Error ? e.message : "导出失败");
    }
  };

  const updatePlace = async (id: number, body: Record<string, unknown>) => {
    if (!tripId) return;
    try {
      await api.updatePlace(tripId, id, body);
      const data = await api.getPlaces(tripId);
      setPlaces(data.places);
    } catch (e) {
      setError(e instanceof Error ? e.message : "更新失败");
    }
  };

  const days = new Map<number, Place[]>();
  for (const p of places) {
    const arr = days.get(p.day) ?? [];
    arr.push(p);
    days.set(p.day, arr);
  }
  for (const arr of days.values()) arr.sort((a, b) => a.seq - b.seq);
  const dayKeys = [...days.keys()].sort((a, b) => a - b);

  return (
    <div className="min-h-screen bg-[#F7F7F7]">
      <header className="sticky top-0 z-10 border-b border-[#EBEBEB] bg-white/90 backdrop-blur">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-4 py-3 sm:px-6">
          <div className="flex items-center gap-2">
            <span
              className="flex h-8 w-8 items-center justify-center rounded-full font-bold text-white"
              style={{ background: BRAND }}
            >
              T
            </span>
            <span className="text-lg font-bold tracking-tight">TripFlow</span>
          </div>
          <div className="text-sm text-[#717171]">旅行全流程助手</div>
        </div>
      </header>

      <main className="mx-auto max-w-5xl px-4 pb-24 sm:px-6">
        <section className="py-8 sm:py-12">
          <h1 className="text-2xl font-bold leading-tight tracking-tight sm:text-3xl">
            把攻略变成
            <span style={{ color: BRAND }}> 一张可走的动线</span>
          </h1>
          <p className="mt-2 text-sm text-[#717171] sm:text-base">
            粘贴小红书攻略链接，自动识别景点、连成百度地图多途径点动线。
          </p>

          <div className="mt-6 flex flex-col gap-3 sm:flex-row">
            <div className="flex flex-1 items-center rounded-2xl border border-[#DDDDDD] bg-white px-4 shadow-sm focus-within:border-[#4FA83C] focus-within:ring-2 focus-within:ring-[#4FA83C]/20">
              <MapPin size={18} className="shrink-0 text-[#717171]" />
              <input
                value={link}
                onChange={(e) => setLink(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleGenerate()}
                placeholder="粘贴小红书攻略链接…"
                className="w-full bg-transparent px-3 py-3.5 text-[15px] outline-none placeholder:text-[#B0B0B0]"
              />
            </div>
            <button
              onClick={() => handleGenerate()}
              disabled={phase === "loading" || phase === "routing"}
              className="inline-flex items-center justify-center gap-2 rounded-2xl px-7 py-3.5 text-[15px] font-semibold text-white transition hover:opacity-90 disabled:opacity-60"
              style={{ background: BRAND }}
            >
              {phase === "loading" ? (
                <Loader2 size={18} className="animate-spin" />
              ) : (
                <Sparkles size={18} />
              )}
              生成动线
            </button>
          </div>
          <button
            onClick={() => {
              setLink(DEMO_LINK);
              handleGenerate(DEMO_LINK);
            }}
            className="mt-3 text-sm font-medium underline-offset-4 hover:underline"
            style={{ color: BRAND }}
          >
            试试这篇重庆攻略 →
          </button>

          {phase === "loading" && (
            <div className="mt-6 flex items-center gap-2 text-sm text-[#717171]">
              <Loader2 size={16} className="animate-spin" style={{ color: BRAND }} />
              {progress || "处理中…"}
            </div>
          )}
          {phase === "routing" && (
            <div className="mt-6 flex items-center gap-2 text-sm text-[#717171]">
              <Loader2 size={16} className="animate-spin" style={{ color: BRAND }} />
              {progress || "路线编排中…"}
            </div>
          )}
          {error && (
            <div className="mt-6 rounded-xl bg-[#FEF2F2] px-4 py-3 text-sm text-[#DC2626]">
              {error}
            </div>
          )}
        </section>

        {/* 地点确认 */}
        {(phase === "confirm" || phase === "route") && places.length > 0 && (
          <section>
            <div className="mb-4 flex flex-wrap items-baseline justify-between gap-2">
              <h2 className="text-xl font-bold">{title || "行程地点"}</h2>
              <span className="text-sm text-[#717171]">
                {city && `${city} · `}
                共 {places.length} 个地点
              </span>
            </div>

            {dayKeys.map((day) => (
              <div key={day} className="mb-6">
                <div className="mb-3 flex items-center gap-2">
                  <span
                    className="rounded-lg px-2.5 py-1 text-xs font-bold text-white"
                    style={{ background: BRAND }}
                  >
                    Day {day}
                  </span>
                  <span className="text-sm text-[#717171]">
                    {days.get(day)!.length} 个地点
                  </span>
                </div>
                <div className="grid gap-3 sm:grid-cols-2">
                  {days.get(day)!.map((p) => (
                    <PlaceCard key={p.id} place={p} onUpdate={updatePlace} />
                  ))}
                </div>
              </div>
            ))}

            {phase === "confirm" && (
              <div className="mt-6 flex flex-wrap items-center gap-3">
                <button
                  onClick={handleGenerateRoute}
                  className="inline-flex items-center gap-2 rounded-2xl px-6 py-3 text-[15px] font-semibold text-white transition hover:opacity-90"
                  style={{ background: BRAND }}
                >
                  <Navigation size={18} />
                  确认并生成动线
                </button>
                <button
                  onClick={handleShare}
                  className="inline-flex items-center gap-2 rounded-2xl border border-[#DDDDDD] bg-white px-6 py-3 text-[15px] font-medium text-[#222] transition hover:border-[#B0B0B0]"
                >
                  <Share2 size={18} />
                  分享
                </button>
              </div>
            )}
          </section>
        )}

        {/* 动线结果 */}
        {phase === "route" && route && (
          <section className="mt-6">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-xl font-bold">动线结果</h2>
              <button
                onClick={() => setPhase("confirm")}
                className="text-sm font-medium underline-offset-4 hover:underline"
                style={{ color: BRAND }}
              >
                调整地点
              </button>
            </div>
            <RouteView
              route={route}
              nav={nav}
              onAppNav={handleAppNav}
              onSegmentNav={handleSegmentNav}
              onShare={handleShare}
              onExport={handleExport}
              exporting={exporting}
              exportProgress={exportProgress}
            />
          </section>
        )}
      </main>

      {scanLeg && (
        <ScanModal
          url={`${window.location.origin}/share/${tripId}`}
          leg={scanLeg}
          onClose={() => setScanLeg(null)}
        />
      )}
      {navHint && (
        <div className="fixed inset-x-0 bottom-4 z-40 flex justify-center px-4">
          <div className="flex max-w-xl items-start gap-3 rounded-2xl bg-[#222] px-4 py-3 text-sm text-white shadow-xl">
            <span>{navHint}</span>
            <button onClick={() => setNavHint("")} className="shrink-0 text-white/70 hover:text-white">
              知道了
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
