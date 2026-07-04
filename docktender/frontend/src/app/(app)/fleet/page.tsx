"use client";
import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api, Vessel } from "@/lib/api";
import { fmtDate } from "@/lib/format";

const TYPES = ["MR", "LR1", "LR2", "Aframax", "Suezmax", "VLCC", "Handysize", "Panamax"];

export default function FleetPage() {
  const router = useRouter();
  const [fleet, setFleet] = useState<Vessel[] | null>(null);
  const [adding, setAdding] = useState(false);

  const load = useCallback(() => { api.get<Vessel[]>("/api/fleet").then(setFleet); }, []);
  useEffect(load, [load]);

  async function startSpec(v: Vessel) {
    const s = await api.post<{ id: string }>("/api/specs", { vessel_id: v.id, title: `${v.name} — docking specification` });
    router.push(`/specifications/${s.id}`);
  }

  return (
    <>
      <div className="stage-head">
        <div><h1>Fleet</h1><div className="sub">{fleet?.length ?? 0} vessels · docking windows from the 36-month rule</div></div>
        <button className="btn btn-signal" onClick={() => setAdding(true)}>Add vessel</button>
      </div>

      {!fleet ? <div className="skel" style={{ height: 300 }} /> : fleet.length === 0 ? (
        <div className="empty"><h3>No vessels yet</h3><p>Add your first vessel to compute its docking window and start a specification.</p></div>
      ) : (
        <div className="panel">
          <div className="scrollx">
            <table className="grid">
              <thead><tr><th>Vessel</th><th>Class / SS</th><th className="num">Last docked</th><th className="num">Window closes</th><th></th></tr></thead>
              <tbody>
                {fleet.map((v) => {
                  const w = v.window;
                  const sig = w.severity === "signal";
                  return (
                    <tr key={v.id}>
                      <td><b>{v.name}</b><div className="mono" style={{ fontSize: 11, color: "var(--ink-3)" }}>{v.vessel_type} · {v.dwt.toLocaleString()} DWT · {v.loa_m}×{v.beam_m} m</div></td>
                      <td>{v.class_society || "—"} · SS {v.special_survey_no}<div style={{ fontSize: 11, color: "var(--ink-3)" }}>{w.driver}</div></td>
                      <td className="num">{fmtDate(v.last_docking_date)}</td>
                      <td className="num">{w.hard_stop ? <>{fmtDate(w.hard_stop)} · <b style={sig ? { color: "var(--signal-deep)" } : undefined}>{w.days_left}d</b></> : "—"}</td>
                      <td style={{ textAlign: "right" }}>
                        <button className="btn btn-quiet" style={{ padding: "5px 12px", fontSize: 12 }} onClick={() => startSpec(v)}>Start spec</button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
      {adding && <VesselModal onClose={() => { setAdding(false); load(); }} />}
    </>
  );
}

function VesselModal({ onClose }: { onClose: () => void }) {
  const [f, setF] = useState({
    name: "", vessel_type: "LR2", dwt: "", loa_m: "", beam_m: "", summer_draft_m: "",
    class_society: "", last_docking_date: "", special_survey_no: "2", uwild_ok: false, tce_usd_day: "",
  });
  const [busy, setBusy] = useState(false);
  function set(k: string, v: string | boolean) { setF({ ...f, [k]: v }); }

  async function submit() {
    setBusy(true);
    try {
      await api.post("/api/vessels", {
        name: f.name, vessel_type: f.vessel_type, dwt: Number(f.dwt) || 0,
        loa_m: Number(f.loa_m) || 0, beam_m: Number(f.beam_m) || 0, summer_draft_m: Number(f.summer_draft_m) || 0,
        class_society: f.class_society, special_survey_no: Number(f.special_survey_no) || 1,
        uwild_ok: f.uwild_ok, tce_usd_day: Number(f.tce_usd_day) || 0,
        last_docking_date: f.last_docking_date ? new Date(f.last_docking_date).toISOString() : null,
      });
      onClose();
    } catch (e) { alert((e as Error).message); setBusy(false); }
  }

  const F = (label: string, k: keyof typeof f, type = "text") => (
    <div className="field"><label>{label}</label>
      <input type={type} value={f[k] as string} onChange={(e) => set(k, e.target.value)} /></div>
  );

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()} style={{ width: 640 }}>
        <h2>Add a vessel</h2>
        <p style={{ fontSize: 13, color: "var(--ink-2)", marginTop: 2 }}>The last-docking date and survey number drive the 36-month docking-window clock.</p>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, marginTop: 10 }}>
          {F("Name", "name")}
          <div className="field"><label>Type</label>
            <select value={f.vessel_type} onChange={(e) => set("vessel_type", e.target.value)}>
              {TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
            </select></div>
          {F("DWT", "dwt", "number")}
          {F("Class society", "class_society")}
          {F("LOA (m)", "loa_m", "number")}
          {F("Beam (m)", "beam_m", "number")}
          {F("Summer draft (m)", "summer_draft_m", "number")}
          {F("Special survey no.", "special_survey_no", "number")}
          {F("Last docking date", "last_docking_date", "date")}
          {F("TCE ($/day)", "tce_usd_day", "number")}
        </div>
        <label style={{ display: "flex", gap: 8, alignItems: "center", fontSize: 13, marginTop: 12 }}>
          <input type="checkbox" checked={f.uwild_ok} onChange={(e) => set("uwild_ok", e.target.checked)} /> UWILD-eligible (in-water survey in lieu of docking)
        </label>
        <div style={{ display: "flex", gap: 10, marginTop: 18, justifyContent: "flex-end" }}>
          <button className="btn btn-quiet" onClick={onClose}>Cancel</button>
          <button className="btn btn-signal" disabled={busy || !f.name.trim()} onClick={submit}>{busy ? "Saving…" : "Add vessel"}</button>
        </div>
      </div>
    </div>
  );
}
