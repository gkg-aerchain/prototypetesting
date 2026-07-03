"use client";
import { useState } from "react";
import { api, ApiError } from "@/lib/api";
import { Icons, NavIcon } from "./icons";

interface Msg { role: "user" | "assistant"; content: string; }

export function Assistant() {
  const [open, setOpen] = useState(false);
  const [msgs, setMsgs] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);

  async function send() {
    if (!input.trim()) return;
    const next = [...msgs, { role: "user" as const, content: input }];
    setMsgs(next);
    setInput("");
    setBusy(true);
    try {
      const r = await api.post<{ reply: string }>("/api/ai/chat", { messages: next });
      setMsgs([...next, { role: "assistant", content: r.reply }]);
    } catch (e) {
      const msg = e instanceof ApiError && e.status === 503
        ? "The assistant needs an Anthropic API key configured on the server. Everything else works without it."
        : (e as Error).message;
      setMsgs([...next, { role: "assistant", content: msg }]);
    }
    setBusy(false);
  }

  return (
    <>
      <button className="assist-fab" onClick={() => setOpen(!open)} aria-label="Assistant">
        <NavIcon d={Icons.assistant} />
      </button>
      {open && (
        <div className="assist-panel">
          <div className="assist-head">
            <b>Assistant</b>
            <button onClick={() => setOpen(false)} aria-label="Close" style={{ background: "none", border: "none", color: "var(--chrome-dim)", cursor: "pointer", fontSize: 18 }}>×</button>
          </div>
          <div className="assist-body">
            {msgs.length === 0 && (
              <div className="assist-hint">
                Ask about the programme, a tender’s leveling (e.g. “Why is Besiktas ranked last on
                TND-2026-014?”), a vessel’s window, or a guide norm.
              </div>
            )}
            {msgs.map((m, i) => (
              <div key={i} className={`assist-msg ${m.role}`}>{m.content}</div>
            ))}
            {busy && <div className="assist-msg assistant" style={{ opacity: .6 }}>Thinking…</div>}
          </div>
          <form className="assist-input" onSubmit={(e) => { e.preventDefault(); send(); }}>
            <input value={input} onChange={(e) => setInput(e.target.value)} placeholder="Ask the superintendent’s assistant…" disabled={busy} />
            <button className="btn btn-signal" type="submit" disabled={busy || !input.trim()}>Send</button>
          </form>
        </div>
      )}
    </>
  );
}
