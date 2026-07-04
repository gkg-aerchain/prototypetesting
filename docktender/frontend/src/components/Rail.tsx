"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Icons, NavIcon } from "./icons";
import { useUser } from "@/lib/user";

const NAV = [
  { href: "/programme", label: "Programme", icon: Icons.programme },
  { href: "/fleet", label: "Fleet", icon: Icons.fleet },
  { href: "/specifications", label: "Specifications", icon: Icons.specs },
  { href: "/tenders", label: "Tenders", icon: Icons.tenders },
  { href: "/yards", label: "Yards", icon: Icons.yards },
  { href: "/executions", label: "Executions", icon: Icons.executions },
  { href: "/settlements", label: "Settlements", icon: Icons.settlements },
];

export function Rail() {
  const pathname = usePathname();
  const { me, logout } = useUser();

  return (
    <nav className="rail">
      <div className="brand">
        Dock<em>Tender</em>
      </div>
      <button className="rail-cmdk" onClick={() => window.dispatchEvent(new Event("cmdk-open"))}>
        <span>Search &amp; commands</span>
        <kbd>⌘K</kbd>
      </button>
      {NAV.map((n) => {
        const active = pathname === n.href || pathname.startsWith(n.href + "/");
        return (
          <Link key={n.href} href={n.href} className={`nav${active ? " active" : ""}`}>
            <NavIcon d={n.icon} />
            {n.label}
          </Link>
        );
      })}
      <div style={{ marginTop: "auto", display: "flex", flexDirection: "column", gap: 2 }}>
        <Link
          href="/settings"
          className={`nav${pathname.startsWith("/settings") ? " active" : ""}`}
        >
          <NavIcon d={Icons.settings} />
          Settings
        </Link>
        <div className="rail-foot">
          <b>{me ? `${me.org} · ${me.vessel_count} vessel${me.vessel_count === 1 ? "" : "s"}` : "—"}</b>
          {me?.full_name || me?.email || "—"} — Docking Supt.
          <button type="button" className="rail-signout" onClick={logout}>Sign out</button>
        </div>
      </div>
    </nav>
  );
}
