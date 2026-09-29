import { BedDouble, Bike, Bus, Clock, Download, ExternalLink, Footprints, Loader2, MapPin, Navigation, Share2, Star } from "lucide-react";
import type { AppNavResponse, HotelDay, HotelsResponse, NavLeg, NavLink, NavSegment, RouteResponse } from "../lib/types";
import MapView from "./MapView";

interface Props {
  route: RouteResponse;
  nav: AppNavResponse | null;
  onAppNav: (leg: NavLeg) => void;
  onSegmentNav: (link: NavLink) => void;
  hotels: HotelsResponse | null;
  hotelsError: string;
  onShare: () => void;
  onExport: () => void;
  exporting: boolean;
  exportProgress: string;
}

function toMercator(lng: number, lat: number): [number, number] {
  const x = (lng * 20037508.34) / 180;
  const y = Math.log(Math.tan(((90 + lat) * Math.PI) / 360)) / (Math.PI / 180);
  const yM = (y * 20037508.34) / 180;
  return [x, yM];
}

function webMapUrl(points: { lat?: number | null; lng?: number | null }[]): string {
  const pts = points.filter((p) => p.lat != null && p.lng != null) as {
    lat: number;
    lng: number;
  }[];
  if (!pts.length) return "https://map.baidu.com/";
  const lng = pts.reduce((s, p) => s + p.lng, 0) / pts.length;
  const lat = pts.reduce((s, p) => s + p.lat, 0) / pts.length;
  const [mx, my] = toMercator(lng, lat);
  return `https://map.baidu.com/@${mx.toFixed(2)},${my.toFixed(2)},13z`;
}

const SEGMENT_MODES = [
  { key: "transit", label: "公交", Icon: Bus },
  { key: "walking", label: "步行", Icon: Footprints },
  { key: "riding", label: "骑行", Icon: Bike },
] as const;

function SegmentModes({
  seg,
  onSegmentNav,
}: {
  seg: NavSegment;
  onSegmentNav: (link: NavLink) => void;
}) {
  return (
    <div className="route-modes">
      {SEGMENT_MODES.map(({ key, label, Icon }) => (
        <a
          key={key}
          href={seg[key].uri}
          onClick={(e) => {
            e.preventDefault();
            onSegmentNav(seg[key]);
          }}
          className="route-mode"
        >
          <Icon size={12} />
          {label}
        </a>
      ))}
    </div>
  );
}

function fmtDistance(m: number): string {
  return m < 1000 ? `${m} 米` : `${(m / 1000).toFixed(1)} 公里`;
}

function HotelSection({ data, loading, error, onSegmentNav }: { data?: HotelDay; loading: boolean; error: string; onSegmentNav: (link: NavLink) => void }) {
  if (!loading && !error && !data) return null;
  const titleId = `hotel-title-${data?.day ?? "loading"}`;
  return <section className="route-hotels" aria-labelledby={titleId}>
    <header className="hotel-header"><span className="hotel-icon"><BedDouble size={18} /></span><div><h4 id={titleId}>今晚住哪</h4><p>{data ? `在「${data.anchor.name}」收尾，住附近不折返` : "按档次为你挑三家"}</p></div></header>
    {error ? <p className="hotel-status" role="status">{error}</p>
      : !data ? <p className="hotel-status" role="status"><Loader2 size={14} className="animate-spin" />正在查找附近酒店…</p>
      : !data.hotels.length ? <p className="hotel-status" role="status">附近暂未找到合适的酒店。</p>
      : <div className="hotel-list">{data.hotels.map(h => <article className={`hotel-item tier-${h.tier}`} key={h.uid ?? h.name}>
        <div className="hotel-tier"><strong>{h.tier_label}</strong>{h.grade && <small>{h.grade}</small>}</div>
        <div className="hotel-main"><strong>{h.name}</strong>{h.address && <p>{h.address}</p>}
          <div className="hotel-meta"><span className="hotel-rating"><Star size={11} />{h.rating.toFixed(1)}</span><span>{h.comment_num} 条评价</span><span>距{data.anchor.name} {fmtDistance(h.distance_m)}</span></div></div>
        <a className="route-mode hotel-locate" href={h.link.uri} onClick={e => { e.preventDefault(); onSegmentNav(h.link); }}><MapPin size={12} />查看位置</a>
      </article>)}</div>}
    <p className="hotel-note">档次与评分来自百度地图，价格和房态以预订平台为准。</p>
  </section>;
}

