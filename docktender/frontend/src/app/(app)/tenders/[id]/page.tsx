"use client";
import { useCallback, useEffect, useState } from "react";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { API_BASE, api, getToken, TenderDetail, BidSummary, BidReview, YardDto } from "@/lib/api";
import { fmtDate, fmtM } from "@/lib/format";

interface AwardPreview {
  tender_ref: string; vessel: string; recommended_bid_id: string; recommended_yard: string;
  recommended_tec_usd: number; ranking: { rank: number; yard: string; tec_usd: number; recommended: boolean }[];
  rationale: string; checklist: Record<string, boolean>; already_awarded: boolean;
}

export default function TenderRoomPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const search = useSearchParams();
  const [t, setT] = useState<TenderDetail | null>(null);
  const [tab, setTab] = useState<"overview" | "bids">("overview");
  const [award, setAward] = useState<AwardPreview | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(() => {
    api.get<TenderDetail>(`/api/tenders/${id}`).then(setT).catch(() => setT(null));
  }, [id]);
  useEffect(load, [load]);

  const openAward = useCallback(() => {
    api.get<AwardPreview>(`/api/tenders/${id}/award/preview`).then(setAward).catch((e) => alert(e.message));
  }, [id]);

  useEffect(() => { if (search.get("award") === "1") openAward(); }, [search, openAward]);

  async function issue() {
    setBusy(true);
    try { await api.post(`/api/tenders/${id}/issue`); load(); }
    catch (e) { alert((e as Error).message); }
    setBusy(false);
  }

  if (!t) return <div className="skel" style={{ height: 300 }} />;
  const pillKind = t.status === "awarded" ? "good" : t.status === "issued" ? "signal" : "neutral";

  return (
    <>
      <div className="stage-head">
        <div>
          <span className="eyebrow">{t.ref} <span style={{ color: "var(--ink-3)" }}>·</span> <span className={`pill ${pillKind}`} style={{ verticalAlign: "middle" }}>{t.status}</span></span>
          <h1 style={{ marginTop: 8 }}>{t.vessel} — docking tender</h1>
          <div className="sub">{t.spec_title} · deadline {fmtDate(t.deadline)} · {t.invited} invited · {t.bids} bids</div>
        </div>
        <div style={{ display: "flex", gap: 10 }}>
          {t.status === "draft" && (
            <button className="btn btn-signal" disabled={busy || t.invited === 0} onClick={issue}>
              {t.invited === 0 ? "Invite a yard to issue" : "Issue tender"}
            </button>
          )}
          {t.bids > 0 && (
            <button className="btn btn-quiet" onClick={() => router.push(`/tenders/${id}/leveling`)}>Open leveling</button>
          )}
          {t.status !== "awarded" && t.bids > 0 && (
            <button className="btn btn-signal" onClick={openAward}>Draft award memo</button>
          )}
        </div>
      </div>

      <div className="tabs">
        <button className={tab === "overview" ? "active" : ""} onClick={() => setTab("overview")}>Overview</button>
        <button className={tab === "bids" ? "active" : ""} onClick={() => setTab("bids")}>Bids ({t.bids})</button>
      </div>

      {tab === "overview"
        ? <Overview t={t} onChange={load} />
        : <Bids tenderId={id} t={t} onChange={load} />}

      {award && <AwardModal id={id} preview={award} onClose={() => { setAward(null); load(); }} />}
    </>
  );
}

