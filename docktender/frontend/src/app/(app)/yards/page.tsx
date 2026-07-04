"use client";
import { useCallback, useEffect, useState } from "react";
import { api, TenderSummary, Vessel, YardDto } from "@/lib/api";
import { fmtDate } from "@/lib/format";

const REGIONS = [
  { k: "", label: "All regions" }, { k: "SEA", label: "SE Asia" }, { k: "MEast", label: "Middle East" },
  { k: "ISC", label: "India subcont." }, { k: "FarEast", label: "Far East" }, { k: "Med", label: "Mediterranean" },
  { k: "NEur", label: "N. Europe" }, { k: "Am", label: "Americas" },
];

export default function YardsPage() {
  const [region, setRegion] = useState("");
  const [vesselId, setVesselId] = useState("");
  const [fitsOnly, setFitsOnly] = useState(false);
  const [fleet, setFleet] = useState<Vessel[]>([]);
  const [yards, setYards] = useState<YardDto[] | null>(null);

  useEffect(() => { api.get<Vessel[]>("/api/fleet").then(setFleet); }, []);

  useEffect(() => {
    const p = new URLSearchParams();
    if (region) p.set("region", region);
    if (vesselId) p.set("vessel_id", vesselId);
    if (fitsOnly && vesselId) p.set("fits_only", "true");
    api.get<YardDto[]>(`/api/yards?${p}`).then(setYards);
  }, [region, vesselId, fitsOnly]);

  const vessel = fleet.find((v) => v.id === vesselId);
  const [openYard, setOpenYard] = useState<string | null>(null);

  return (
    <>
      <div className="stage-head">
        <div><h1>Yards</h1><div className="sub">Repair-yard directory with physical-fit filtering</div></div>
      </div>

      <div style={{ display: "flex", gap: 12, marginBottom: 18, flexWrap: "wrap", alignItems: "flex-end" }}>
        <div className="field" style={{ width: 180 }}>
          <label>Region</label>
          <select value={region} onChange={(e) => setRegion(e.target.value)}>
            {REGIONS.map((r) => <option key={r.k} value={r.k}>{r.label}</option>)}
          </select>
        </div>
        <div className="field" style={{ width: 220 }}>
          <label>Fits vessel</label>
          <select value={vesselId} onChange={(e) => setVesselId(e.target.value)}>
            <option value="">— none —</option>
            {fleet.map((v) => <option key={v.id} value={v.id}>{v.name} ({v.vessel_type})</option>)}
          </select>
        </div>
        {vesselId && (
          <label style={{ display: "flex", gap: 6, alignItems: "center", fontSize: 13, paddingBottom: 9 }}>
            <input type="checkbox" checked={fitsOnly} onChange={(e) => setFitsOnly(e.target.checked)} />
            Only yards that fit
          </label>
        )}
      </div>

      {vessel && (
        <div className="sub" style={{ marginBottom: 12 }}>
          {vessel.name}: LOA {vessel.loa_m} m · beam {vessel.beam_m} m · summer draft {vessel.summer_draft_m} m
        </div>
      )}

      {!yards ? (
        <div className="skel" style={{ height: 300 }} />
      ) : (
        <div className="card-grid" style={{ gridTemplateColumns: "repeat(auto-fill, minmax(340px, 1fr))" }}>
          {yards.map((y) => (
            <div key={y.id} className="panel yard-card" style={{ padding: 0 }} onClick={() => setOpenYard(y.id)}>
              <div style={{ padding: "14px 18px", borderBottom: "1px solid var(--hairline)", display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                <div>
                  <div style={{ fontWeight: 600, fontSize: 14 }}>{y.name}</div>
                  <div className="mono" style={{ fontSize: 11, color: "var(--ink-3)", marginTop: 2 }}>{y.country} · {y.region} · {y.labor_rate_band} labour</div>
                </div>
                {vesselId && (
                  <span className={`pill ${y.fits ? "good" : "neutral"}`}>{y.fits ? "Fits" : "No fit"}</span>
                )}
              </div>
              <table className="grid" style={{ fontSize: 12 }}>
                <tbody>
                  {y.docks.map((d) => (
                    <tr key={d.id}>
                      <td>
                        <b style={{ fontWeight: 600 }}>{d.name}</b>
                        <span className="mono" style={{ fontSize: 10.5, color: "var(--ink-3)", marginLeft: 6 }}>{d.kind}</span>
                      </td>
                      <td className="num mono" style={{ fontSize: 11 }}>{d.length_m}×{d.beam_m} m</td>
                      <td style={{ textAlign: "right" }}>
                        {vesselId && d.margins && (
                          <span className={`xchip ${d.fits ? "ok" : "neutral"}`} style={{ fontSize: 10.5 }}>
                            L+{d.margins.loa_m} B+{d.margins.beam_m}
                          </span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <div className="yard-card-foot">Details &amp; invite →</div>
            </div>
          ))}
        </div>
      )}
      {openYard && <YardDrawer yardId={openYard} vesselId={vesselId} onClose={() => setOpenYard(null)} />}
    </>
  );
}

function YardDrawer({ yardId, vesselId, onClose }: { yardId: string; vesselId: string; onClose: () => void }) {
  const [y, setY] = useState<YardDto | null>(null);
  const [tenders, setTenders] = useState<TenderSummary[]>([]);
  const [msg, setMsg] = useState<string | null>(null);

  const load = useCallback(() => {
    const p = new URLSearchParams(); if (vesselId) p.set("vessel_id", vesselId);
    api.get<YardDto>(`/api/yards/${yardId}?${p}`).then(setY);
  }, [yardId, vesselId]);
  useEffect(load, [load]);
  useEffect(() => { api.get<TenderSummary[]>("/api/tenders").then((ts) => setTenders(ts.filter((t) => t.status === "draft" || t.status === "issued"))); }, []);

  async function invite(tid: string, ref: string) {
    try { await api.post(`/api/tenders/${tid}/invite`, { yard_ids: [yardId] }); setMsg(`Invited to ${ref}.`); }
    catch (e) { setMsg((e as Error).message); }
  }

  if (!y) return <div className="drawer-backdrop" onClick={onClose}><div className="drawer" onClick={(e) => e.stopPropagation()}><div className="skel" style={{ height: 300 }} /></div></div>;
  const scores = y.scores || [];

  return (
    <div className="drawer-backdrop" onClick={onClose}>
      <div className="drawer" onClick={(e) => e.stopPropagation()}>
        <span className="eyebrow">{y.region} · {y.labor_rate_band} labour</span>
        <h2 style={{ marginTop: 6 }}>{y.name}</h2>
        <div className="sub" style={{ marginBottom: 16 }}>{y.country} · {y.docks.length} docks</div>

        <div className="eyebrow dim" style={{ marginBottom: 8 }}>Docks</div>
        <div className="panel" style={{ marginBottom: 18 }}>
          <table className="grid" style={{ fontSize: 12.5 }}>
            <thead><tr><th>Dock</th><th className="num">L × B</th><th className="num">Depth</th><th className="num">Max DWT</th></tr></thead>
            <tbody>
              {y.docks.map((d) => (
                <tr key={d.id}>
                  <td><b>{d.name}</b> <span className="mono" style={{ fontSize: 10.5, color: "var(--ink-3)" }}>{d.kind}</span>
                    {vesselId && d.fits != null && <span className={`pill ${d.fits ? "good" : "crit"}`} style={{ marginLeft: 8 }}>{d.fits ? "fits" : "no fit"}</span>}</td>
                  <td className="num">{d.length_m}×{d.beam_m} m</td>
                  <td className="num">{d.depth_over_blocks_m} m</td>
                  <td className="num">{d.max_dwt.toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="eyebrow dim" style={{ marginBottom: 8 }}>Performance history</div>
        {scores.length === 0 ? <div className="sub" style={{ marginBottom: 18 }}>No prior dockings recorded for this yard.</div> : (
          <div className="panel" style={{ marginBottom: 18 }}>
            <table className="grid" style={{ fontSize: 12.5 }}>
              <thead><tr><th>Docking</th><th className="num">Growth</th><th className="num">Overrun</th><th className="num">Quality</th><th className="num">HSE</th></tr></thead>
              <tbody>
                {scores.map((s, i) => (
                  <tr key={i}>
                    <td className="mono" style={{ fontSize: 11.5 }}>{s.docking_ref}</td>
                    <td className="num" style={{ color: s.growth_pct > 8 ? "var(--crit)" : s.growth_pct > 4 ? "var(--warn)" : "var(--good)" }}>+{s.growth_pct}%</td>
                    <td className="num">{s.overrun_days} d</td>
                    <td className="num">{s.quality}/5</td>
                    <td className="num">{s.hse}/5</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        <div className="eyebrow dim" style={{ marginBottom: 8 }}>Invite to a tender</div>
        {tenders.length === 0 ? <div className="sub">No open tenders. Create one from a frozen spec.</div> : (
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {tenders.map((t) => (
              <div key={t.id} className="invite-row" style={{ borderRadius: "var(--r-sm)", border: "1px solid var(--hairline)" }}>
                <div style={{ flex: 1 }}><b>{t.ref}</b> — {t.vessel} <span className="mono" style={{ fontSize: 11, color: "var(--ink-3)" }}>{t.status}</span>
                  <div style={{ fontSize: 11.5, color: "var(--ink-3)" }}>deadline {fmtDate(t.deadline)}</div></div>
                <button className="btn btn-quiet" style={{ padding: "5px 12px", fontSize: 12 }} onClick={() => invite(t.id, t.ref)}>Invite</button>
              </div>
            ))}
          </div>
        )}
        {msg && <div style={{ marginTop: 12, fontSize: 13, color: "var(--good)" }}>{msg}</div>}
      </div>
    </div>
  );
}
