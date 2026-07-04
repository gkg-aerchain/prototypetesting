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
      const { access_token } = await api.post<{ access_token: string }>("/api/auth/login", { email, password });
      setToken(access_token);
      router.replace("/programme");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Sign-in failed");
      setBusy(false);
    }
  }

  return (
    <div className="auth-wrap">
      <div className="auth-aurora" aria-hidden />
      <div className="auth-grid" aria-hidden />
      <div className="auth-card">
        <div className="auth-brand">Dock<em>Tender</em></div>
        <p className="auth-tag">The tender room for dry-docking — plan the window, normalize every bid, and rank yards on <b>total evaluated cost</b>.</p>
        <form onSubmit={submit} className="auth-form">
          <div className="field">
            <label>Email</label>
            <input value={email} onChange={(e) => setEmail(e.target.value)} type="email" autoComplete="username" />
          </div>
          <div className="field">
            <label>Password</label>
            <input value={password} onChange={(e) => setPassword(e.target.value)} type="password" autoComplete="current-password" />
          </div>
          {error && <div className="auth-err">{error}</div>}
          <button className="btn btn-signal" type="submit" disabled={busy} style={{ width: "100%" }}>
            {busy ? "Signing in…" : "Sign in →"}
          </button>
        </form>
        <div className="auth-demo">
          <span className="pill signal">Demo</span>
          Galene Maritime tenant · credentials pre-filled
        </div>
      </div>
    </div>
  );
}
