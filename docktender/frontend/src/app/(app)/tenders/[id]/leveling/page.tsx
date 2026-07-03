"use client";
import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { api, Leveling, TecCard } from "@/lib/api";
import { fmtM, fmtUsd } from "@/lib/format";

const SCOLOR: Record<string, string> = { s1: "var(--s1)", s2: "var(--s2)", s3: "var(--s3)", s4: "var(--s4)" };

export default function LevelingPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [lev, setLev] = useState<Leveling | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [showExposure, setShowExposure] = useState(false);

  useEffect(() => {
    api.get<Leveling>(`/api/tenders/${id}/leveling`).then(setLev).catch((e) => setErr(String(e.message)));
  }, [id]);

  if (err) return <div className="empty"><h3>No leveling yet</h3><p>{err}</p></div>;
  if (!lev) return <div className="skel" style={{ height: 400 }} />;

  return (
    <>
      <div className="stage-head">
        <div>
          <span className="eyebrow">{lev.tender_ref} · leveling</span>
          <h1 style={{ marginTop: 6 }}>Leveling — {lev.cards.length} bids normalized</h1>
          <div className="sub">
            {lev.spec_line_count} spec lines · off-hire at {fmtUsd(lev.offhire_usd_day)}/day
          </div>
        </div>
        <div style={{ display: "flex", gap: 10 }}>
          <button className="btn btn-quiet" onClick={() => router.push(`/tenders/${id}`)}>Back to tender</button>
          <button className="btn btn-signal" onClick={() => router.push(`/tenders/${id}?award=1`)}>Draft award memo</button>
        </div>
      </div>

      <div className="legend">
        {lev.legend.map((l) => (
          <span key={l.key}><i style={{ background: SCOLOR[l.color] }} />{l.label}</span>
        ))}
      </div>

      <div className="tec-cards">
        {lev.cards.map((c) => <TecCardView key={c.bid_id} card={c} />)}
      </div>

      <div className="panel matrix">
        <div className="panel-head">
          <h2>By specification section</h2>
          <span className="eyebrow dim">green edge = lowest priced with scope confirmed</span>
        </div>
        <div className="scrollx">
          <table className="grid">
            <thead>
              <tr>
                <th>Section</th>
                {lev.matrix.columns.map((col) => <th key={col.bid_id} className="num">{col.yard}</th>)}
              </tr>
            </thead>
            <tbody>
              {lev.matrix.rows.map((row) => (
                <tr key={row.section}>
                  <td className="sec-name"><b>{row.name}</b><span>§{row.section}</span></td>
                  {row.cells.map((cell) => (
                    <td key={cell.bid_id} className={`num${cell.best ? " best" : ""}`}>
                      {cell.amount != null ? (
                        <span className="cellv">{fmtUsd(cell.amount)}</span>
                      ) : (
                        <span className="cellv">— <span className="delta hi">{cell.state}</span></span>
                      )}
                      {cell.flag && (
                        <span className="cellflag">
                          <span className={`xchip ${cell.flag.includes("excluded") ? "" : "warn"}`}>{cell.flag}</span>
                        </span>
                      )}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="matrix-foot">
          <div className="note">
            Section totals are normalized to the canonical grid. The lowest sticker is not the lowest
            evaluated cost once exclusions, deviation, off-hire and VO exposure are priced.
          </div>
          <button className="btn btn-quiet" onClick={() => setShowExposure(true)}>Open exposure model</button>
        </div>
      </div>

      {showExposure && (
        <div className="drawer-backdrop" onClick={() => setShowExposure(false)}>
          <div className="drawer" onClick={(e) => e.stopPropagation()}>
            <h2>VO exposure model</h2>
            <p style={{ color: "var(--ink-2)", fontSize: 13, marginTop: 4 }}>
              What each bid’s sticker hides — excluded/unpriced work priced at tariff median, plus
              modelled final-account growth.
            </p>
            {lev.exposure.map((ex) => (
              <div key={ex.bid_id} className="panel" style={{ marginTop: 16 }}>
                <div className="panel-head">
                  <h2>{ex.yard}</h2>
                  <span className="mono" style={{ fontWeight: 600 }}>{fmtUsd(ex.total_usd)}</span>
                </div>
                <div className="scrollx">
                  <table className="grid">
                    <tbody>
                      {ex.items.map((it, i) => (
                        <tr key={i}>
                          <td>{it.label}</td>
                          <td className="num">{fmtUsd(it.exposure_usd)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            ))}
            <button className="btn btn-quiet" style={{ marginTop: 18 }} onClick={() => setShowExposure(false)}>Close</button>
          </div>
        </div>
      )}
    </>
  );
}

function TecCardView({ card }: { card: TecCard }) {
  const totalUsd = card.composition.reduce((s, c) => s + c.usd, 0) || 1;
  return (
    <div className={`tec-card${card.recommended ? " winner" : ""}`}>
      <div className="rank">
        {card.recommended ? <b>RANK {card.rank} · RECOMMENDED</b> : <span>RANK {card.rank}</span>}
        <span>TEC</span>
      </div>
      <h3>{card.yard}</h3>
      <div className="yard-meta">{card.dock} · {card.slot}</div>
      <div className="tec-fig">{fmtM(card.tec_usd)}<small> M</small></div>
      <div className="sticker">
        Bid <span className="mono">{fmtM(card.sticker_usd)} M</span>
        {card.lowest_sticker ? " — lowest sticker" : ""} · {card.dock_days} dock days
      </div>
      <div className="tecbar" role="img" aria-label="TEC composition">
        {card.composition.map((c) => (
          <i key={c.key} style={{ flex: Math.max(1, c.usd), background: SCOLOR[c.color] }} />
        ))}
      </div>
      <div className="tec-flags">
        {card.flags.map((f, i) => <span key={i} className={`xchip ${f.kind === "ok" ? "ok" : f.kind === "warn" ? "warn" : ""}`}>{f.text}</span>)}
      </div>
      <div className="tec-note">{card.note}</div>
    </div>
  );
}
