export function fmtDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  const d = new Date(iso);
  return d.toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "2-digit" });
}

export function fmtUsd(n: number, opts: { millions?: boolean } = {}): string {
  if (opts.millions) return `$${(n / 1e6).toFixed(2)}M`;
  return n.toLocaleString("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 });
}

export function fmtM(n: number): string {
  return `$${(n / 1e6).toFixed(2)}`;
}

export function fmtNum(n: number): string {
  return n.toLocaleString("en-US");
}
