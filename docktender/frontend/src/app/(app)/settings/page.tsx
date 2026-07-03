"use client";
import { useState } from "react";
import { api, Me } from "@/lib/api";
import { useUser } from "@/lib/user";

const ACCENTS = [
  { key: "cerise", label: "Cerise", dots: ["#D62A6E", "#AD1257"] },
  { key: "marigold", label: "Marigold", dots: ["#B8860B", "#7E5C00"] },
  { key: "verdigris", label: "Verdigris", dots: ["#0F8C7D", "#0A6A5E"] },
  { key: "azure", label: "Azure", dots: ["#2E6BE6", "#1E4FD0"] },
  { key: "violet", label: "Violet", dots: ["#6D4AE7", "#5433C4"] },
];
const THEMES = [
  { key: "system", label: "System" },
  { key: "light", label: "Light" },
  { key: "dark", label: "Dark" },
];

export default function SettingsPage() {
  const { me, refresh, applyAccent, applyTheme } = useUser();
  const [accent, setAccent] = useState(me?.accent || "cerise");
  const [theme, setTheme] = useState(me?.theme || "system");
  const [saved, setSaved] = useState(false);

  async function pickAccent(key: string) {
    setAccent(key);
    applyAccent(key); // instant, optimistic
    await api.patch<Me>("/api/me", { accent: key });
    await refresh();
    flash();
  }
  async function pickTheme(key: string) {
    setTheme(key);
    applyTheme(key);
    await api.patch<Me>("/api/me", { theme: key });
    await refresh();
    flash();
  }
  function flash() {
    setSaved(true);
    setTimeout(() => setSaved(false), 1400);
  }

  return (
    <>
      <div className="stage-head">
        <div>
          <h1>Settings</h1>
          <div className="sub">{me?.full_name} · {me?.email}</div>
        </div>
        {saved && <span className="pill good">Saved</span>}
      </div>

      <div style={{ display: "grid", gap: 24, maxWidth: 760 }}>
        <section className="panel" style={{ padding: 24 }}>
          <div className="eyebrow" style={{ marginBottom: 4 }}>Appearance</div>
          <h2 style={{ margin: "0 0 4px", fontSize: 16 }}>The signal accent</h2>
          <p style={{ margin: "0 0 18px", fontSize: 13, color: "var(--ink-2)", maxWidth: "60ch" }}>
            One colour marks time and the recommended answer across every screen — the
            today line, closing windows, the primary action, the winning bid. Pick the one
            you want; it applies instantly and everywhere.
          </p>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(140px, 1fr))", gap: 12 }}>
            {ACCENTS.map((a) => (
              <button key={a.key} onClick={() => pickAccent(a.key)}
                style={{
                  textAlign: "left", background: "var(--card)", cursor: "pointer",
                  border: accent === a.key ? "2px solid var(--signal)" : "1px solid var(--hairline-2)",
                  borderRadius: 8, padding: 14, fontFamily: "var(--sans)", color: "var(--ink)",
                }}>
                <div style={{ display: "flex", gap: 6, marginBottom: 10 }}>
                  {a.dots.map((d) => <i key={d} style={{ width: 20, height: 20, borderRadius: "50%", background: d }} />)}
                </div>
                <b style={{ display: "block", fontSize: 14, fontWeight: 600 }}>{a.label}</b>
                <span className="mono" style={{ fontSize: 11, color: "var(--ink-3)" }}>{a.dots[0]}</span>
              </button>
            ))}
          </div>
        </section>

        <section className="panel" style={{ padding: 24 }}>
          <h2 style={{ margin: "0 0 14px", fontSize: 16 }}>Theme</h2>
          <div style={{ display: "flex", gap: 10 }}>
            {THEMES.map((t) => (
              <button key={t.key} onClick={() => pickTheme(t.key)}
                className={`btn ${theme === t.key ? "btn-signal" : "btn-quiet"}`}>
                {t.label}
              </button>
            ))}
          </div>
        </section>
      </div>
    </>
  );
}
