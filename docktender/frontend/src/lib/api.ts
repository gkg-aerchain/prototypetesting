// API client — talks to the FastAPI backend. Token is kept in localStorage; the
// (app) layout gates on it. All calls are org-scoped server-side.

export const API_BASE =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const TOKEN_KEY = "dt-token";

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(TOKEN_KEY);
}
export function setToken(t: string) {
  window.localStorage.setItem(TOKEN_KEY, t);
}
export function clearToken() {
  window.localStorage.removeItem(TOKEN_KEY);
}

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function req<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(init.headers as Record<string, string>),
  };
  const token = getToken();
  if (token) headers["Authorization"] = `Bearer ${token}`;
  const res = await fetch(`${API_BASE}${path}`, { ...init, headers });
  if (res.status === 204) return undefined as T;
  const text = await res.text();
  const body = text ? JSON.parse(text) : null;
  if (!res.ok) {
    const detail = body?.detail || res.statusText;
    throw new ApiError(res.status, typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  return body as T;
}

export const api = {
  get: <T>(p: string) => req<T>(p),
  post: <T>(p: string, body?: unknown) =>
    req<T>(p, { method: "POST", body: body ? JSON.stringify(body) : undefined }),
  patch: <T>(p: string, body?: unknown) =>
    req<T>(p, { method: "PATCH", body: body ? JSON.stringify(body) : undefined }),
  del: <T>(p: string) => req<T>(p, { method: "DELETE" }),
};

// ------------------------------------------------------------------ types
export interface Me {
  id: string; email: string; full_name: string; role: string;
  accent: string; theme: string; org_id: string; org: string; vessel_count: number;
}

export interface DockingWindow {
  window_start: string | null; hard_stop: string | null;
  days_left: number | null; driver: string; severity: string; edd_note: string | null;
}

export interface VesselStatus {
  id: string; name: string; sub: string; driver: string;
  hard_stop: string | null; window_start: string | null; days_left: number | null;
  severity: string; in_dock: boolean; category: string; pill: string; pill_kind: string;
  link: string | null;
}

export interface AgentEventDto {
  id: string; agent: string; agent_label: string; severity: string;
  vessel: string | null; message: string; evidence: string;
  needs_decision: boolean; age: string; link: string | null;
}

export interface Stat {
  key: string; label: string; value: number; sub: string; unit?: string;
}

export interface Programme {
  today: string; org: string; vessel_count: number; docking_count: number;
  waterline: VesselStatus[]; fleet_clock: VesselStatus[];
  focus: { vessel: string; driver: string; days_left: number; hard_stop: string; sub: string; link: string | null } | null;
  stats: Stat[]; queue: AgentEventDto[]; feed: AgentEventDto[];
}

export interface Vessel {
  id: string; name: string; vessel_type: string; dwt: number; loa_m: number;
  beam_m: number; summer_draft_m: number; gt: number; built_year: number;
  class_society: string; last_docking_date: string | null; last_docking_yard: string;
  special_survey_no: number; uwild_ok: boolean; edd_enrolled: boolean;
  tce_usd_day: number; notes: string; window: DockingWindow;
}

export interface WorkItem {
  id: string; code: string; section: number; section_name: string; title: string;
  uom: string; norm_value: number; norm_unit: string; norm_basis: string;
  factors: Record<string, unknown>; typical: boolean;
}

export interface TenderSummary {
  id: string; ref: string; status: string; vessel: string; vessel_type: string;
  spec_id: string; spec_title: string; deadline: string | null;
  offhire_usd_day: number; bids: number; invited: number;
}

export interface Invitation {
  yard_id: string; yard: string; region: string; status: string; has_bid: boolean;
}
export interface Clarification {
  id: string; question: string; answer: string; addendum_no: number | null; published: boolean;
}
export interface TenderDetail extends TenderSummary {
  invitations: Invitation[]; clarifications: Clarification[]; sealed_bids_hidden: boolean;
}

export interface TecFlag { kind: string; text: string; }
export interface TecCard {
  bid_id: string; rank: number; recommended: boolean; yard: string; dock: string;
  slot: string; tec_usd: number; sticker_usd: number; dock_days: number;
  composition: { key: string; usd: number; color: string }[];
  deviation_nm: number; flags: TecFlag[]; note: string; lowest_sticker: boolean;
}
export interface MatrixCell {
  bid_id: string; amount: number | null; state: string; flag: string | null; best: boolean;
}
export interface MatrixRow { section: number; name: string; cells: MatrixCell[]; }
export interface Leveling {
  tender_ref: string; spec_line_count: number; fx_date: string | null; offhire_usd_day: number;
  legend: { key: string; label: string; color: string }[];
  cards: TecCard[];
  matrix: { columns: { bid_id: string; yard: string }[]; rows: MatrixRow[] };
  exposure: { bid_id: string; yard: string; total_usd: number; items: { label: string; kind: string; exposure_usd: number }[] }[];
}

export interface SpecSummary {
  id: string; title: string; status: string; version: number; vessel: string;
  vessel_type: string; items: number; sections_covered: number; sections_total: number;
  pct_complete: number; frozen_at: string | null;
}
export interface SpecItemDto {
  id: string; line_no: number; title: string; qty: number; uom: string; qty_tbc: boolean;
  origin: string; notes: string; code: string | null; section: number | null;
  section_name: string | null; norm_value: number | null; norm_unit: string | null;
  norm_basis: string | null;
}
export interface SpecDetail extends SpecSummary {
  item_list: SpecItemDto[];
}

export interface DockDto {
  id: string; name: string; kind: string; length_m: number; beam_m: number;
  depth_over_blocks_m: number; max_dwt: number; cranes: number[];
  fits?: boolean; margins?: { loa_m: number; beam_m: number; depth_m: number; docking_draft_m: number };
}
export interface YardDto {
  id: string; name: string; country: string; region: string; labor_rate_band: string;
  lat: number; lon: number; notes: string; docks: DockDto[]; fits?: boolean;
  scores?: { docking_ref: string; growth_pct: number; overrun_days: number; quality: number; hse: number; notes: string }[];
}
