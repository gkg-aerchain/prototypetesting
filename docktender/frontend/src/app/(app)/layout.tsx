"use client";
import { UserProvider } from "@/lib/user";
import { Rail } from "@/components/Rail";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <UserProvider>
      <div className="app-shell">
        <Rail />
        <main className="stage">{children}</main>
      </div>
    </UserProvider>
  );
}
