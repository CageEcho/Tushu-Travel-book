import { Bike, Bus, Clock, Download, ExternalLink, Footprints, Loader2, Navigation, Share2 } from "lucide-react";
import type { AppNavResponse, NavLeg, NavLink, NavSegment, RouteResponse } from "../lib/types";
import MapView from "./MapView";

interface Props {
  route: RouteResponse;
  nav: AppNavResponse | null;
  onAppNav: (leg: NavLeg) => void;
  onSegmentNav: (link: NavLink) => void;
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

function webMapUrl(points: { lat: number | null | undefined; lng: number | null | undefined }[]): string {
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
    <div className="mt-1.5 flex gap-1.5">
      {SEGMENT_MODES.map(({ key, label, Icon }) => (
        <a
          key={key}
          href={seg[key].uri}
          onClick={(e) => {
            e.preventDefault();
            onSegmentNav(seg[key]);
          }}
          className="inline-flex items-center gap-1 rounded-lg border border-[#DDDDDD] bg-white px-2 py-1 text-xs text-[#484848] transition hover:border-[#4FA83C] hover:text-[#4FA83C]"
        >
          <Icon size={12} />
          {label}
        </a>
      ))}
    </div>
  );
}

function NavButton({
  leg,
  label,
  onAppNav,
}: {
  leg: NavLeg;
  label: string;
  onAppNav: (leg: NavLeg) => void;
}) {
  return (
    <a
      href={leg.uri}
      title={leg.via.length ? `途经：${leg.via.join("、")}` : undefined}
      onClick={(e) => {
        e.preventDefault();
        onAppNav(leg);
      }}
      className="inline-flex max-w-full items-center gap-2 rounded-2xl px-5 py-2.5 text-sm font-semibold text-white transition hover:opacity-90"
      style={{ background: "#4FA83C" }}
    >
      <Navigation size={16} className="shrink-0" />
      <span className="truncate">{label}</span>
    </a>
  );
}

export default function RouteView({
  route,
  nav,
  onAppNav,
  onSegmentNav,
  onShare,
  onExport,
  exporting,
  exportProgress,
}: Props) {
  return (
    <div>
      {route.days.map((d) => {
        const navDay = nav?.days.find((n) => n.day === d.day);
        return (
          <div key={d.day} className="mb-8">
            <div className="mb-3 flex items-center gap-2">
              <span
                className="rounded-lg px-2.5 py-1 text-xs font-bold text-white"
                style={{ background: "#4FA83C" }}
              >
                Day {d.day}
              </span>
              <span className="text-sm text-[#717171]">
                {d.places.length} 个地点 · {d.segments.length} 段
              </span>
              <a
                href={webMapUrl(d.places.map((p) => ({ lat: p.lat ?? null, lng: p.lng ?? null })))}
                target="_blank"
                rel="noreferrer"
                className="ml-auto inline-flex items-center gap-1 text-sm font-medium underline-offset-4 hover:underline"
                style={{ color: "#4FA83C" }}
              >
                <ExternalLink size={14} />
                网页版打开
              </a>
            </div>

            <MapView
              points={d.places.map((p) => ({
                name: p.name,
                lat: p.lat ?? null,
                lng: p.lng ?? null,
              }))}
              mapUrl={d.map_url}
            />

            <div className="mt-3 rounded-2xl border border-[#EBEBEB] bg-white px-4 py-2">
              {navDay?.segments.length ? (
                <p className="pt-2 text-xs text-[#B0B0B0]">
                  公交 / 步行 / 骑行：百度地图不支持途经点，请逐段打开
                </p>
              ) : null}
              {d.segments.map((s, i) => {
                const seg = navDay?.segments[i];
                const matched = seg && seg.from_place === s.from_place && seg.to_place === s.to_place;
                return (
                  <div
                    key={i}
                    className="border-b border-dashed border-[#EBEBEB] py-2.5 text-sm last:border-b-0"
                  >
                    <div className="flex items-center justify-between">
                      <span className="min-w-0 truncate pr-3">
                        {s.from_place} → {s.to_place}
                      </span>
                      <span className="flex shrink-0 items-center gap-1.5 text-[#717171]">
                        <Clock size={13} />
                        {s.mode} · {s.duration_text}
                      </span>
                    </div>
                    {matched && <SegmentModes seg={seg} onSegmentNav={onSegmentNav} />}
                  </div>
                );
              })}
            </div>

            <div className="mt-3 flex flex-wrap gap-2">
              {(navDay?.legs ?? []).map((leg, _, legs) => (
                <NavButton
                  key={leg.leg}
                  leg={leg}
                  label={
                    legs.length > 1
                      ? `驾车 Day ${d.day} 第 ${leg.leg} 段：${leg.from_place} → ${leg.to_place}`
                      : `在百度地图打开 Day ${d.day}（驾车 · 途经 ${leg.via.length} 个点）`
                  }
                  onAppNav={onAppNav}
                />
              ))}
            </div>
          </div>
        );
      })}

      <div className="mt-6 flex flex-wrap items-center gap-3">
        <button
          onClick={onShare}
          className="inline-flex items-center gap-2 rounded-2xl border border-[#DDDDDD] bg-white px-6 py-3 text-[15px] font-medium text-[#222] transition hover:border-[#B0B0B0]"
        >
          <Share2 size={18} />
          分享
        </button>
        <button
          onClick={onExport}
          disabled={exporting}
          className="inline-flex items-center gap-2 rounded-2xl border border-[#DDDDDD] bg-white px-6 py-3 text-[15px] font-medium text-[#222] transition hover:border-[#B0B0B0] disabled:opacity-60"
        >
          {exporting ? (
            <Loader2 size={18} className="animate-spin" />
          ) : (
            <Download size={18} />
          )}
          导出长图
        </button>
      </div>
      {exportProgress && (
        <p className="mt-3 text-sm text-[#717171]">{exportProgress}</p>
      )}
    </div>
  );
}