/* ---------------------------------------------------------------- Overview */
function Overview({ t, onChange }: { t: TenderDetail; onChange: () => void }) {
  const [invite, setInvite] = useState(false);
  const [q, setQ] = useState("");
  const editable = t.status !== "awarded";

  async function raise() {
    if (!q.trim()) return;
    await api.post(`/api/tenders/${t.id}/clarifications`, { question: q });
    setQ(""); onChange();
  }

  return (
    <div className="ov-cols">
      <div className="panel">
        <div className="panel-head">
          <h2>Invited yards</h2>
          {editable && <button className="btn btn-quiet" style={{ padding: "5px 12px", fontSize: 12 }} onClick={() => setInvite(true)}>Invite yards</button>}
        </div>
        {t.invitations.length === 0 ? (
          <div style={{ padding: 16, fontSize: 13, color: "var(--ink-3)" }}>No yards invited yet — invite from the directory to issue this tender.</div>
        ) : (
          <div className="scrollx">
            <table className="grid">
              <thead><tr><th>Yard</th><th>Region</th><th>Status</th></tr></thead>
              <tbody>
                {t.invitations.map((inv) => (
                  <tr key={inv.yard_id}>
                    <td><b>{inv.yard}</b></td>
                    <td className="mono" style={{ fontSize: 11.5 }}>{inv.region}</td>
                    <td><span className={`pill ${inv.has_bid ? "good" : "neutral"}`}>{inv.has_bid ? "Bid received" : inv.status}</span></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <div className="panel">
        <div className="panel-head"><h2>Clarifications &amp; addenda</h2></div>
        {editable && (
          <div style={{ padding: "12px 16px", borderBottom: "1px solid var(--hairline)", display: "flex", gap: 8 }}>
            <input className="field" style={{ flex: 1 }} value={q} onChange={(e) => setQ(e.target.value)}
              placeholder="Raise a clarification…" onKeyDown={(e) => e.key === "Enter" && raise()} />
            <button className="btn btn-quiet" disabled={!q.trim()} onClick={raise}>Add</button>
          </div>
        )}
        {t.clarifications.length === 0 && <div style={{ padding: 16, fontSize: 13, color: "var(--ink-3)" }}>No clarifications raised.</div>}
        {t.clarifications.map((c) => <Clarification key={c.id} c={c} editable={editable} onChange={onChange} />)}
      </div>

      {invite && <InviteModal tenderId={t.id} vesselId={t.vessel_id} invited={t.invitations.map((i) => i.yard_id)} onClose={() => { setInvite(false); onChange(); }} />}
    </div>
  );
}

function Clarification({ c, editable, onChange }: { c: TenderDetail["clarifications"][0]; editable: boolean; onChange: () => void }) {
  const [ans, setAns] = useState(c.answer);
  const [editing, setEditing] = useState(false);
  async function publish() {
    await api.patch(`/api/clarifications/${c.id}`, { answer: ans, publish: true });
    setEditing(false); onChange();
  }
  return (
    <div style={{ padding: "12px 16px", borderBottom: "1px solid var(--hairline)" }}>
      <div style={{ fontSize: 13, fontWeight: 600 }}>{c.question}</div>
      {c.answer && !editing && <div style={{ fontSize: 12.5, color: "var(--ink-2)", marginTop: 4 }}>{c.answer}</div>}
      {editing && (
        <div style={{ display: "flex", gap: 8, marginTop: 8 }}>
          <input className="field" style={{ flex: 1 }} value={ans} onChange={(e) => setAns(e.target.value)} placeholder="Answer + publish as addendum…" />
          <button className="btn btn-signal" style={{ padding: "6px 12px", fontSize: 12 }} disabled={!ans.trim()} onClick={publish}>Publish</button>
        </div>
      )}
      <div style={{ marginTop: 6, display: "flex", gap: 8, alignItems: "center" }}>
        {c.published && <span className="pill signal">Addendum {c.addendum_no}</span>}
        {editable && !c.published && !editing && <button className="btn btn-quiet" style={{ padding: "3px 10px", fontSize: 11.5 }} onClick={() => setEditing(true)}>Answer</button>}
      </div>
    </div>
  );
}

/* ---------------------------------------------------------------- Bids */
function Bids({ tenderId, t, onChange }: { tenderId: string; t: TenderDetail; onChange: () => void }) {
  const [bids, setBids] = useState<BidSummary[] | null>(null);
  const [ingest, setIngest] = useState(false);
  const [portal, setPortal] = useState(false);
  const [reviewId, setReviewId] = useState<string | null>(null);

  const reload = useCallback(() => {
    api.get<BidSummary[]>(`/api/tenders/${tenderId}/bids`).then(setBids).catch(() => setBids([]));
  }, [tenderId]);
  useEffect(reload, [reload]);

  return (
    <>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 14, gap: 10, flexWrap: "wrap" }}>
        <div className="sub">{bids?.length ?? 0} bids received</div>
        <div style={{ display: "flex", gap: 8 }}>
          <button className="btn btn-quiet" onClick={() => setPortal(true)}>Enter portal bid</button>
          <button className="btn btn-quiet" onClick={() => setIngest(true)}>Ingest quotation (AI)</button>
        </div>
      </div>
      {!bids ? <div className="skel" style={{ height: 120 }} /> : bids.length === 0 ? (
        <div className="empty"><h3>No bids yet</h3><p>Enter a portal bid, or ingest a PDF/text quote for AI-assisted review.</p></div>
      ) : (
        <div className="panel">
          <div className="scrollx">
            <table className="grid">
              <thead><tr><th>Yard</th><th>Source</th><th className="num">Lines</th><th>Review</th><th></th></tr></thead>
              <tbody>
                {bids.map((b) => (
                  <tr key={b.bid_id}>
                    <td><b>{b.yard}</b> <span className="mono" style={{ fontSize: 11, color: "var(--ink-3)" }}>{b.region}</span></td>
                    <td><span className="pill neutral">{b.source === "ai_ingest" ? "AI ingest" : "Portal"}</span></td>
                    <td className="num">{b.lines}</td>
                    <td>{b.unreviewed > 0 ? <span className="pill warn">{b.unreviewed} to review</span> : <span className="pill good">Reviewed</span>}</td>
                    <td style={{ textAlign: "right" }}>
                      <button className="btn btn-quiet" style={{ padding: "4px 12px", fontSize: 12 }} onClick={() => setReviewId(b.bid_id)}>
                        {b.unreviewed > 0 ? "Review" : "View"}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
      {ingest && <IngestModal tenderId={tenderId} yards={t.invitations} onClose={() => { setIngest(false); reload(); onChange(); }} />}
      {portal && <PortalBidModal tenderId={tenderId} yards={t.invitations} onClose={() => { setPortal(false); reload(); onChange(); }} />}
      {reviewId && <ReviewDrawer bidId={reviewId} onClose={() => { setReviewId(null); reload(); onChange(); }} />}
    </>
  );
}

/* ---------------------------------------------------------------- Invite modal */
function InviteModal({ tenderId, vesselId, invited, onClose }: { tenderId: string; vesselId: string | null; invited: string[]; onClose: () => void }) {
  const [yards, setYards] = useState<YardDto[] | null>(null);
  const [region, setRegion] = useState("");
  const [sel, setSel] = useState<Set<string>>(new Set());
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    const p = new URLSearchParams();
    if (vesselId) p.set("vessel_id", vesselId);
    api.get<YardDto[]>(`/api/yards?${p}`).then(setYards);
  }, [vesselId]);

  const regions = Array.from(new Set((yards || []).map((y) => y.region))).sort();
  const shown = (yards || []).filter((y) => !region || y.region === region);

  function toggle(id: string) {
    const n = new Set(sel); n.has(id) ? n.delete(id) : n.add(id); setSel(n);
  }
  async function submit() {
    setBusy(true);
    try { await api.post(`/api/tenders/${tenderId}/invite`, { yard_ids: [...sel] }); onClose(); }
    catch (e) { alert((e as Error).message); setBusy(false); }
  }

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()} style={{ width: 640 }}>
        <h2>Invite yards</h2>
        <p style={{ fontSize: 13, color: "var(--ink-2)", marginTop: 2 }}>
          {vesselId ? "Fit-checked against the vessel’s docking dimensions." : "Select yards to invite."}
        </p>
        <div style={{ display: "flex", gap: 8, margin: "10px 0 12px", flexWrap: "wrap" }}>
          <button className={`btn btn-quiet ${!region ? "active" : ""}`} style={{ padding: "4px 12px", fontSize: 12, borderColor: !region ? "var(--signal)" : undefined }} onClick={() => setRegion("")}>All</button>
          {regions.map((r) => (
            <button key={r} className="btn btn-quiet" style={{ padding: "4px 12px", fontSize: 12, borderColor: region === r ? "var(--signal)" : undefined }} onClick={() => setRegion(r)}>{r}</button>
          ))}
        </div>
        <div style={{ maxHeight: 380, overflowY: "auto", border: "1px solid var(--hairline)", borderRadius: "var(--r-sm)" }}>
          {!yards ? <div className="skel" style={{ height: 120 }} /> : shown.map((y) => {
            const already = invited.includes(y.id);
            return (
              <label key={y.id} className="invite-row" style={{ opacity: already ? .5 : 1 }}>
                <input type="checkbox" disabled={already} checked={sel.has(y.id)} onChange={() => toggle(y.id)} />
                <div style={{ flex: 1 }}>
                  <b>{y.name}</b> <span className="mono" style={{ fontSize: 11, color: "var(--ink-3)" }}>{y.region}</span>
                  <div style={{ fontSize: 11.5, color: "var(--ink-3)" }}>{y.docks.length} dock{y.docks.length === 1 ? "" : "s"}{y.country ? ` · ${y.country}` : ""}</div>
                </div>
                {already ? <span className="pill neutral">Invited</span>
                  : y.fits ? <span className="pill good">Fits</span>
                  : y.fits === false ? <span className="pill crit">No fit</span> : null}
              </label>
            );
          })}
        </div>
        <div style={{ display: "flex", gap: 10, marginTop: 18, justifyContent: "flex-end" }}>
          <button className="btn btn-quiet" onClick={onClose}>Cancel</button>
          <button className="btn btn-signal" disabled={busy || sel.size === 0} onClick={submit}>Invite {sel.size || ""}</button>
        </div>
      </div>
    </div>
  );
}

/* ---------------------------------------------------------------- Portal bid modal */
interface PLine { raw_text: string; amount: string; state: string; }
function PortalBidModal({ tenderId, yards, onClose }: { tenderId: string; yards: TenderDetail["invitations"]; onClose: () => void }) {
  const [yardId, setYardId] = useState(yards[0]?.yard_id || "");
  const [dockDays, setDockDays] = useState("13");
  const [devNm, setDevNm] = useState("0");
  const [tariff, setTariff] = useState(true);
  const [lines, setLines] = useState<PLine[]>([{ raw_text: "Yard total (all sections)", amount: "", state: "priced" }]);
  const [busy, setBusy] = useState(false);

  function setLine(i: number, p: Partial<PLine>) { setLines(lines.map((l, j) => j === i ? { ...l, ...p } : l)); }

  async function submit() {
    setBusy(true);
    try {
      await api.post(`/api/tenders/${tenderId}/bids`, {
        yard_id: yardId, currency: "USD", dock_days: Number(dockDays) || 0,
        tariff_captured: tariff, deviation_nm: Number(devNm) || 0,
        lines: lines.filter((l) => l.amount || l.state !== "priced").map((l) => ({
          raw_text: l.raw_text, amount: l.amount ? Number(l.amount) : null, state: l.state, uom: "lot",
        })),
      });
      onClose();
    } catch (e) { alert((e as Error).message); setBusy(false); }
  }

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()} style={{ width: 620 }}>
        <h2>Enter a portal bid</h2>
        <p style={{ fontSize: 13, color: "var(--ink-2)", marginTop: 2 }}>A structured bid, trusted as entered — it counts toward leveling immediately.</p>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, marginTop: 8 }}>
          <div className="field"><label>Yard</label>
            <select value={yardId} onChange={(e) => setYardId(e.target.value)}>
              {yards.map((y) => <option key={y.yard_id} value={y.yard_id}>{y.yard}</option>)}
            </select>
          </div>
          <div className="field"><label>Dock days</label><input type="number" value={dockDays} onChange={(e) => setDockDays(e.target.value)} /></div>
          <div className="field"><label>Deviation (nm)</label><input type="number" value={devNm} onChange={(e) => setDevNm(e.target.value)} /></div>
          <div className="field" style={{ display: "flex", alignItems: "flex-end" }}>
            <label style={{ display: "flex", gap: 8, alignItems: "center", fontWeight: 500 }}>
              <input type="checkbox" checked={tariff} onChange={(e) => setTariff(e.target.checked)} /> Standard tariff annexed
            </label>
          </div>
        </div>
        <div className="eyebrow" style={{ margin: "16px 0 8px" }}>Bid lines</div>
        {lines.map((l, i) => (
          <div key={i} style={{ display: "flex", gap: 8, marginBottom: 8 }}>
            <input className="field" style={{ flex: 2 }} value={l.raw_text} onChange={(e) => setLine(i, { raw_text: e.target.value })} placeholder="Description" />
            <input className="field" style={{ flex: 1 }} type="number" value={l.amount} onChange={(e) => setLine(i, { amount: e.target.value })} placeholder="USD" />
            <select className="field" style={{ width: 120 }} value={l.state} onChange={(e) => setLine(i, { state: e.target.value })}>
              <option value="priced">priced</option><option value="excluded">excluded</option><option value="unpriced">unpriced</option>
            </select>
          </div>
        ))}
        <button className="btn btn-quiet" style={{ padding: "4px 12px", fontSize: 12 }} onClick={() => setLines([...lines, { raw_text: "", amount: "", state: "priced" }])}>+ Add line</button>
        <div style={{ display: "flex", gap: 10, marginTop: 18, justifyContent: "flex-end" }}>
          <button className="btn btn-quiet" onClick={onClose}>Cancel</button>
          <button className="btn btn-signal" disabled={busy || !yardId} onClick={submit}>{busy ? "Saving…" : "Submit bid"}</button>
        </div>
      </div>
    </div>
  );
}

