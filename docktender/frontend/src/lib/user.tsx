"use client";
import { createContext, useContext, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api, clearToken, getToken, Me } from "./api";

interface UserCtx {
  me: Me | null;
  refresh: () => Promise<void>;
  applyAccent: (accent: string) => void;
  applyTheme: (theme: string) => void;
  logout: () => void;
}

const Ctx = createContext<UserCtx>({
  me: null,
  refresh: async () => {},
  applyAccent: () => {},
  applyTheme: () => {},
  logout: () => {},
});

export function useUser() {
  return useContext(Ctx);
}

function setRoot(attr: string, value: string | null) {
  const root = document.documentElement;
  if (value === null) root.removeAttribute(attr);
  else root.setAttribute(attr, value);
}

export function UserProvider({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [me, setMe] = useState<Me | null>(null);
  const [ready, setReady] = useState(false);

  function applyAccent(accent: string) {
    setRoot("data-accent", accent);
    localStorage.setItem("dt-accent", accent);
  }
  function applyTheme(theme: string) {
    if (theme === "system") setRoot("data-theme", null);
    else setRoot("data-theme", theme);
    localStorage.setItem("dt-theme", theme);
  }

  async function refresh() {
    const u = await api.get<Me>("/api/auth/me");
    setMe(u);
    applyAccent(u.accent);
    applyTheme(u.theme);
  }

  function logout() {
    clearToken();
    setMe(null);
    router.replace("/login");
  }

  useEffect(() => {
    if (!getToken()) {
      router.replace("/login");
      return;
    }
    refresh()
      .catch(() => {
        clearToken();
        router.replace("/login");
      })
      .finally(() => setReady(true));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (!ready) {
    return (
      <div style={{ minHeight: "100vh", display: "grid", placeItems: "center", color: "var(--ink-3)" }}>
        <div className="mono" style={{ fontSize: 13 }}>Loading DockTender…</div>
      </div>
    );
  }

  return (
    <Ctx.Provider value={{ me, refresh, applyAccent, applyTheme, logout }}>{children}</Ctx.Provider>
  );
}
