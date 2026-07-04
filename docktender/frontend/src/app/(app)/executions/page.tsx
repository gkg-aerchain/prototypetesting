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
  vo_count: number; vo_open: number; vo_approved_usd: number; settled: boolean; vos: VO[];
}

const VO_PILL: Record<string, string> = { proposed: "warn", approved: "good", disputed: "crit", rejected: "neutral" };

export default function ExecutionsPage() {
  const [execs, setExecs] = useState<Execution[] | null>(null);
  const [raise, setRaise] = useState<string | null>(null);
  const [reasonFor, setReasonFor] = useState<{ vo: VO; state: string } | null>(null);
  const load = useCallback(() => api.get<Execution[]>("/api/executions").then(setExecs).catch(() => setExecs([])), []);
  useEffect(() => { load(); }, [load]);

  async function decide(voId: string, state: string, reason = "") {
    await api.patch(`/api/vos/${voId}`, { state, reason });
    load();
  }
  async function settle(awardId: string) {
    if (!confirm("Close the final account for this docking? It moves to Settlements.")) return;
    await api.post(`/api/settlements/${awardId}/close`, {});
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
            <div className="panel-head">
              <h2>Variation orders</h2>
              <div style={{ display: "flex", gap: 8 }}>
                <button className="btn btn-quiet" style={{ padding: "5px 12px", fontSize: 12 }} onClick={() => setRaise(ex.award_id)}>Raise VO</button>
                <button className="btn btn-signal" style={{ padding: "5px 12px", fontSize: 12 }} disabled={ex.vo_open > 0} title={ex.vo_open > 0 ? "Resolve open VOs first" : ""} onClick={() => settle(ex.award_id)}>Settle final account</button>
              </div>
            </div>
            <div className="scrollx">
              <table className="grid">
                <thead>
                  <tr><th>VO</th><th>Title</th><th className="num">Proposed</th><th className="num">Tariff</th><th className="num">Δ vs tariff</th><th>State</th><th></th></tr>
                </thead>
                <tbody>
                  {ex.vos.length === 0 && <tr><td colSpan={7} style={{ color: "var(--ink-3)", fontSize: 13 }}>No variation orders raised.</td></tr>}
                  {ex.vos.map((v) => (
                    <tr key={v.id}>
                      <td className="mono" style={{ fontSize: 12 }}>{v.vo_no}</td>
                      <td>{v.title}{v.decided_by && <div style={{ fontSize: 11, color: "var(--ink-3)" }}>by {v.decided_by}</div>}</td>
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
                            {v.state !== "disputed" && <button className="btn btn-quiet" style={{ padding: "3px 10px", fontSize: 12 }} onClick={() => setReasonFor({ vo: v, state: "disputed" })}>Dispute</button>}
                            <button className="btn btn-quiet" style={{ padding: "3px 10px", fontSize: 12 }} onClick={() => setReasonFor({ vo: v, state: "rejected" })}>Reject</button>
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
      {raise && <RaiseVOModal awardId={raise} onClose={() => { setRaise(null); load(); }} />}
      {reasonFor && <ReasonModal vo={reasonFor.vo} state={reasonFor.state}
        onSubmit={(reason) => { decide(reasonFor.vo.id, reasonFor.state, reason); setReasonFor(null); }}
        onClose={() => setReasonFor(null)} />}
    </>
  );
}

function ReasonModal({ vo, state, onSubmit, onClose }: { vo: VO; state: string; onSubmit: (r: string) => void; onClose: () => void }) {
  const [reason, setReason] = useState("");
  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()} style={{ width: 480 }}>
        <h2>{state === "rejected" ? "Reject" : "Dispute"} {vo.vo_no}</h2>
        <p style={{ fontSize: 13, color: "var(--ink-2)", marginTop: 2 }}>{vo.title} · {fmtUsd(vo.proposed_usd)}{vo.over_tariff_usd ? ` · ${vo.over_tariff_usd > 0 ? "+" : ""}${fmtUsd(vo.over_tariff_usd)} vs tariff` : ""}</p>
        <div className="field" style={{ marginTop: 8 }}>
          <label>Reason (recorded on the audit trail)</label>
          <textarea rows={3} value={reason} onChange={(e) => setReason(e.target.value)} placeholder={state === "rejected" ? "Out of contracted scope…" : "Query the rate against the captured tariff…"} />
        </div>
        <div style={{ display: "flex", gap: 10, marginTop: 16, justifyContent: "flex-end" }}>
          <button className="btn btn-quiet" onClick={onClose}>Cancel</button>
          <button className="btn btn-signal" disabled={!reason.trim()} onClick={() => onSubmit(reason)}>{state === "rejected" ? "Reject VO" : "Dispute VO"}</button>
        </div>
      </div>
    </div>
  );
}

function RaiseVOModal({ awardId, onClose }: { awardId: string; onClose: () => void }) {
  const [f, setF] = useState({ title: "", qty: "", uom: "", proposed_usd: "", tariff_usd: "" });
  const [busy, setBusy] = useState(false);
  function set(k: string, v: string) { setF({ ...f, [k]: v }); }
  async function submit() {
    setBusy(true);
    try {
      await api.post(`/api/executions/${awardId}/vos`, {
        title: f.title, qty: Number(f.qty) || 0, uom: f.uom,
        proposed_usd: Number(f.proposed_usd) || 0,
        tariff_usd: f.tariff_usd ? Number(f.tariff_usd) : null,
      });
      onClose();
    } catch (e) { alert((e as Error).message); setBusy(false); }
  }
  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()} style={{ width: 520 }}>
        <h2>Raise a variation order</h2>
        <p style={{ fontSize: 13, color: "var(--ink-2)", marginTop: 2 }}>Price it against the yard&rsquo;s captured tariff to surface any over-tariff exposure.</p>
        <div className="field" style={{ marginTop: 8 }}><label>Title</label><input value={f.title} onChange={(e) => set("title", e.target.value)} placeholder="Additional steel renewal — frame 42" /></div>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, marginTop: 12 }}>
          <div className="field"><label>Qty</label><input type="number" value={f.qty} onChange={(e) => set("qty", e.target.value)} /></div>
          <div className="field"><label>Unit</label><input value={f.uom} onChange={(e) => set("uom", e.target.value)} placeholder="t / m² / lot" /></div>
          <div className="field"><label>Proposed (USD)</label><input type="number" value={f.proposed_usd} onChange={(e) => set("proposed_usd", e.target.value)} /></div>
          <div className="field"><label>Tariff (USD)</label><input type="number" value={f.tariff_usd} onChange={(e) => set("tariff_usd", e.target.value)} placeholder="from captured tariff" /></div>
        </div>
        <div style={{ display: "flex", gap: 10, marginTop: 18, justifyContent: "flex-end" }}>
          <button className="btn btn-quiet" onClick={onClose}>Cancel</button>
          <button className="btn btn-signal" disabled={busy || !f.title.trim()} onClick={submit}>{busy ? "Saving…" : "Raise VO"}</button>
        </div>
      </div>
    </div>
  );
}
