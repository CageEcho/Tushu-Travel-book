export type TaskStatus = "pending" | "running" | "done" | "failed";

export interface Task {
  id: string;
  trip_id: string;
  kind: string;
  status: TaskStatus;
  progress?: string | null;
  error?: string | null;
  result_path?: string | null;
}

export interface Candidate {
  name: string;
  uid?: string | null;
  address?: string | null;
  lat?: number | null;
  lng?: number | null;
}

export interface Place {
  id: number;
  day: number;
  seq: number;
  name: string;
  type: string;
  source_text?: string | null;
  confirmed: boolean;
  skipped: boolean;
  poi_name?: string | null;
  poi_uid?: string | null;
  poi_address?: string | null;
  lat?: number | null;
  lng?: number | null;
  geocode_status: string;
  candidates?: Candidate[] | null;
}

export interface Trip {
  id: string;
  source_link: string;
  note_id?: string | null;
  title?: string | null;
  city?: string | null;
  status: string;
  created_at?: string | null;
}

export interface PlacesResponse {
  trip_id: string;
  status: string;
  title?: string | null;
  city?: string | null;
  places: Place[];
}

export interface RouteSegment {
  from_place: string;
  to_place: string;
  mode: string;
  distance_m: number;
  duration_s: number;
  duration_text: string;
}

export interface RouteDay {
  day: number;
  places: Place[];
  segments: RouteSegment[];
  map_url: string;
}

export interface RouteResponse {
  trip_id: string;
  days: RouteDay[];
}

export interface NavLeg {
  leg: number;
  from_place: string;
  to_place: string;
  via: string[];
  uri: string;
  web_uri: string;
  web_basic_uri: string;
}

export interface NavLink {
  uri: string;
  web_uri: string;
}

// 公交 / 步行 / 骑行逐段链接（百度这三种方式不支持途经点）
export interface NavSegment {
  from_place: string;
  to_place: string;
  transit: NavLink;
  walking: NavLink;
  riding: NavLink;
}

export interface NavDay {
  day: number;
  legs: NavLeg[];
  segments: NavSegment[];
}

export interface AppNavResponse {
  max_via: number;
  uris: string[];
  days: NavDay[];
}

// 推荐住宿：每天最后一站附近，经济 / 舒适 / 高端各一家，档次与评分来自百度地点检索（无价格）
export interface Hotel {
  tier: "budget" | "comfort" | "premium";
  tier_label: string;
  grade?: string | null;
  name: string;
  uid?: string | null;
  address?: string | null;
  rating: number;
  comment_num: number;
  distance_m: number;
  lat: number;
  lng: number;
  link: NavLink;
}

export interface HotelDay {
  day: number;
  anchor: { name: string; lat: number; lng: number };
  hotels: Hotel[];
}

export interface HotelsResponse {
  trip_id: string;
  days: HotelDay[];
}

// 地点实景图：百度百科词条首图，由后端下载缓存后提供；没找到可靠图片的地点不在 photos 里
export interface PlacePhoto {
  src: string;
  title?: string | null;
  source_url?: string | null;
}

export interface PhotosResponse {
  trip_id: string;
  photos: Record<string, PlacePhoto>;
}
