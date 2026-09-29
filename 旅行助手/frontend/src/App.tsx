import { useCallback, useEffect, useRef, useState } from "react";

import { api } from "./lib/api";
import type { AppNavResponse, HotelsResponse, NavLeg, NavLink, Place, PlacePhoto, RouteResponse } from "./lib/types";
import JourneyWorkspace from "./components/JourneyWorkspace";
import RouteView from "./components/RouteView";
import ScanModal from "./components/ScanModal";

const DEMO_LINK = "https://xhslink.cn/o/10vTPLjLXy7";


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
  const [hotels, setHotels] = useState<HotelsResponse | null>(null);
  const [hotelsError, setHotelsError] = useState("");
  const [photos, setPhotos] = useState<Record<string, PlacePhoto>>({});
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

  // 实景图只是锦上添花：失败时不提示，卡片照常显示
  const loadPhotos = useCallback((trip: string) => {
    api
      .getPhotos(trip)
      .then((r) => setPhotos(r.photos))
      .catch(() => {});
  }, []);

  const loadHotels = useCallback((trip: string) => {
    setHotels(null);
    setHotelsError("");
    api
      .getHotels(trip)
      .then(setHotels)
      .catch((e) => setHotelsError(e instanceof Error ? e.message : "推荐住宿加载失败"));
  }, []);

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
        loadPhotos(trip);
        try {
          const r = await api.getRoute(trip);
          setRoute(r);
          setPhase("route");
          loadHotels(trip);
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
  }, [loadHotels, loadPhotos]);

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
    if (!value || phase === "loading" || phase === "routing") return;
    setError("");
    setProgress("提交中…");
    setPhase("loading");
    setPlaces([]);
    setPhotos({});
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
          loadPhotos(trip_id);
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
          loadHotels(tripId);
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
      loadPhotos(tripId); // 改名 / 换 POI 后重新匹配图片（未变的地点走缓存）
    } catch (e) {
      setError(e instanceof Error ? e.message : "更新失败");
    }
  };

  return (
    <>
      <JourneyWorkspace
        phase={phase} link={link} onLinkChange={setLink} tripId={tripId}
        title={title} city={city} places={places} photos={photos} progress={progress} error={error}
        onGenerate={() => handleGenerate()}
        onDemo={() => { setLink(DEMO_LINK); document.getElementById("source-link")?.focus(); }}
        onUpdate={updatePlace} onConfirm={handleGenerateRoute} onShare={handleShare}
      >
        {phase === "route" && route && (
          <section className="result-section">
            <div className="result-heading"><h2>动线结果</h2>
              <button onClick={() => setPhase("confirm")} className="quiet-button">调整地点</button>
            </div>
            <RouteView route={route} nav={nav} onAppNav={handleAppNav}
              onSegmentNav={handleSegmentNav} hotels={hotels} hotelsError={hotelsError} onShare={handleShare} onExport={handleExport}
              exporting={exporting} exportProgress={exportProgress} />
          </section>
        )}
      </JourneyWorkspace>
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
    </>
  );
}