export default function RouteView({ route, nav, onAppNav, onSegmentNav, hotels, hotelsError, onShare, onExport, exporting, exportProgress }: Props) {
  return <div className="route-results">
    <div className="route-intro"><span className="eyebrow">READY TO EXPLORE</span><p>把每一站，连成今天的风景。</p></div>
    {route.days.map(d => {
      const navDay = nav?.days.find(n => n.day === d.day);
      const minutes = Math.round(d.segments.reduce((sum, s) => sum + s.duration_s, 0) / 60);
      return <article className="route-day-card" key={d.day}>
        <header className="route-day-header">
          <div className="route-day-number"><small>DAY</small><strong>{String(d.day).padStart(2, "0")}</strong></div>
          <div className="route-day-title"><h3>第 {d.day} 天 · 沿途漫游</h3><p>{d.places.length} 个地点<span>·</span>{d.segments.length} 段路程{minutes > 0 && <><span>·</span>交通约 {minutes} 分钟</>}</p></div>
          <a className="route-map-link" href={navDay?.legs[0]?.web_uri || webMapUrl(d.places)} target="_blank" rel="noreferrer" aria-label={`在百度地图网页版打开第${d.day}天`}><ExternalLink size={16} /></a>
        </header>
        <div className="route-map-frame"><MapView points={d.places.map(p => ({name:p.name,lat:p.lat ?? null,lng:p.lng ?? null}))} mapUrl={d.map_url} /><div className="route-map-caption"><span />地点顺序示意 · 实际道路以导航为准</div></div>
        <div className="route-itinerary">
          <div className="route-itinerary-heading"><h4>今日路线</h4><span>跟着顺序，慢慢走</span></div>
          {d.places.map((place, i) => {
            const segment = d.segments[i];
            const link = navDay?.segments[i];
            const matched = segment && link && link.from_place === segment.from_place && link.to_place === segment.to_place;
            return <div className="route-stop" key={place.id}>
              <span className="route-stop-number">{i + 1}</span>
              <div className="route-stop-content"><div className="route-stop-title"><strong>{place.name}</strong><span>{i === 0 ? "出发" : i === d.places.length - 1 ? "最后一站" : place.type}</span></div>
                {place.poi_address && <p className="route-stop-address">{place.poi_address}</p>}
                {segment && <div className="route-connection"><div className="route-duration"><Clock size={12} /><span>{segment.mode} · {segment.duration_text}</span></div>{matched && <SegmentModes seg={link} onSegmentNav={onSegmentNav} />}</div>}
              </div>
            </div>;
          })}
          {!!navDay?.segments.length && <p className="route-transport-note">公交、步行、骑行可按相邻两站分别导航。</p>}
        </div>
        {!!navDay?.legs.length && <div className="route-navigation">{navDay.legs.map(leg => <a key={leg.leg} href={leg.uri} onClick={event => {event.preventDefault(); onAppNav(leg);}} className="black-button" title={`${leg.from_place} → ${leg.to_place}`}><Navigation size={15} /><span>{navDay.legs.length > 1 ? `驾车导航 · 第 ${leg.leg} 段` : "在百度地图开始导航"}</span><ExternalLink size={13} /></a>)}</div>}
        <HotelSection data={hotels?.days.find(h => h.day === d.day)} loading={!hotels && !hotelsError} error={hotelsError} onSegmentNav={onSegmentNav} />
      </article>;
    })}
    <div className="route-save-bar"><div><strong>留住这份旅行灵感</strong><p>分享给同行的人，或保存为长图。</p></div><div className="route-save-actions"><button onClick={onShare}><Share2 size={15} />分享</button><button onClick={onExport} disabled={exporting}>{exporting ? <Loader2 size={15} className="animate-spin" /> : <Download size={15} />}{exporting ? "导出中" : "保存长图"}</button></div></div>
    {exportProgress && <p className="route-export-status" role="status">{exportProgress}</p>}
  </div>;
}
