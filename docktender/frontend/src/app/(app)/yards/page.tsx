"use client";
import { useEffect, useState } from "react";

export default function YardsPage() {
  const [ready, setReady] = useState(false);
  useEffect(() => setReady(true), []);
  return (
    <>
      <div className="stage-head"><div><h1>Yards</h1><div className="sub">Coming together in this build</div></div></div>
      <div className="empty">
        <h3>Yards</h3>
        <p>This section is being wired to live data.</p>
      </div>
    </>
  );
}
