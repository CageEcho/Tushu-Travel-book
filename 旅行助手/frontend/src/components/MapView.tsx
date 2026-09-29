import { useEffect, useRef, useState } from "react";

interface Pt {
  name: string;
  lat: number | null;
  lng: number | null;
}

interface Props {
  points: Pt[];
  mapUrl: string;
}

export default function MapView({ points, mapUrl }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const pointsRef = useRef(points);
  pointsRef.current = points;
  const [ready, setReady] = useState(false);
  const [failed, setFailed] = useState(false);

  // 等 index.html 里引入的 BMapGL 就绪
  useEffect(() => {
    let cancelled = false;
    const deadline = Date.now() + 8000;
    const check = () => {
      if (cancelled) return;
      const w = window as unknown as { BMapGL?: any };
      if (w.BMapGL) {
        setReady(true);
      } else if (Date.now() < deadline) {
        setTimeout(check, 300);
      } else {
        setFailed(true);
      }
    };
    check();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!ready) return;
    const el = containerRef.current;
    const w = window as unknown as { BMapGL?: any };
    if (!el || !w.BMapGL) {
      setFailed(true);
      return;
    }
    const pts = pointsRef.current.filter((p) => p.lat != null && p.lng != null);
    if (!pts.length) {
      setFailed(true);
      return;
    }
    try {
      const map = new w.BMapGL.Map(el);
      map.centerAndZoom(new w.BMapGL.Point(pts[0].lng, pts[0].lat), 14);
      map.enableScrollWheelZoom(true);
      const path = pts.map((p) => new w.BMapGL.Point(p.lng, p.lat));
      map.addOverlay(
        new w.BMapGL.Polyline(path, {
          strokeColor: "#4FA83C",
          strokeWeight: 4,
          strokeOpacity: 0.9,
        }),
      );
      pts.forEach((p, i) => {
        const pt = new w.BMapGL.Point(p.lng, p.lat);
        map.addOverlay(new w.BMapGL.Marker(pt));
        map.addOverlay(
          new w.BMapGL.Label(`${i + 1}. ${p.name}`, {
            position: pt,
            offset: new w.BMapGL.Size(12, -34),
          }),
        );
      });
    } catch {
      setFailed(true);
    }
  }, [ready]);

  if (failed) {
    return (
      <img
        src={mapUrl}
        alt="动线地图"
        className="w-full rounded-2xl border border-[#EBEBEB]"
      />
    );
  }

  return (
    <div
      ref={containerRef}
      className="h-[380px] w-full rounded-2xl border border-[#EBEBEB]"
    />
  );
}
