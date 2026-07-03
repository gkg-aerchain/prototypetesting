"use client";
import { useEffect, useState } from "react";

export default function SpecificationsPage() {
  const [ready, setReady] = useState(false);
  useEffect(() => setReady(true), []);
  return (
    <>
      <div className="stage-head"><div><h1>Specifications</h1><div className="sub">Coming together in this build</div></div></div>
      <div className="empty">
        <h3>Specifications</h3>
        <p>This section is being wired to live data.</p>
      </div>
    </>
  );
}
