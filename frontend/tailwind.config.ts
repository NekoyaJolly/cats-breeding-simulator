import type { Config } from "tailwindcss";

// トークンは globals.css の CSS 変数 (R G B チャンネル) を参照する。
// rgb(var(--x) / <alpha-value>) にすることで bg-surface / text-ink/70 のような不透明度指定も効く。
const token = (name: string) => `rgb(var(--${name}) / <alpha-value>)`;

const config: Config = {
  darkMode: "class",
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: token("bg"),
        surface: token("surface"),
        "surface-2": token("surface-2"),
        inset: token("inset"),
        ink: token("ink"),
        "ink-soft": token("ink-soft"),
        muted: token("muted"),
        line: token("line"),
        "line-soft": token("line-soft"),
        accent: token("accent"),
        "accent-ink": token("accent-ink"),
        male: token("male"),
        female: token("female"),
        confirmed: token("confirmed"),
        "confirmed-bg": token("confirmed-bg"),
        conditional: token("conditional"),
        "conditional-bg": token("conditional-bg"),
        danger: token("danger"),
        "danger-bg": token("danger-bg"),
      },
    },
  },
  plugins: [],
};

export default config;