/* ---------------------------------------------------------------- Review drawer */
function ReviewDrawer({ bidId, onClose }: { bidId: string; onClose: () => void }) {
  const [r, setR] = useState<BidReview | null>(null);
  const [findings, setFindings] = useState<{ severity: string; message: string; evidence: string }[] | null>(null);

  const load = useCallback(() => { api.get<BidReview>(`/api/bids/${bidId}/review`).then(setR); }, [bidId]);
  useEffect(load, [load]);

  async function patch(lineId: string, body: Record<string, unknown>) {
    await api.patch(`/api/bids/${bidId}/lines/${lineId}`, body); load();
  }
  async function acceptAllHigh() {
    if (!r) return;
    const high = r.lines.filter((l) => !l.reviewed && (l.ai_confidence ?? 1) >= 0.9);
    for (const l of high) await api.patch(`/api/bids/${bidId}/lines/${l.id}`, { accept: true });
    load();
  }
  async function sanity() {
    const res = await api.post<{ findings: typeof findings }>(`/api/bids/${bidId}/sanity-check`);
    setFindings(res.findings);
  }

  if (!r) return (
    <div className="drawer-backdrop" onClick={onClose}><div className="drawer" onClick={(e) => e.stopPropagation()}><div className="skel" style={{ height: 300 }} /></div></div>
  );
  const isAI = r.source === "ai_ingest";
  const pending = r.lines.filter((l) => l.ai_confidence !== null && !l.reviewed).length;

  return (
    <div className="drawer-backdrop" onClick={onClose}>
      <div className="drawer" onClick={(e) => e.stopPropagation()}>
        <span className="eyebrow">{isAI ? "AI-ingested bid" : "Portal bid"} · review</span>
        <h2 style={{ marginTop: 6 }}>{r.yard}</h2>
        <div className="sub" style={{ marginBottom: 14 }}>{r.currency} · {r.dock_days} dock days · {r.lines.length} lines{pending ? ` · ${pending} awaiting review` : ""}</div>

        {isAI && (
          <div style={{ display: "flex", gap: 8, marginBottom: 14, flexWrap: "wrap" }}>
            <button className="btn btn-signal" style={{ padding: "6px 14px", fontSize: 12.5 }} onClick={acceptAllHigh}>Accept all ≥90% confidence</button>
            <button className="btn btn-quiet" style={{ padding: "6px 14px", fontSize: 12.5 }} onClick={sanity}>Run sanity check</button>
          </div>
        )}
        {findings && (
          <div className="panel" style={{ marginBottom: 14, padding: "10px 14px" }}>
            <div className="eyebrow" style={{ marginBottom: 6 }}>Sanity checker</div>
            {findings.length === 0 ? <div style={{ fontSize: 12.5, color: "var(--ink-3)" }}>No norm deviations found.</div>
              : findings.map((f, i) => <div key={i} style={{ fontSize: 12.5, marginBottom: 4 }}><span className={`pill ${f.severity === "crit" ? "crit" : "warn"}`}>{f.severity}</span> {f.message} <span className="mono" style={{ color: "var(--ink-3)" }}>{f.evidence}</span></div>)}
          </div>
        )}

        <div className="panel">
          <div className="scrollx">
            <table className="grid">
              <thead><tr><th>Line</th><th className="num">Amount</th><th>Maps to</th>{isAI && <th>Conf.</th>}<th></th></tr></thead>
              <tbody>
                {r.lines.map((l) => (
                  <tr key={l.id}>
                    <td>
                      <b style={{ fontSize: 12.5 }}>{l.raw_text}</b>
                      <div><span className={`xchip ${l.state === "excluded" ? "" : l.state === "unpriced" ? "warn" : "ok"}`}>{l.state}</span></div>
                    </td>
                    <td className="num">{l.amount != null ? l.amount.toLocaleString() : "—"}</td>
                    <td>
                      <select className="field" style={{ minWidth: 150, fontSize: 12 }} value={l.spec_item_id || l.proposed_spec_item_id || ""}
                        onChange={(e) => patch(l.id, { spec_item_id: e.target.value })}>
                        <option value="">— unmapped —</option>
                        {r.spec_items.map((si) => <option key={si.id} value={si.id}>§{si.line_no} {si.title}</option>)}
                      </select>
                    </td>
                    {isAI && <td>{l.ai_confidence != null && <ConfHeat c={l.ai_confidence} />}</td>}
                    <td style={{ textAlign: "right" }}>
                      {l.reviewed ? <span className="pill good">Accepted</span>
                        : <button className="btn btn-quiet" style={{ padding: "3px 10px", fontSize: 11.5 }} onClick={() => patch(l.id, { accept: true })}>Accept</button>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
        <div style={{ display: "flex", justifyContent: "flex-end", marginTop: 16 }}>
          <button className="btn btn-signal" onClick={onClose}>Done</button>
        </div>
      </div>
    </div>
  );
}

function ConfHeat({ c }: { c: number }) {
  const color = c >= 0.9 ? "var(--good)" : c >= 0.7 ? "var(--warn)" : "var(--crit)";
  return (
    <span className="heat" title={`${Math.round(c * 100)}% confidence`}>
      <i style={{ width: `${Math.round(c * 100)}%`, background: color }} />
    </span>
  );
}

/* ---------------------------------------------------------------- Ingest + Award (kept) */
function IngestModal({ tenderId, yards, onClose }: { tenderId: string; yards: TenderDetail["invitations"]; onClose: () => void }) {
  const [yardId, setYardId] = useState(yards[0]?.yard_id || "");
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);

  async function submit() {
    setBusy(true); setMsg(null);
    try {
      const r = await api.post<{ bid_id: string; lines: number; low_confidence: number }>(
        `/api/tenders/${tenderId}/bids/ingest`, { yard_id: yardId, text });
      setMsg(`Parsed ${r.lines} lines (${r.low_confidence} low-confidence). Open the bid to review before it counts.`);
      setBusy(false);
    } catch (e) { setMsg((e as Error).message); setBusy(false); }
  }

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <h2>Ingest a yard quotation</h2>
        <p style={{ fontSize: 13, color: "var(--ink-2)", marginTop: 2 }}>
          Paste a quote; the Bid Parser maps it to the spec grid. Every line lands as a draft you review —
          nothing counts toward leveling until you accept it.
        </p>
        <div className="field" style={{ marginBottom: 12 }}>
          <label>Yard</label>
          <select value={yardId} onChange={(e) => setYardId(e.target.value)}>
            {yards.map((y) => <option key={y.yard_id} value={y.yard_id}>{y.yard}</option>)}
          </select>
        </div>
        <div className="field">
          <label>Quotation text</label>
          <textarea rows={8} value={text} onChange={(e) => setText(e.target.value)} placeholder="Paste the yard's quotation here…" />
        </div>
        {msg && <div style={{ fontSize: 13, color: "var(--ink-2)", marginTop: 12 }}>{msg}</div>}
        <div style={{ display: "flex", gap: 10, marginTop: 18, justifyContent: "flex-end" }}>
          <button className="btn btn-quiet" onClick={onClose}>Close</button>
          <button className="btn btn-signal" disabled={busy || !text || !yardId} onClick={submit}>{busy ? "Parsing…" : "Parse quotation"}</button>
        </div>
      </div>
    </div>
  );
}

function AwardModal({ id, preview, onClose }: { id: string; preview: AwardPreview; onClose: () => void }) {
  const [checklist, setChecklist] = useState(preview.checklist);
  const [busy, setBusy] = useState(false);
  const [awardId, setAwardId] = useState<string | null>(null);

  async function confirm() {
    setBusy(true);
    try {
      const r = await api.post<{ award_id: string }>(`/api/tenders/${id}/award`, {
        bid_id: preview.recommended_bid_id, memo_note: "", checklist,
      });
      setAwardId(r.award_id);
    } catch (e) { alert((e as Error).message); setBusy(false); }
  }
  function downloadMemo(aid: string) {
    fetch(`${API_BASE}/api/awards/${aid}/memo.pdf`, { headers: { Authorization: `Bearer ${getToken()}` } })
      .then((r) => r.blob()).then((b) => window.open(URL.createObjectURL(b), "_blank"));
  }

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <span className="eyebrow">{preview.tender_ref} · award recommendation</span>
        <h2 style={{ margin: "6px 0 4px" }}>Award to {preview.recommended_yard}</h2>
        <div className="mono" style={{ fontSize: 24, fontWeight: 500 }}>{fmtM(preview.recommended_tec_usd)} <small style={{ fontSize: 13, color: "var(--ink-3)" }}>M TEC</small></div>
        <p style={{ fontSize: 13, color: "var(--ink-2)", lineHeight: 1.55 }}>{preview.rationale}</p>
        <div className="panel" style={{ marginBottom: 16 }}>
          <div className="scrollx">
            <table className="grid">
              <thead><tr><th>Rank</th><th>Yard</th><th className="num">TEC</th></tr></thead>
              <tbody>
                {preview.ranking.map((r) => (
                  <tr key={r.rank}>
                    <td>{r.rank}</td>
                    <td><b>{r.yard}</b>{r.recommended && <span className="pill signal" style={{ marginLeft: 8 }}>Recommended</span>}</td>
                    <td className="num">{fmtM(r.tec_usd)} M</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
        <div style={{ marginBottom: 16 }}>
          <div className="eyebrow" style={{ marginBottom: 8 }}>Contract checklist</div>
          {Object.entries(checklist).map(([k, v]) => (
            <label key={k} style={{ display: "flex", gap: 8, alignItems: "center", fontSize: 13, padding: "4px 0", cursor: "pointer" }}>
              <input type="checkbox" checked={v} onChange={(e) => setChecklist({ ...checklist, [k]: e.target.checked })} />
              {k.replace(/_/g, " ")}
            </label>
          ))}
        </div>
        {awardId ? (
          <div style={{ display: "flex", gap: 10, justifyContent: "flex-end" }}>
            <button className="btn btn-quiet" onClick={onClose}>Done</button>
            <button className="btn btn-signal" onClick={() => downloadMemo(awardId)}>Download memo PDF</button>
          </div>
        ) : preview.already_awarded ? (
          <div style={{ fontSize: 13, color: "var(--good)" }}>This tender is already awarded.</div>
        ) : (
          <div style={{ display: "flex", gap: 10, justifyContent: "flex-end" }}>
            <button className="btn btn-quiet" onClick={onClose}>Cancel</button>
            <button className="btn btn-signal" disabled={busy} onClick={confirm}>{busy ? "Awarding…" : "Confirm award"}</button>
          </div>
        )}
      </div>
    </div>
  );
}
