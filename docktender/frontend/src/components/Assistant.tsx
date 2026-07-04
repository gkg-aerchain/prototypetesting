"use client";
import { useState } from "react";
import { api, ApiError } from "@/lib/api";
import { Icons, NavIcon } from "./icons";

interface Msg { role: "user" | "assistant"; content: string; }

const SUGGESTIONS = [
  "Why is Besiktas ranked last on TND-2026-014?",
  "Which vessel’s docking window closes next?",
  "What’s the guide norm for shell-plate steel renewal?",
];

export function Assistant() {
  const [open, setOpen] = useState(false);
  const [msgs, setMsgs] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);

  async function sendText(text: string) {
    const q = text.trim();
    if (!q) return;
    const next = [...msgs, { role: "user" as const, content: q }];
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
            <span className="assist-title"><span className="dot" />Superintendent’s assistant</span>
            <button onClick={() => setOpen(false)} aria-label="Close">×</button>
          </div>
          <div className="assist-body">
            {msgs.length === 0 && (
              <>
                <div className="assist-hint">
                  Ask about the programme, a tender’s leveling, a vessel’s docking window, or a guide norm.
                  I read your fleet live and cite evidence — and never reveal a sealed bid before its deadline.
                </div>
                <div className="assist-suggest">
                  {SUGGESTIONS.map((s) => (
                    <button key={s} onClick={() => sendText(s)}>{s}</button>
                  ))}
                </div>
              </>
            )}
            {msgs.map((m, i) => (
              <div key={i} className={`assist-msg ${m.role}`}>{m.content}</div>
            ))}
            {busy && <div className="assist-msg assistant thinking">Thinking…</div>}
          </div>
          <form className="assist-input" onSubmit={(e) => { e.preventDefault(); sendText(input); }}>
            <input value={input} onChange={(e) => setInput(e.target.value)} placeholder="Ask anything…" disabled={busy} />
            <button className="btn btn-signal" type="submit" disabled={busy || !input.trim()}>Send</button>
          </form>
        </div>
      )}
    </>
  );
}
