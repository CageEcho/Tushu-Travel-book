import { useState, type ChangeEvent } from "react";
import { MapPin } from "lucide-react";
import type { Place } from "../lib/types";

interface Props {
  place: Place;
  onUpdate: (id: number, body: Record<string, unknown>) => void;
}

export default function PlaceCard({ place, onUpdate }: Props) {
  const [name, setName] = useState(place.name);

  const saveName = () => {
    const v = name.trim();
    if (v && v !== place.name) onUpdate(place.id, { name: v });
  };

  const handlePoi = (e: ChangeEvent<HTMLSelectElement>) => {
    const opt = e.target.selectedOptions[0];
    if (!opt?.value) return;
    onUpdate(place.id, {
      poi_uid: opt.value,
      poi_name: opt.dataset.name,
      poi_address: opt.dataset.addr,
      lat: opt.dataset.lat ? parseFloat(opt.dataset.lat) : null,
      lng: opt.dataset.lng ? parseFloat(opt.dataset.lng) : null,
    });
  };

  return (
    <div className="rounded-2xl border border-[#EBEBEB] bg-white p-4 shadow-sm">
      <div className="flex items-start gap-3">
        <span
          className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-xs font-bold"
          style={{ background: "#EAF2EA", color: "#4FA83C" }}
        >
          {place.seq}
        </span>
        <div className="min-w-0 flex-1">
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            onBlur={saveName}
            className="w-full rounded-lg border border-transparent bg-transparent px-1 py-0.5 font-semibold outline-none transition hover:border-[#DDDDDD] focus:border-[#4FA83C]"
          />
          <div className="mt-0.5 flex items-center gap-1 text-xs text-[#717171]">
            <MapPin size={12} className="shrink-0" />
            <span className="truncate">{place.poi_address || "定位中…"}</span>
          </div>
        </div>
        {place.skipped ? (
          <span className="shrink-0 rounded-full bg-[#F3F4F6] px-2 py-0.5 text-[11px] font-medium text-[#717171]">
            已跳过
          </span>
        ) : place.geocode_status === "ok" ? (
          <span className="shrink-0 rounded-full bg-[#E8F7EE] px-2 py-0.5 text-[11px] font-medium text-[#1A7F3C]">
            已定位
          </span>
        ) : (
          <span className="shrink-0 rounded-full bg-[#FFF3E8] px-2 py-0.5 text-[11px] font-medium text-[#E8872A]">
            待处理
          </span>
        )}
      </div>

      <div className="mt-3 flex flex-wrap items-center gap-2 text-sm">
        <label className="flex items-center gap-1.5">
          <span className="text-xs text-[#717171]">天</span>
          <select
            value={place.day}
            onChange={(e) => onUpdate(place.id, { day: parseInt(e.target.value, 10) })}
            className="rounded-lg border border-[#DDDDDD] bg-white px-2 py-1 outline-none"
          >
            <option value={1}>Day 1</option>
            <option value={2}>Day 2</option>
          </select>
        </label>

        <label className="flex min-w-0 flex-1 items-center gap-1.5">
          <span className="shrink-0 text-xs text-[#717171]">换POI</span>
          <select
            value=""
            onChange={handlePoi}
            className="w-full min-w-0 rounded-lg border border-[#DDDDDD] bg-white px-2 py-1 outline-none"
          >
            <option value="">
              {place.geocode_status === "ok" ? "保持当前" : "选择候选…"}
            </option>
            {place.candidates?.map((c) => (
              <option
                key={c.uid ?? c.name}
                value={c.uid ?? c.name}
                data-name={c.name}
                data-addr={c.address ?? ""}
                data-lat={c.lat}
                data-lng={c.lng}
              >
                {c.name}
                {c.address ? ` · ${c.address}` : ""}
              </option>
            ))}
          </select>
        </label>

        <label className="flex shrink-0 items-center gap-1.5">
          <input
            type="checkbox"
            checked={place.skipped}
            onChange={(e) => onUpdate(place.id, { skipped: e.target.checked })}
            className="h-4 w-4 accent-[#4FA83C]"
          />
          <span className="text-xs text-[#717171]">跳过</span>
        </label>
      </div>
    </div>
  );
}
