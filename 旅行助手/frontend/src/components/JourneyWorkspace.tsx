import { useState, type ReactNode } from "react";
import { ArrowDown, ArrowLeft, ArrowUpRight, CalendarDays, Check, ChevronRight, Compass, Link2, ListChecks, Loader2, Map, MapPin, Navigation, PanelLeftClose, PanelLeftOpen, Share2, Sparkles } from "lucide-react";
import type { Place, PlacePhoto } from "../lib/types";
import PlaceCard from "./PlaceCard";
import MapView from "./MapView";

interface Props {
  phase: string; link: string; onLinkChange: (value: string) => void;
  tripId: string; title: string; city: string; places: Place[]; photos: Record<string, PlacePhoto>;
  progress: string; error: string; onGenerate: () => void; onDemo: () => void;
  onUpdate: (id: number, body: Record<string, unknown>) => void;
  onConfirm: () => void; onShare: () => void; children: ReactNode;
}

export default function JourneyWorkspace(p: Props) {
  const [selectedDay, setSelectedDay] = useState<number | null>(null);
  const [selectedPlace, setSelectedPlace] = useState<number | null>(null);
  const [sidebar, setSidebar] = useState(true);
  const [mobileTab, setMobileTab] = useState("list");
  const busy = p.phase === "loading" || p.phase === "routing";
  const hasTrip = !!p.tripId;
  const days = [...new Set(p.places.map(place => place.day))].sort((a, b) => a - b);
  const day = selectedDay !== null && days.includes(selectedDay) ? selectedDay : days[0];
  const active = p.places.filter(place => place.day === day).sort((a, b) => a.seq - b.seq);
  const mapped = active.filter(place => !place.skipped && place.lat != null && place.lng != null);
  const focused = mapped.find(place => place.id === selectedPlace);
  const input = <form className="link-composer" onSubmit={event => { event.preventDefault(); p.onGenerate(); }}>
    <div className="composer-label"><Link2 size={15} /> 解析攻略链接</div>
    <label className="sr-only" htmlFor="source-link">小红书攻略链接</label>
    <textarea id="source-link" value={p.link} onChange={event => p.onLinkChange(event.target.value)} placeholder="把喜欢的小红书攻略，粘贴在这里…" rows={hasTrip ? 3 : 2} />
    <div className="composer-bottom"><span>保留攻略里的旅行顺序</span><button className="send-button" disabled={busy || !p.link.trim()} aria-label="解析攻略">{busy ? <Loader2 className="animate-spin" size={20} /> : <ArrowUpRight size={22} />}</button></div>
  </form>;
  return <div className={`trip-app ${hasTrip ? "has-trip" : "is-home"}`}>
    <header className="app-header">
      <a className="brand-lockup" href="/" aria-label="途书旅记 首页"><span className="brand-symbol"><Compass size={23} /></span><strong>途书旅记<span>TripFlow AI旅行助手</span></strong></a>
      {hasTrip ? <div className="header-trip"><span>{p.city || "我的旅行"}</span><span className="header-divider" /><CalendarDays size={16} /><span>{days.length || "—"} 天</span></div> : <span className="header-caption">灵感出发，自在抵达。</span>}
      {hasTrip && <div className="header-actions"><a href="/" className="quiet-button"><ArrowLeft size={15} /><span>新建行程</span></a><button className="black-button small" onClick={p.onShare}><Share2 size={15} /> 分享</button></div>}
    </header>
    {!hasTrip ? <main className="home-main">
      <div className="hero-heading">
        <div className="hero-eyebrow">Trip Flow</div>
        <h1>把收藏的攻略，<br className="mobile-break" />变成下一段旅程<span>。</span></h1>
      </div>
      <p className="hero-description">少一点查找，多一些风景。</p>
      <div className="home-composer">{input}<div className="home-demo"><span>还没想好去哪？</span><button disabled={busy} onClick={p.onDemo}>试试这篇重庆攻略 <ArrowUpRight size={15} /></button></div></div>
      {p.error && <div className="error-message" role="alert">{p.error}</div>}
      <div className="home-steps">{[{ icon: Link2, title: "留住灵感", text: "粘贴你喜欢的攻略" }, { icon: ListChecks, title: "安排刚刚好", text: "确认地点，按天整理" }, { icon: Navigation, title: "带着地图出发", text: "导航、分享与长图" }].map((step, i) => <div className="home-step" key={step.title}><span className="step-icon"><step.icon size={21} /></span><div><small>0{i + 1}</small><h2>{step.title}</h2><p>{step.text}</p></div></div>)}</div>
    </main> : <div className={`workspace ${sidebar ? "" : "sidebar-collapsed"}`}>
      {sidebar && <aside className="assistant-panel">
        <div className="panel-top"><span className="assistant-title"><Sparkles size={17} /> 旅行灵感</span><button className="icon-button" onClick={() => setSidebar(false)} aria-label="收起攻略侧栏"><PanelLeftClose size={18} /></button></div>
        <div className="assistant-intro"><span className="soft-icon"><Compass size={27} /></span><h2>让灵感，<br />慢慢成为行程。</h2><p>我们把攻略中的地点整理好了。<br />按你的节奏，确认每一站。</p></div>
        <div className="journey-progress">
          <div className="progress-step complete"><span><Check size={12} /></span><div>导入攻略<small>从链接开始这次旅行</small></div></div>
          <div className={`progress-step ${p.phase === "loading" ? "current" : "complete"}`}><span>{p.phase === "loading" ? <Loader2 size={12} className="animate-spin" /> : <Check size={12} />}</span><div>识别旅行地点<small>{p.phase === "loading" ? p.progress || "正在解析…" : `已整理 ${p.places.length} 个地点`}</small></div></div>
          <div className={`progress-step ${p.phase === "confirm" ? "current" : ""}`}><span>3</span><div>确认并出发<small>核对地点，再生成动线</small></div></div>
        </div>
        <div className="sidebar-bottom">{input}<button className="demo-link" disabled={busy} onClick={p.onDemo}>试试这篇重庆攻略 <ArrowUpRight size={14} /></button></div>
      </aside>}
      <main className={`planning-panel ${mobileTab === "map" ? "mobile-hidden" : ""}`}>
        <div className="planning-toolbar"><div className="toolbar-title">{!sidebar && <button className="icon-button" onClick={() => setSidebar(true)} aria-label="展开攻略侧栏"><PanelLeftOpen size={19} /></button>}<ListChecks size={17} /><span>我的行程</span></div><span className="subtle-caption">按自己的节奏出发</span></div>
        <div className="planning-scroll">
          <div className="trip-heading"><span className="eyebrow">YOUR NEXT JOURNEY</span><h1>{p.title || "正在整理你的旅行灵感"}</h1><p><MapPin size={14} /> {p.city || "目的地识别中"}<span>·</span>{days.length} 天<span>·</span>{p.places.length} 个地点</p></div>
          <div className="day-tabs" role="tablist" aria-label="行程天数">{days.map(d => <button key={d} role="tab" aria-selected={day === d} onClick={() => { setSelectedDay(d); setSelectedPlace(null); }} className={day === d ? "active" : ""}><span className={`day-dot day-${d % 4}`} />Day {d}<small>{p.places.filter(place => place.day === d).length}</small></button>)}</div>
          {p.error && <div className="error-message" role="alert">{p.error}</div>}
          {busy && <div className="working-message" role="status"><Loader2 size={17} className="animate-spin" />{p.progress || "正在整理行程…"}</div>}
          {p.phase !== "route" && (active.length > 0 ? <div className="day-column"><div className="day-heading"><span className={`day-badge day-${(day ?? 1) % 4}`}>DAY {day}</span><span>{active.filter(place => !place.skipped).length} 站，串起今天的风景</span></div><div className="place-timeline">{active.map((place, i) => <div key={place.id} className="timeline-item"><PlaceCard place={place} photo={p.photos[String(place.id)]} onUpdate={p.onUpdate} selected={selectedPlace === place.id} onSelect={() => setSelectedPlace(place.id)} />{i < active.length - 1 && <div className="timeline-connector"><ArrowDown size={12} /><span>下一站</span></div>}</div>)}</div><div className="day-ending"><span /><Compass size={14} /> 把时间留给沿途的惊喜</div></div> : !busy && <div className="empty-planning"><MapPin size={30} /><h2>还没有可展示的地点</h2><p>可以在左侧提交一篇攻略开始。</p></div>)}
          {p.children}
        </div>
        {p.phase === "confirm" && <div className="confirm-bar"><div><strong>确认好每一站了吗？</strong><span>生成前，你可以继续调整地点。</span></div><button className="black-button" onClick={p.onConfirm} disabled={busy || !mapped.length}>确认并生成动线 <ArrowUpRight size={17} /></button></div>}
      </main>
      <aside className={`map-panel ${mobileTab === "list" ? "mobile-hidden" : ""}`}>
        <div className="map-top"><span><Map size={16} /> 地图预览</span><span className="map-day">Day {day || "—"}</span></div>
        {mapped.length ? <MapView key={`${p.tripId}-${day}-${mobileTab}`} points={mapped.map(place => ({ name: place.name, lat: place.lat ?? null, lng: place.lng ?? null }))} mapUrl={`/api/v1/trips/${p.tripId}/map?day=${day}`} focusPoint={focused && { name: focused.name, lat: focused.lat ?? null, lng: focused.lng ?? null }} /> : <div className="map-empty"><Map size={35} /><strong>下一站，即将出现</strong><span>地点定位完成后，在这里查看地图</span></div>}
        <div className="map-summary"><span className="eyebrow">DAY {day || "—"} · EXPLORE</span><h2>{focused?.name || `${p.city || "这座城市"}，慢慢走`}</h2><p>{focused?.poi_address || `已定位 ${mapped.length} 个地点，点选行程卡片查看位置。`}</p><div className="map-place-chips">{mapped.slice(0, 3).map(place => <button onClick={() => setSelectedPlace(place.id)} key={place.id}>{place.name}<ChevronRight size={12} /></button>)}</div><small>连线为地点顺序示意；实际道路请以导航为准。</small></div>
      </aside>
      <nav className="mobile-view-tabs" aria-label="切换行程视图"><button className={mobileTab === "list" ? "active" : ""} onClick={() => setMobileTab("list")}><ListChecks size={16} /> 行程清单</button><button className={mobileTab === "map" ? "active" : ""} onClick={() => setMobileTab("map")}><Map size={16} /> 地图预览</button></nav>
    </div>}
  </div>;
}
