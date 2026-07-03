"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api, TenderSummary } from "@/lib/api";
import { fmtDate } from "@/lib/format";

const STATUS_PILL: Record<string, string> = {
  draft: "neutral", issued: "signal", closed: "warn", awarded: "good",
};

export default function TendersPage() {
  const router = useRouter();
  const [tenders, setTenders] = useState<TenderSummary[] | null>(null);

  useEffect(() => {
    api.get<TenderSummary[]>("/api/tenders").then(setTenders).catch(() => setTenders([]));
  }, []);

  return (
    <>
      <div className="stage-head">
        <div><h1>Tenders</h1><div className="sub">Docking tenders across the fleet</div></div>
      </div>
      {!tenders ? (
        <div className="skel" style={{ height: 240 }} />
      ) : tenders.length === 0 ? (
        <div className="empty"><h3>No tenders yet</h3><p>Freeze a specification, then issue it to yards.</p></div>
      ) : (
        <div className="panel">
          <div className="scrollx">
            <table className="grid">
              <thead>
                <tr><th>Ref</th><th>Vessel</th><th>Deadline</th><th className="num">Bids</th><th>Status</th><th></th></tr>
              </thead>
              <tbody>
                {tenders.map((t) => (
                  <tr className="rowlink" key={t.id} onClick={() => router.push(`/tenders/${t.id}`)}>
                    <td className="mono" style={{ fontSize: 12.5 }}>{t.ref}</td>
                    <td className="vessel-name"><b>{t.vessel}</b><span>{t.vessel_type}</span></td>
                    <td>{fmtDate(t.deadline)}</td>
                    <td className="num">{t.bids} of {t.invited}</td>
                    <td><span className={`pill ${STATUS_PILL[t.status] || "neutral"}`}>{t.status}</span></td>
                    <td style={{ textAlign: "right" }}>
                      {t.bids > 0 && (
                        <a className="more" onClick={(e) => { e.stopPropagation(); router.push(`/tenders/${t.id}/leveling`); }}
                           style={{ cursor: "pointer" }}>Leveling →</a>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </>
  );
}
