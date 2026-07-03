"use client";
import { useEffect, useState } from "react";
import { api, Vessel, YardDto } from "@/lib/api";

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
            <div key={y.id} className="panel" style={{ padding: 0 }}>
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
            </div>
          ))}
        </div>
      )}
    </>
  );
}
