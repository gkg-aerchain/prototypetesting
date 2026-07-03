"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api, SpecSummary, Vessel } from "@/lib/api";
import { fmtDate } from "@/lib/format";

export default function SpecificationsPage() {
  const router = useRouter();
  const [specs, setSpecs] = useState<SpecSummary[] | null>(null);
  const [creating, setCreating] = useState(false);

  const load = () => api.get<SpecSummary[]>("/api/specs").then(setSpecs).catch(() => setSpecs([]));
  useEffect(() => { load(); }, []);

  return (
    <>
      <div className="stage-head">
        <div><h1>Specifications</h1><div className="sub">Docking work packages by vessel</div></div>
        <button className="btn btn-primary" onClick={() => setCreating(true)}>New specification</button>
      </div>

      {!specs ? (
        <div className="skel" style={{ height: 240 }} />
      ) : specs.length === 0 ? (
        <div className="empty"><h3>No specifications yet</h3><p>Start one from a vessel to build its docking scope.</p></div>
      ) : (
        <div className="panel">
          <div className="scrollx">
            <table className="grid">
              <thead><tr><th>Specification</th><th>Vessel</th><th className="num">Lines</th><th>Coverage</th><th>Status</th></tr></thead>
              <tbody>
                {specs.map((s) => (
                  <tr className="rowlink" key={s.id} onClick={() => router.push(`/specifications/${s.id}`)}>
                    <td><b>{s.title}</b></td>
                    <td className="vessel-name"><b>{s.vessel}</b><span>{s.vessel_type}</span></td>
                    <td className="num">{s.items}</td>
                    <td style={{ minWidth: 120 }}>
                      <div className="progress-bar"><i style={{ width: `${s.pct_complete}%` }} /></div>
                      <span style={{ fontSize: 11, color: "var(--ink-3)" }}>{s.sections_covered}/{s.sections_total} sections</span>
                    </td>
                    <td><span className={`pill ${s.status === "frozen" ? "good" : "neutral"}`}>{s.status}</span></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {creating && <NewSpecModal onClose={(id) => { setCreating(false); if (id) router.push(`/specifications/${id}`); else load(); }} />}
    </>
  );
}

function NewSpecModal({ onClose }: { onClose: (id?: string) => void }) {
  const [fleet, setFleet] = useState<Vessel[]>([]);
  const [vesselId, setVesselId] = useState("");
  const [title, setTitle] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api.get<Vessel[]>("/api/fleet").then((f) => { setFleet(f); if (f[0]) setVesselId(f[0].id); });
  }, []);

  async function create() {
    setBusy(true);
    try {
      const s = await api.post<{ id: string }>("/api/specs", { vessel_id: vesselId, title });
      onClose(s.id);
    } catch (e) { alert((e as Error).message); setBusy(false); }
  }

  return (
    <div className="modal-backdrop" onClick={() => onClose()}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <h2 style={{ margin: "0 0 14px", fontSize: 18 }}>New specification</h2>
        <div className="field" style={{ marginBottom: 12 }}>
          <label>Vessel</label>
          <select value={vesselId} onChange={(e) => setVesselId(e.target.value)}>
            {fleet.map((v) => <option key={v.id} value={v.id}>{v.name} — {v.vessel_type}</option>)}
          </select>
        </div>
        <div className="field">
          <label>Title</label>
          <input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="e.g. Kalymnos Voyager — SS No. 2 docking specification" />
        </div>
        <div style={{ display: "flex", gap: 10, marginTop: 18, justifyContent: "flex-end" }}>
          <button className="btn btn-quiet" onClick={() => onClose()}>Cancel</button>
          <button className="btn btn-signal" disabled={busy || !vesselId || !title} onClick={create}>Create</button>
        </div>
      </div>
    </div>
  );
}
