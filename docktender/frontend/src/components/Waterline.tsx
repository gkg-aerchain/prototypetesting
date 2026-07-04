"use client";
import { useRouter } from "next/navigation";
import { VesselStatus } from "@/lib/api";

// Geometry (matches the approved design_direction.html signature element).
const VB_W = 1040;
const VB_H = 176;
const LEFT = 34;
const RIGHT = 1012;
const WATERLINE_Y = 92;
const SEA_H = 28;
const BAND_Y = 86;
const BAND_H = 12;
const HORIZON_MONTHS = 18;

function monthStart(d: Date): Date {
  return new Date(d.getFullYear(), d.getMonth(), 1);
}
function addMonths(d: Date, m: number): Date {
  return new Date(d.getFullYear(), d.getMonth() + m, d.getDate());
}

export function Waterline({ today, vessels }: { today: string; vessels: VesselStatus[] }) {
  const router = useRouter();
  const t0 = new Date(today);
  const start = monthStart(t0);
  const end = addMonths(start, HORIZON_MONTHS);
  const span = end.getTime() - start.getTime();

  const x = (iso: string | Date): number => {
    const d = typeof iso === "string" ? new Date(iso) : iso;
    const f = (d.getTime() - start.getTime()) / span;
    return LEFT + Math.max(0, Math.min(1, f)) * (RIGHT - LEFT);
  };

  // Month gridlines every 2 months; year suffix on January / first tick.
  const ticks: { x: number; label: string }[] = [];
  for (let i = 0; i <= HORIZON_MONTHS; i += 2) {
    const d = addMonths(start, i);
    const mon = d.toLocaleDateString("en-GB", { month: "short" }).toUpperCase();
    const yr = d.getFullYear().toString().slice(2);
    ticks.push({ x: x(d), label: i === 0 || d.getMonth() === 0 ? `${mon} ${yr}` : mon });
  }

  const todayX = x(t0);
  const upcoming = vessels.filter((v) => v.category === "upcoming" && v.hard_stop);
  const inDock = vessels.filter((v) => v.category === "in_dock");

  // Selective labelling: label a vessel only if far enough from the last labelled one.
  const sorted = [...upcoming].sort((a, b) => x(a.hard_stop!) - x(b.hard_stop!));
  let lastLabel = -999;
  const labelled = new Set<string>();
  for (const v of sorted) {
    const vx = x(v.hard_stop!);
    if (vx - lastLabel >= 118) {
      labelled.add(v.id);
      lastLabel = vx;
    }
  }

  function bandColor(v: VesselStatus, idx: number): { fill: string; opacity: number } {
    if (v.severity === "signal") return { fill: "var(--signal)", opacity: 1 };
    return { fill: "var(--steel)", opacity: Math.max(0.4, 0.72 - idx * 0.08) };
  }

  return (
    <div className="waterline-panel">
      <div className="wl-head">
        <h2>The waterline · 18 months</h2>
        <div className="key">
          <span><i style={{ background: "var(--signal)" }} />Window closing</span>
          <span><i style={{ background: "var(--steel)" }} />Docking window</span>
          <span><i style={{ background: "var(--chrome)" }} />In dock</span>
        </div>
      </div>
      <svg className="waterline" viewBox={`0 0 ${VB_W} ${VB_H}`} role="img"
           aria-label="Fleet docking timeline over the next 18 months">
        {/* month grid */}
        <g fontFamily="Geist Mono, monospace" fontSize="9.5" fill="var(--ink-3)" textAnchor="middle">
          {ticks.map((tk, i) => (
            <g key={i}>
              <line x1={tk.x} y1={26} x2={tk.x} y2={120} stroke="var(--hairline)" />
              <text x={tk.x} y={136}>{tk.label}</text>
            </g>
          ))}
        </g>

        {/* sea below the waterline */}
        <rect x="0" y={WATERLINE_Y} width={VB_W} height={SEA_H} fill="var(--sea)" />
        <line x1="0" y1={WATERLINE_Y} x2={VB_W} y2={WATERLINE_Y} stroke="var(--steel)" strokeWidth="1.5" />

        {/* window bands */}
        {sorted.map((v, i) => {
          const x1 = v.window_start ? x(v.window_start) : x(v.hard_stop!) - 60;
          const x2 = x(v.hard_stop!);
          const c = bandColor(v, i);
          return (
            <rect key={`band-${v.id}`} x={x1} y={BAND_Y} width={Math.max(8, x2 - x1)} height={BAND_H}
                  rx="2" fill={c.fill} opacity={c.opacity} />
          );
        })}

        {/* vessels above the line */}
        {sorted.map((v) => {
          const vx = x(v.hard_stop!);
          const isSignal = v.severity === "signal";
          const stroke = isSignal ? "var(--signal)" : "var(--steel)";
          const show = labelled.has(v.id);
          return (
            <g key={`v-${v.id}`} style={{ cursor: "pointer" }}
               onClick={() => router.push(v.link || "/tenders")}>
              <line x1={vx} y1={60} x2={vx} y2={84} stroke={stroke} strokeWidth={isSignal ? 1.4 : 1.2} />
              <circle cx={vx} cy={86} r={isSignal ? 3.4 : 3.2} fill={stroke} />
              {show && (
                <>
                  <text x={vx} y={42} textAnchor="middle" fontWeight="600" fontSize="11.5"
                        fontFamily="Geist, sans-serif" fill="var(--ink)">{v.name}</text>
                  <text x={vx} y={56} textAnchor="middle" fontFamily="Geist Mono, monospace"
                        fontSize="9.5" fill={isSignal ? "var(--signal-deep)" : "var(--ink-3)"}>
                    {waterlineSub(v)}
                  </text>
                </>
              )}
            </g>
          );
        })}

        {/* in-dock vessels below the line */}
        {inDock.map((v, i) => {
          const cx = todayX + 8 + i * 132;
          const label = `${v.name} · ${dockDayLabel(v.pill)}`;
          const w = Math.max(118, label.length * 6.0);
          return (
            <g key={`dock-${v.id}`} style={{ cursor: "pointer" }}
               onClick={() => router.push(v.link || "/executions")}>
              <rect x={cx} y={100} width={w} height={16} rx="3" fill="var(--chrome)" />
              <text x={cx + w / 2} y={111.5} textAnchor="middle" fontFamily="Geist, sans-serif"
                    fontSize="10" fontWeight="600" fill="var(--chrome-ink)">{label}</text>
            </g>
          );
        })}

        {/* today */}
        <line x1={todayX} y1={18} x2={todayX} y2={122} stroke="var(--signal)" strokeWidth="2" />
        <text x={todayX + 6} y={24} fontFamily="Geist Mono, monospace" fontSize="9.5"
              fill="var(--signal-deep)">TODAY</text>
      </svg>
    </div>
  );
}

function waterlineSub(v: VesselStatus): string {
  if (v.severity === "signal" && v.hard_stop) {
    const d = new Date(v.hard_stop);
    const s = d.toLocaleDateString("en-GB", { day: "2-digit", month: "short" }).toUpperCase();
    const bids = v.pill.startsWith("Bids in") ? " · " + v.pill.replace("Bids in · ", "BIDS ").replace(" of ", "/") : "";
    return `CLOSES ${s}${bids}`;
  }
  return v.pill.toUpperCase();
}

function dockDayLabel(pill: string): string {
  // "In dock · day 6/13" -> "D6/13"
  const m = pill.match(/day (\d+)\/(\d+)/);
  return m ? `D${m[1]}/${m[2]}` : pill;
}
