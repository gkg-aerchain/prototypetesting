"use client";
import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { useUser } from "@/lib/user";

interface Cmd { id: string; label: string; hint?: string; group: string; run: () => void; }

export function CommandPalette() {
  const router = useRouter();
  const { applyTheme, logout } = useUser();
  const [open, setOpen] = useState(false);
  const [q, setQ] = useState("");
  const [active, setActive] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  const commands = useMemo<Cmd[]>(() => {
    const go = (href: string) => () => { router.push(href); setOpen(false); };
    return [
      { id: "programme", label: "Go to Programme", group: "Navigate", run: go("/programme") },
      { id: "fleet", label: "Go to Fleet", group: "Navigate", run: go("/fleet") },
      { id: "specs", label: "Go to Specifications", group: "Navigate", run: go("/specifications") },
      { id: "tenders", label: "Go to Tenders", group: "Navigate", run: go("/tenders") },
      { id: "yards", label: "Go to Yards", group: "Navigate", run: go("/yards") },
      { id: "executions", label: "Go to Executions", group: "Navigate", run: go("/executions") },
      { id: "settlements", label: "Go to Settlements", group: "Navigate", run: go("/settlements") },
      { id: "settings", label: "Go to Settings", group: "Navigate", run: go("/settings") },
      { id: "new-spec", label: "New specification", hint: "from a vessel", group: "Create", run: go("/fleet") },
      { id: "add-vessel", label: "Add a vessel", group: "Create", run: go("/fleet") },
      { id: "theme-dark", label: "Theme: Dark", group: "Preferences", run: () => { applyTheme("dark"); setOpen(false); } },
      { id: "theme-light", label: "Theme: Light", group: "Preferences", run: () => { applyTheme("light"); setOpen(false); } },
      { id: "signout", label: "Sign out", group: "Session", run: () => { logout(); } },
    ];
  }, [router, applyTheme, logout]);

  const filtered = useMemo(() => {
    const s = q.trim().toLowerCase();
    if (!s) return commands;
    return commands.filter((c) => (c.label + " " + c.group + " " + (c.hint || "")).toLowerCase().includes(s));
  }, [q, commands]);

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") { e.preventDefault(); setOpen((o) => !o); }
      else if (e.key === "Escape") setOpen(false);
    }
    function onOpen() { setOpen(true); }
    window.addEventListener("keydown", onKey);
    window.addEventListener("cmdk-open", onOpen);
    return () => { window.removeEventListener("keydown", onKey); window.removeEventListener("cmdk-open", onOpen); };
  }, []);

  useEffect(() => { if (open) { setQ(""); setActive(0); setTimeout(() => inputRef.current?.focus(), 30); } }, [open]);
  useEffect(() => { setActive(0); }, [q]);

  if (!open) return null;

  function onKeyDown(e: React.KeyboardEvent) {
    if (e.key === "ArrowDown") { e.preventDefault(); setActive((a) => Math.min(a + 1, filtered.length - 1)); }
    else if (e.key === "ArrowUp") { e.preventDefault(); setActive((a) => Math.max(a - 1, 0)); }
    else if (e.key === "Enter") { e.preventDefault(); filtered[active]?.run(); }
  }

  let lastGroup = "";
  return (
    <div className="cmdk-backdrop" onClick={() => setOpen(false)}>
      <div className="cmdk" onClick={(e) => e.stopPropagation()}>
        <input ref={inputRef} className="cmdk-input" value={q} onChange={(e) => setQ(e.target.value)} onKeyDown={onKeyDown}
          placeholder="Search commands, screens, actions…" />
        <div className="cmdk-list">
          {filtered.length === 0 && <div className="cmdk-empty">No matches</div>}
          {filtered.map((c, i) => {
            const head = c.group !== lastGroup ? (lastGroup = c.group) : null;
            return (
              <div key={c.id}>
                {head && <div className="cmdk-group">{head}</div>}
                <button className={`cmdk-item${i === active ? " active" : ""}`} onMouseEnter={() => setActive(i)} onClick={c.run}>
                  <span>{c.label}</span>
                  {c.hint && <span className="cmdk-hint">{c.hint}</span>}
                </button>
              </div>
            );
          })}
        </div>
        <div className="cmdk-foot"><span><kbd>↑</kbd><kbd>↓</kbd> navigate</span><span><kbd>↵</kbd> select</span><span><kbd>esc</kbd> close</span></div>
      </div>
    </div>
  );
}
