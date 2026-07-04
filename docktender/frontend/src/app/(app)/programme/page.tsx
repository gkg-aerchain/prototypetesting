"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api, Programme } from "@/lib/api";
import { Waterline } from "@/components/Waterline";
import { fmtDate } from "@/lib/format";

export default function ProgrammePage() {
  const router = useRouter();
  const [p, setP] = useState<Programme | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [resolving, setResolving] = useState<string | null>(null);

  useEffect(() => {
    api.get<Programme>("/api/programme").then(setP).catch((e) => setErr(String(e.message)));
  }, []);

  const go = (link: string | null) => router.push(link || "/tenders");

  async function resolve(id: string) {
    setResolving(id);
    try {
      await api.patch(`/api/agents/events/${id}`);
      setP((cur) => (cur ? { ...cur, queue: cur.queue.filter((q) => q.id !== id) } : cur));
    } finally {
      setResolving(null);
    }
  }

  if (err) return <div className="empty"><h3>Couldn’t load the programme</h3><p>{err}</p></div>;
  if (!p) return <ProgrammeSkeleton />;

  return (
    <>
      <div className="stage-head">
        <div>
          <h1>Docking programme</h1>
          <div className="sub">
            {new Date(p.today).toLocaleDateString("en-GB", { weekday: "long", day: "numeric", month: "long", year: "numeric" })}
            {" · "}{p.vessel_count} vessels · {p.docking_count} dockings in flight
          </div>
        </div>
        <button className="btn btn-primary" onClick={() => router.push("/specifications")}>
          Start a specification
        </button>
      </div>

      <Waterline today={p.today} vessels={p.waterline} />

      <div className="focus-strip">
        {p.focus && (
          <div className="stat focus">
            <div className="k-label">Next hard stop · {p.focus.vessel} · {p.focus.driver}</div>
            <div className="k-value">{p.focus.days_left}<small> days</small></div>
            <div className="k-sub">{p.focus.sub}</div>
            <div className="k-actions"><a onClick={() => go(p.focus!.link)} style={{ cursor: "pointer" }}>Open leveling →</a></div>
          </div>
        )}
        {p.stats.map((s) => (
          <div className="stat" key={s.key}>
            <div className="k-label">{s.label}</div>
            <div className="k-value">
              {formatStatValue(s.key, s.value)}
              {s.unit && <small> {s.unit}</small>}
            </div>
            <div className={`k-sub${s.key === "final_vs_quoted" ? " down" : ""}`}>{s.sub}</div>
          </div>
        ))}
      </div>

      <div className="ov-cols">
        <div className="panel">
          <div className="panel-head">
            <h2>Fleet docking clock</h2>
            <a className="more" onClick={() => router.push("/tenders")} style={{ cursor: "pointer" }}>
              All {p.vessel_count} vessels →
            </a>
          </div>
          <div className="scrollx">
            <table className="grid">
              <thead>
                <tr><th>Vessel</th><th>Driver</th><th className="num">Window closes</th><th>Status</th></tr>
              </thead>
              <tbody>
                {p.fleet_clock.slice(0, 6).map((v) => (
                  <tr className="rowlink" key={v.id} onClick={() => go(v.link)}>
                    <td className="vessel-name"><b>{v.name}</b><span>{v.sub}</span></td>
                    <td>{v.driver}</td>
                    <td className="num">{windowCell(v)}</td>
                    <td><span className={`pill ${v.pill_kind}`}>{v.pill}</span></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div style={{ display: "grid", gap: 14 }}>
          <div className="panel">
            <div className="panel-head"><h2>Needs your decision</h2><span className="eyebrow dim">{p.queue.length}</span></div>
            {p.queue.length === 0 && <div style={{ padding: 16, fontSize: 13, color: "var(--ink-3)" }}>Nothing waiting on you.</div>}
            {p.queue.map((q) => (
              <div className="queue-item" key={q.id}>
                <div className="q"><b>{q.message}</b><span>{q.agent_label}{q.vessel ? ` · ${q.vessel}` : ""}</span></div>
                <div style={{ display: "flex", gap: 6 }}>
                  {q.link && <button className="btn btn-quiet" onClick={() => go(q.link)}>Review</button>}
                  <button className="btn btn-quiet" disabled={resolving === q.id} onClick={() => resolve(q.id)}>
                    {resolving === q.id ? "…" : "Resolve"}
                  </button>
                </div>
              </div>
            ))}
          </div>
          <div className="panel">
            <div className="panel-head"><h2>Agent activity</h2><span className="eyebrow dim">Log</span></div>
            {p.feed.map((f) => (
              <div className="feed-item" key={f.id}>
                <span className={`sev ${f.severity}`} />
                <div>
                  <div className="who"><b>{f.agent_label}</b><span>{f.age}</span></div>
                  <p>{f.message}</p>
                  {f.evidence && <span className="evidence">{f.evidence}</span>}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </>
  );
}

function formatStatValue(key: string, value: number): string {
  if (key === "programme") return `$${value}`;
  if (key === "final_vs_quoted") return `+${value}`;
  return String(value);
}

function windowCell(v: { hard_stop: string | null; days_left: number | null; category: string; severity: string }) {
  if (v.category === "in_dock") return <>in dock</>;
  if (v.category === "completed") return <>completed</>;
  if (!v.hard_stop || v.days_left === null) return <>—</>;
  const isSignal = v.severity === "signal";
  return (
    <>
      {fmtDate(v.hard_stop)} ·{" "}
      <b style={isSignal ? { color: "var(--signal-deep)" } : undefined}>{v.days_left} d</b>
    </>
  );
}

function ProgrammeSkeleton() {
  return (
    <>
      <div className="stage-head"><div><h1>Docking programme</h1><div className="sub">Loading…</div></div></div>
      <div className="skel" style={{ height: 200, marginBottom: 16 }} />
      <div className="focus-strip">
        {[0, 1, 2, 3].map((i) => <div key={i} className="skel" style={{ height: 120 }} />)}
      </div>
    </>
  );
}
