import { useEffect, useRef, useState } from "react";

interface Pt { name: string; lat: number | null; lng: number | null }
interface MapPoint { lng: number; lat: number }
interface BaiduMap {
  centerAndZoom: (point: MapPoint, zoom: number) => void;
  enableScrollWheelZoom: (enabled: boolean) => void;
  addOverlay: (overlay: unknown) => void;
  clearOverlays: () => void;
  setViewport: (points: MapPoint[]) => void;
  destroy?: () => void;
}
interface MapApi {
  Map: new (element: HTMLElement) => BaiduMap;
  Point: new (lng: number, lat: number) => MapPoint;
  Polyline: new (points: MapPoint[], options: Record<string, unknown>) => unknown;
  Marker: new (point: MapPoint) => unknown;
  Label: new (text: string, options: Record<string, unknown>) => { setStyle?: (style: Record<string, string>) => void };
  Size: new (width: number, height: number) => unknown;
}
const getApi = () => (window as unknown as { BMapGL?: MapApi }).BMapGL;
interface Props { points: Pt[]; mapUrl: string; focusPoint?: Pt; }
export default function MapView({ points, mapUrl, focusPoint }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<BaiduMap | null>(null);
  const [ready, setReady] = useState(false);
  const [failed, setFailed] = useState(false);
  const [imageFailed, setImageFailed] = useState(false);
  const pointKey = JSON.stringify(points);
  useEffect(() => {
    let timer: ReturnType<typeof setTimeout>;
    const deadline = Date.now() + 8000;
    const check = () => {
      if (getApi()) setReady(true);
      else if (Date.now() < deadline) timer = setTimeout(check, 300);
      else setFailed(true);
    };
    check();
    return () => clearTimeout(timer);
  }, []);
  useEffect(() => {
    const api = getApi();
    if (!ready || !api || !containerRef.current) return;
    try {
      const map = new api.Map(containerRef.current);
      map.enableScrollWheelZoom(true);
      mapRef.current = map;
      return () => { map.clearOverlays(); map.destroy?.(); mapRef.current = null; };
    } catch { setFailed(true); }
  }, [ready]);
  useEffect(() => {
    const api = getApi();
    const map = mapRef.current;
    if (!ready || !api || !map) return;
    const pts = (JSON.parse(pointKey) as Pt[]).filter((p): p is Pt & { lat: number; lng: number } => p.lat != null && p.lng != null);
    if (!pts.length) return;
    try {
      map.clearOverlays();
      const path = pts.map(p => new api.Point(p.lng, p.lat));
      map.centerAndZoom(path[0], 14);
      map.addOverlay(new api.Polyline(path, { strokeColor: "#28BDF0", strokeWeight: 4, strokeOpacity: 0.8 }));
      pts.forEach((p, i) => {
        const safeName = p.name.replace(/[&<>"']/g, character => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[character]!);
        const label = new api.Label(`<span title="${i + 1}. ${safeName}" style="display:grid;place-items:center;width:28px;height:28px;border:3px solid white;border-radius:50%;background:#24b7e5;color:white;font:600 12px/1 system-ui;box-shadow:0 2px 8px #23475b35;box-sizing:border-box">${i + 1}</span>`, { position: path[i], offset: new api.Size(-14, -14) });
        label.setStyle?.({ border: "none", backgroundColor: "transparent", padding: "0" });
        map.addOverlay(label);
      });
      map.setViewport(path);
    } catch { setFailed(true); }
  }, [ready, pointKey]);
  useEffect(() => {
    const api = getApi();
    if (api && mapRef.current && focusPoint?.lat != null && focusPoint.lng != null) {
      mapRef.current.centerAndZoom(new api.Point(focusPoint.lng, focusPoint.lat), 16);
    }
  }, [ready, focusPoint?.lat, focusPoint?.lng]);
  if (failed) return <div className="map-canvas static-map">{imageFailed ? <p role="status">地图暂时无法加载，地点清单仍可使用。</p> : <img src={mapUrl} alt="地点顺序示意地图" onError={() => setImageFailed(true)} />}<span>静态地图预览</span></div>;
  return <div className="map-canvas" ref={containerRef}>{!ready && <div className="map-loading" role="status">正在展开旅行地图…</div>}</div>;
}
