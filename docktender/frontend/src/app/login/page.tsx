"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { api, setToken, ApiError } from "@/lib/api";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("superintendent@docktender.demo");
  const [password, setPassword] = useState("DryDock2026!");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const { access_token } = await api.post<{ access_token: string }>("/api/auth/login", {
        email,
        password,
      });
      setToken(access_token);
      router.replace("/programme");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Sign-in failed");
      setBusy(false);
    }
  }

  return (
    <div style={{ minHeight: "100vh", display: "grid", placeItems: "center", background: "var(--chrome)" }}>
      <div style={{ width: 380, maxWidth: "90vw" }}>
        <div style={{ textAlign: "center", marginBottom: 28 }}>
          <div style={{ fontSize: 30, fontWeight: 600, letterSpacing: "-.02em", color: "#fff" }}>
            Dock<span style={{ color: "var(--signal)" }}>Tender</span>
          </div>
          <div style={{ color: "var(--chrome-dim)", fontSize: 14, marginTop: 6 }}>
            The tender room for dry-docking
          </div>
        </div>
        <form
          onSubmit={submit}
          style={{
            background: "var(--card)", border: "1px solid var(--hairline)", borderRadius: 8,
            padding: 28, display: "grid", gap: 16,
          }}
        >
          <div className="field">
            <label>Email</label>
            <input value={email} onChange={(e) => setEmail(e.target.value)} type="email" autoComplete="username" />
          </div>
          <div className="field">
            <label>Password</label>
            <input value={password} onChange={(e) => setPassword(e.target.value)} type="password" autoComplete="current-password" />
          </div>
          {error && <div style={{ color: "var(--crit)", fontSize: 13 }}>{error}</div>}
          <button className="btn btn-signal" type="submit" disabled={busy} style={{ width: "100%" }}>
            {busy ? "Signing in…" : "Sign in"}
          </button>
          <div style={{ fontSize: 11.5, color: "var(--ink-3)", textAlign: "center" }}>
            Demo tenant · Galene Maritime — credentials pre-filled
          </div>
        </form>
      </div>
    </div>
  );
}
