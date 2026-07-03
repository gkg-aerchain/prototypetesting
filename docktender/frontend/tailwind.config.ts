import type { Config } from "tailwindcss";

// The design system is token-driven (see styles/tokens.css). Tailwind is used only
// for occasional layout utilities; colours come from CSS variables, not Tailwind's
// palette, so components stay theme- and accent-aware.
const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        chrome: "var(--chrome)",
        paper: "var(--paper)",
        card: "var(--card)",
        ink: "var(--ink)",
        signal: "var(--signal)",
      },
      fontFamily: {
        sans: ["Geist", "sans-serif"],
        mono: ["Geist Mono", "monospace"],
      },
    },
  },
  plugins: [],
};

export default config;
