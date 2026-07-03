"use client";
import { useCallback, useEffect, useState } from "react";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { API_BASE, api, getToken, TenderDetail } from "@/lib/api";
import { fmtDate, fmtM, fmtUsd } from "@/lib/format";

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

  const load = useCallback(() => {
    api.get<TenderDetail>(`/api/tenders/${id}`).then(setT).catch(() => setT(null));
  }, [id]);
  useEffect(load, [load]);

  const openAward = useCallback(() => {
    api.get<AwardPreview>(`/api/tenders/${id}/award/preview`)
      .then(setAward)
      .catch((e) => alert(e.message));
  }, [id]);

  useEffect(() => {
    if (search.get("award") === "1") openAward();
  }, [search, openAward]);

  if (!t) return <div className="skel" style={{ height: 300 }} />;

  return (
    <>
      <div className="stage-head">
        <div>
          <span className="eyebrow">{t.ref} · {t.status}</span>
          <h1 style={{ marginTop: 6 }}>{t.vessel} — docking tender</h1>
          <div className="sub">{t.spec_title} · deadline {fmtDate(t.deadline)}</div>
        </div>
        <div style={{ display: "flex", gap: 10 }}>
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

      {tab === "overview" ? <Overview t={t} /> : <Bids tenderId={id} invitations={t.invitations} onChange={load} />}

      {award && <AwardModal id={id} preview={award} onClose={() => { setAward(null); load(); }} />}
    </>
  );
}

function Overview({ t }: { t: TenderDetail }) {
  return (
    <div className="ov-cols">
      <div className="panel">
        <div className="panel-head"><h2>Invited yards</h2><span className="eyebrow dim">{t.invitations.length}</span></div>
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
      </div>
      <div className="panel">
        <div className="panel-head"><h2>Clarifications & addenda</h2></div>
        {t.clarifications.length === 0 && <div style={{ padding: 16, fontSize: 13, color: "var(--ink-3)" }}>No clarifications raised.</div>}
        {t.clarifications.map((c) => (
          <div key={c.id} style={{ padding: "12px 16px", borderBottom: "1px solid var(--hairline)" }}>
            <div style={{ fontSize: 13, fontWeight: 600 }}>{c.question}</div>
            {c.answer && <div style={{ fontSize: 12.5, color: "var(--ink-2)", marginTop: 4 }}>{c.answer}</div>}
            {c.published && <span className="pill signal" style={{ marginTop: 6 }}>Addendum {c.addendum_no}</span>}
          </div>
        ))}
      </div>
    </div>
  );
}

function Bids({ tenderId, invitations, onChange }: { tenderId: string; invitations: TenderDetail["invitations"]; onChange: () => void }) {
  const [ingest, setIngest] = useState(false);
  const withBids = invitations.filter((i) => i.has_bid);
  return (
    <>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 14 }}>
        <div className="sub">{withBids.length} bids received</div>
        <button className="btn btn-quiet" onClick={() => setIngest(true)}>Ingest a quotation (AI)</button>
      </div>
      {withBids.length === 0 ? (
        <div className="empty"><h3>No bids yet</h3><p>Invited yards submit via the portal, or ingest a PDF/text quote for AI review.</p></div>
      ) : (
        <div className="panel">
          <div className="scrollx">
            <table className="grid">
              <thead><tr><th>Yard</th><th>Region</th><th></th></tr></thead>
              <tbody>
                {withBids.map((inv) => (
                  <tr key={inv.yard_id}><td><b>{inv.yard}</b></td><td className="mono" style={{ fontSize: 11.5 }}>{inv.region}</td>
                    <td style={{ textAlign: "right", color: "var(--ink-3)", fontSize: 12 }}>Portal bid</td></tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
      {ingest && <IngestModal tenderId={tenderId} yards={invitations} onClose={() => { setIngest(false); onChange(); }} />}
    </>
  );
}

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
      setMsg(`Parsed ${r.lines} lines (${r.low_confidence} low-confidence). Review before it counts.`);
    } catch (e) {
      setMsg((e as Error).message);
      setBusy(false);
    }
  }

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <h2 style={{ margin: "0 0 4px", fontSize: 18 }}>Ingest a yard quotation</h2>
        <p style={{ fontSize: 13, color: "var(--ink-2)", marginTop: 0 }}>
          Paste a quote; the Bid Parser maps it to the spec grid. Every line lands as a draft
          you review — nothing counts toward leveling until you accept it.
        </p>
        <div className="field" style={{ marginBottom: 12 }}>
          <label>Yard</label>
          <select value={yardId} onChange={(e) => setYardId(e.target.value)}>
            {yards.map((y) => <option key={y.yard_id} value={y.yard_id}>{y.yard}</option>)}
          </select>
        </div>
        <div className="field">
          <label>Quotation text</label>
          <textarea rows={8} value={text} onChange={(e) => setText(e.target.value)}
            placeholder="Paste the yard's quotation here…" />
        </div>
        {msg && <div style={{ fontSize: 13, color: "var(--ink-2)", marginTop: 12 }}>{msg}</div>}
        <div style={{ display: "flex", gap: 10, marginTop: 18, justifyContent: "flex-end" }}>
          <button className="btn btn-quiet" onClick={onClose}>Close</button>
          <button className="btn btn-signal" disabled={busy || !text || !yardId} onClick={submit}>
            {busy ? "Parsing…" : "Parse quotation"}
          </button>
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
    } catch (e) {
      alert((e as Error).message);
      setBusy(false);
    }
  }

  function downloadMemo(aid: string) {
    // Fetch with auth header, then open the blob.
    fetch(`${API_BASE}/api/awards/${aid}/memo.pdf`, { headers: { Authorization: `Bearer ${getToken()}` } })
      .then((r) => r.blob())
      .then((b) => window.open(URL.createObjectURL(b), "_blank"));
  }

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <span className="eyebrow">{preview.tender_ref} · award recommendation</span>
        <h2 style={{ margin: "6px 0 4px", fontSize: 19 }}>Award to {preview.recommended_yard}</h2>
        <div className="mono" style={{ fontSize: 22, fontWeight: 500 }}>{fmtM(preview.recommended_tec_usd)} <small style={{ fontSize: 13, color: "var(--ink-3)" }}>M TEC</small></div>
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
            <button className="btn btn-signal" disabled={busy} onClick={confirm}>
              {busy ? "Awarding…" : "Confirm award"}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
