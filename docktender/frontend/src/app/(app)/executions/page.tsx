"use client";
import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";
import { fmtUsd } from "@/lib/format";

interface VO {
  id: string; vo_no: string; title: string; qty: number; uom: string;
  proposed_usd: number; tariff_line_ref: string | null; tariff_usd: number | null;
  over_tariff_usd: number | null; state: string; decided_by: string | null;
}
interface Execution {
  award_id: string; tender_ref: string; vessel: string; yard: string;
  in_dock: boolean; dock_day: number; dock_total: number;
  vo_count: number; vo_open: number; vo_approved_usd: number; vos: VO[];
}

const VO_PILL: Record<string, string> = { proposed: "warn", approved: "good", disputed: "crit", rejected: "neutral" };

export default function ExecutionsPage() {
  const [execs, setExecs] = useState<Execution[] | null>(null);
  const load = useCallback(() => api.get<Execution[]>("/api/executions").then(setExecs).catch(() => setExecs([])), []);
  useEffect(() => { load(); }, [load]);

  async function decide(voId: string, state: string) {
    await api.patch(`/api/vos/${voId}`, { state, reason: "" });
    load();
  }

  if (!execs) return <div className="skel" style={{ height: 300 }} />;

  return (
    <>
      <div className="stage-head">
        <div><h1>Executions</h1><div className="sub">Live dockings and variation-order control</div></div>
      </div>
      {execs.length === 0 ? (
        <div className="empty"><h3>No active dockings</h3><p>Awarded dockings appear here until their final account is closed.</p></div>
      ) : execs.map((ex) => (
        <div key={ex.award_id} style={{ marginBottom: 24 }}>
          <div className="panel" style={{ marginBottom: 12 }}>
            <div style={{ padding: "16px 18px", display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 12 }}>
              <div>
                <div style={{ fontWeight: 600, fontSize: 15 }}>{ex.vessel} <span style={{ color: "var(--ink-3)", fontWeight: 400 }}>· {ex.yard}</span></div>
                <div className="mono" style={{ fontSize: 11.5, color: "var(--ink-3)", marginTop: 2 }}>{ex.tender_ref}</div>
              </div>
              {ex.in_dock && (
                <div style={{ minWidth: 220 }}>
                  <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12, marginBottom: 4 }}>
                    <span className="pill warn">In dock · day {ex.dock_day}/{ex.dock_total}</span>
                    <span className="mono" style={{ color: "var(--ink-3)" }}>{Math.round(ex.dock_day / ex.dock_total * 100)}%</span>
                  </div>
                  <div className="progress-bar"><i style={{ width: `${ex.dock_day / ex.dock_total * 100}%` }} /></div>
                </div>
              )}
              <div style={{ textAlign: "right" }}>
                <div className="mono" style={{ fontSize: 18, fontWeight: 500 }}>{fmtUsd(ex.vo_approved_usd)}</div>
                <div style={{ fontSize: 11.5, color: "var(--ink-3)" }}>{ex.vo_count} VOs · {ex.vo_open} open</div>
              </div>
            </div>
          </div>

          <div className="panel">
            <div className="panel-head"><h2>Variation orders</h2></div>
            <div className="scrollx">
              <table className="grid">
                <thead>
                  <tr><th>VO</th><th>Title</th><th className="num">Proposed</th><th className="num">Tariff</th><th className="num">Δ vs tariff</th><th>State</th><th></th></tr>
                </thead>
                <tbody>
                  {ex.vos.map((v) => (
                    <tr key={v.id}>
                      <td className="mono" style={{ fontSize: 12 }}>{v.vo_no}</td>
                      <td>{v.title}</td>
                      <td className="num">{fmtUsd(v.proposed_usd)}</td>
                      <td className="num">{v.tariff_usd != null ? fmtUsd(v.tariff_usd) : <span className="delta hi">no tariff</span>}</td>
                      <td className="num">
                        {v.over_tariff_usd != null && v.over_tariff_usd !== 0 ? (
                          <span className={`delta ${v.over_tariff_usd > 0 ? "hi" : "lo"}`}>
                            {v.over_tariff_usd > 0 ? "+" : ""}{fmtUsd(v.over_tariff_usd)}
                          </span>
                        ) : "—"}
                      </td>
                      <td><span className={`pill ${VO_PILL[v.state]}`}>{v.state}</span></td>
                      <td style={{ textAlign: "right" }}>
                        {(v.state === "proposed" || v.state === "disputed") && (
                          <span style={{ display: "inline-flex", gap: 6 }}>
                            <button className="btn btn-quiet" style={{ padding: "3px 10px", fontSize: 12 }} onClick={() => decide(v.id, "approved")}>Approve</button>
                            <button className="btn btn-quiet" style={{ padding: "3px 10px", fontSize: 12 }} onClick={() => decide(v.id, "disputed")}>Dispute</button>
                          </span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      ))}
    </>
  );
}
