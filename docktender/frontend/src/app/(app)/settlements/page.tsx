"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { fmtM, fmtUsd } from "@/lib/format";

interface Account {
  award_id: string; tender_ref: string; vessel: string; yard: string;
  quoted_usd: number; final_usd: number; growth_pct: number;
  lines: { section: string; quoted: number; final: number }[];
}
interface Scorecard {
  yard: string; region: string; dockings: number; avg_growth_pct: number;
  avg_overrun_days: number; quality: number; hse: number;
}
interface SettlementsData {
  accounts: Account[]; scorecards: Scorecard[]; kpi: { avg_growth_pct: number; settled_count: number };
}

export default function SettlementsPage() {
  const [d, setD] = useState<SettlementsData | null>(null);
  useEffect(() => { api.get<SettlementsData>("/api/settlements").then(setD).catch(() => setD(null)); }, []);

  if (!d) return <div className="skel" style={{ height: 300 }} />;

  return (
    <>
      <div className="stage-head">
        <div><h1>Settlements</h1><div className="sub">Final-account reconciliation and yard performance</div></div>
      </div>

      <div className="focus-strip" style={{ gridTemplateColumns: "1fr 1fr 1fr 1fr", marginBottom: 20 }}>
        <div className="stat"><div className="k-label">Avg final vs quoted</div>
          <div className="k-value">+{d.kpi.avg_growth_pct}<small> %</small></div>
          <div className="k-sub">across {d.kpi.settled_count} settled dockings</div></div>
        <div className="stat"><div className="k-label">Settled dockings</div>
          <div className="k-value">{d.kpi.settled_count}</div><div className="k-sub">final accounts closed</div></div>
        <div className="stat"><div className="k-label">Yards benchmarked</div>
          <div className="k-value">{d.scorecards.length}</div><div className="k-sub">with docking history</div></div>
        <div className="stat"><div className="k-label">Best growth</div>
          <div className="k-value">+{d.scorecards[0]?.avg_growth_pct ?? 0}<small> %</small></div>
          <div className="k-sub">{d.scorecards[0]?.yard.split(" ")[0] ?? "—"}</div></div>
      </div>

      <div className="ov-cols">
        <div className="panel">
          <div className="panel-head"><h2>Final accounts</h2></div>
          {d.accounts.length === 0 ? (
            <div style={{ padding: 16, fontSize: 13, color: "var(--ink-3)" }}>No settled dockings yet.</div>
          ) : d.accounts.map((a) => (
            <div key={a.award_id} style={{ padding: "14px 18px", borderBottom: "1px solid var(--hairline)" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
                <div><b style={{ fontWeight: 600 }}>{a.vessel}</b> <span style={{ color: "var(--ink-3)", fontSize: 12 }}>· {a.yard}</span></div>
                <span className="mono" style={{ fontWeight: 600, color: a.growth_pct > 8 ? "var(--warn)" : "var(--ink)" }}>+{a.growth_pct}%</span>
              </div>
              <div style={{ display: "flex", gap: 20, marginTop: 6, fontSize: 12.5 }}>
                <span style={{ color: "var(--ink-2)" }}>Quoted <span className="mono">{fmtM(a.quoted_usd)} M</span></span>
                <span style={{ color: "var(--ink-2)" }}>Final <span className="mono">{fmtM(a.final_usd)} M</span></span>
                <span style={{ color: "var(--ink-3)" }}>+{fmtUsd(a.final_usd - a.quoted_usd)} in variations</span>
              </div>
            </div>
          ))}
        </div>

        <div className="panel">
          <div className="panel-head"><h2>Yard scorecards</h2></div>
          <div className="scrollx">
            <table className="grid">
              <thead><tr><th>Yard</th><th className="num">Growth</th><th className="num">Q</th><th className="num">HSE</th></tr></thead>
              <tbody>
                {d.scorecards.map((s) => (
                  <tr key={s.yard}>
                    <td><b style={{ fontWeight: 600, fontSize: 12.5 }}>{s.yard}</b>
                      <div className="mono" style={{ fontSize: 10.5, color: "var(--ink-3)" }}>{s.dockings} dockings · {s.region}</div></td>
                    <td className="num"><span className={s.avg_growth_pct > 10 ? "delta hi" : "delta lo"}>+{s.avg_growth_pct}%</span></td>
                    <td className="num">{s.quality}</td>
                    <td className="num">{s.hse}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </>
  );
}
