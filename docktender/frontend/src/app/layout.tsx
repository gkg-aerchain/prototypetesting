import type { Metadata } from "next";
import "../styles/globals.css";

export const metadata: Metadata = {
  title: "DockTender",
  description: "The tender room for dry-docking.",
};

// Apply the saved theme + signal accent before paint to avoid a flash. The real
// values are hydrated from /api/auth/me once the app loads; this reads the mirror
// kept in localStorage.
const themeScript = `
(function () {
  try {
    var t = localStorage.getItem('dt-theme') || 'system';
    var a = localStorage.getItem('dt-accent') || 'cerise';
    var root = document.documentElement;
    if (t === 'light' || t === 'dark') root.setAttribute('data-theme', t);
    root.setAttribute('data-accent', a);
  } catch (e) {}
})();
`;

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeScript }} />
      </head>
      <body>{children}</body>
    </html>
  );
}
