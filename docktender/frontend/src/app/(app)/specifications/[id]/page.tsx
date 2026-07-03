"use client";
import { useCallback, useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { api, SpecDetail, WorkItem } from "@/lib/api";

const SECTIONS = [
  { n: 1, name: "General Services" }, { n: 2, name: "Hull Treatment" },
  { n: 3, name: "Steel Renewals" }, { n: 4, name: "Sea Valves" },
  { n: 5, name: "Propulsion" }, { n: 6, name: "Boiler" },
  { n: 7, name: "Piping & Tanks" }, { n: 8, name: "Machinery" },
  { n: 9, name: "Electrical" }, { n: 10, name: "Class & Surveys" },
];

export default function SpecBuilderPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [spec, setSpec] = useState<SpecDetail | null>(null);
  const [section, setSection] = useState(1);
  const [lib, setLib] = useState<WorkItem[]>([]);
  const [q, setQ] = useState("");

  const load = useCallback(() => {
    api.get<SpecDetail>(`/api/specs/${id}`).then(setSpec).catch(() => setSpec(null));
  }, [id]);
  useEffect(load, [load]);

  useEffect(() => {
    const params = new URLSearchParams();
    params.set("section", String(section));
    if (q) params.set("q", q);
    api.get<WorkItem[]>(`/api/work-items?${params}`).then(setLib);
  }, [section, q]);

  const addItem = useCallback(async (wi: WorkItem) => {
    await api.post(`/api/specs/${id}/items`, [{ work_item_id: wi.id, title: wi.title, qty: 1, uom: wi.uom }]);
    load();
  }, [id, load]);

  const removeItem = useCallback(async (itemId: string) => {
    await api.del(`/api/specs/${id}/items/${itemId}`);
    load();
  }, [id, load]);

  async function freeze() {
    try { await api.post(`/api/specs/${id}/freeze`); load(); }
    catch (e) { alert((e as Error).message); }
  }
  async function copyForward() {
    try { await api.post(`/api/specs/${id}/copy-forward`); load(); }
    catch (e) { alert((e as Error).message); }
  }

  if (!spec) return <div className="skel" style={{ height: 300 }} />;
  const frozen = spec.status === "frozen";
  const sectionCounts: Record<number, number> = {};
  spec.item_list.forEach((it) => { if (it.section) sectionCounts[it.section] = (sectionCounts[it.section] || 0) + 1; });

  return (
    <>
      <div className="stage-head">
        <div>
          <span className="eyebrow">{spec.vessel} · v{spec.version}</span>
          <h1 style={{ marginTop: 6 }}>{spec.title}</h1>
          <div className="sub">{spec.items} lines · {spec.sections_covered}/10 sections · {spec.pct_complete}% coverage</div>
        </div>
        <div style={{ display: "flex", gap: 10 }}>
          {!frozen && <button className="btn btn-quiet" onClick={copyForward}>Copy forward</button>}
          {frozen ? (
            <button className="btn btn-signal" onClick={() => createTender(id, router)}>Create tender</button>
          ) : (
            <button className="btn btn-primary" onClick={freeze}>Freeze specification</button>
          )}
        </div>
      </div>

      <div className="builder">
        <div className="sec-tree">
          {SECTIONS.map((s) => (
            <button key={s.n} className={section === s.n ? "active" : ""} onClick={() => setSection(s.n)}>
              <span>§{s.n} {s.name}</span>
              <span className="c">{sectionCounts[s.n] || 0}</span>
            </button>
          ))}
        </div>

        <div className="panel">
          <div className="panel-head"><h2>Specification lines</h2><span className="eyebrow dim">{frozen ? "frozen" : "editable"}</span></div>
          <div className="scrollx">
            <table className="grid">
              <thead><tr><th>#</th><th>Item</th><th className="num">Qty</th><th>UoM</th><th>Origin</th>{!frozen && <th></th>}</tr></thead>
              <tbody>
                {spec.item_list.length === 0 && (
                  <tr><td colSpan={frozen ? 5 : 6} style={{ color: "var(--ink-3)", fontSize: 13 }}>No lines yet — add from the library →</td></tr>
                )}
                {spec.item_list.map((it) => (
                  <tr key={it.id}>
                    <td className="mono" style={{ color: "var(--ink-3)", fontSize: 11.5 }}>{it.line_no}</td>
                    <td>
                      <b style={{ fontWeight: 600, fontSize: 13 }}>{it.title}</b>
                      {it.code && <span className="mono" style={{ fontSize: 11, color: "var(--ink-3)", marginLeft: 6 }}>{it.code}</span>}
                      {it.qty_tbc && <span className="xchip warn" style={{ marginLeft: 6 }}>qty TBC</span>}
                    </td>
                    <td className="num">{it.qty}</td>
                    <td>{it.uom}</td>
                    <td><span className="pill neutral">{it.origin}</span></td>
                    {!frozen && <td style={{ textAlign: "right" }}><button className="btn btn-quiet" style={{ padding: "3px 10px", fontSize: 12 }} onClick={() => removeItem(it.id)}>Remove</button></td>}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {!frozen ? (
          <div className="lib-drawer">
            <div className="panel-head"><h2>Library §{section}</h2></div>
            <div style={{ padding: 12 }}>
              <input className="mono" style={{ width: "100%", font: "400 13px var(--sans)", color: "var(--ink)", background: "var(--card)", border: "1px solid var(--hairline-2)", borderRadius: 6, padding: "8px 10px" }}
                placeholder="Search…" value={q} onChange={(e) => setQ(e.target.value)} />
            </div>
            <div style={{ maxHeight: 520, overflowY: "auto" }}>
              {lib.map((wi) => (
                <div key={wi.id} className="lib-item" onClick={() => addItem(wi)}>
                  <b>{wi.title}</b>
                  <div className="meta">{wi.code} · norm {wi.norm_value} {wi.norm_unit}</div>
                </div>
              ))}
            </div>
          </div>
        ) : (
          <div className="panel" style={{ padding: 20 }}>
            <div className="eyebrow" style={{ marginBottom: 8 }}>Frozen</div>
            <p style={{ fontSize: 13, color: "var(--ink-2)", margin: 0 }}>
              This specification is locked at version {spec.version}. Create a tender to invite yards.
            </p>
          </div>
        )}
      </div>
    </>
  );
}

async function createTender(specId: string, router: ReturnType<typeof useRouter>) {
  try {
    const deadline = new Date(Date.now() + 30 * 864e5).toISOString();
    const t = await api.post<{ id: string }>("/api/tenders", {
      spec_id: specId, deadline, offhire_usd_day: 22000,
    });
    router.push(`/tenders/${t.id}`);
  } catch (e) { alert((e as Error).message); }
}
