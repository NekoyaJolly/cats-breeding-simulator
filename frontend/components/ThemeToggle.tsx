"use client";

import { Desktop, Moon, Sun } from "@phosphor-icons/react";
import { useEffect, useState } from "react";
import {
  THEME_ORDER,
  THEME_STORAGE_KEY,
  applyTheme,
  type ThemeChoice,
} from "@/lib/theme";
import { UI_TEXT, type Language } from "@/lib/i18n";

// ライト → ダーク → システム を巡回で切り替えるトグル。言語切替の隣に置く想定。
// マウント前は選択が確定しないため中立 (システム) アイコンを出し、hydration mismatch を避ける。
export function ThemeToggle({ language }: { language: Language }) {
  const text = UI_TEXT[language];
  const [choice, setChoice] = useState<ThemeChoice>("system");
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    const stored = localStorage.getItem(THEME_STORAGE_KEY) as ThemeChoice | null;
    if (stored === "light" || stored === "dark" || stored === "system") {
      setChoice(stored);
    }
    setMounted(true);
  }, []);

  // system 選択時は OS のテーマ変更に追従する。
  useEffect(() => {
    if (choice !== "system") return;
    const mq = window.matchMedia("(prefers-color-scheme: dark)");
    const onChange = () => applyTheme("system");
    mq.addEventListener("change", onChange);
    return () => mq.removeEventListener("change", onChange);
  }, [choice]);

  const cycle = () => {
    const next = THEME_ORDER[(THEME_ORDER.indexOf(choice) + 1) % THEME_ORDER.length];
    setChoice(next);
    localStorage.setItem(THEME_STORAGE_KEY, next);
    applyTheme(next);
  };

  const Icon = !mounted
    ? Desktop
    : choice === "light"
      ? Sun
      : choice === "dark"
        ? Moon
        : Desktop;
  const label = `${text.theme.label}: ${text.theme[choice]}`;

  return (
    <button
      type="button"
      onClick={cycle}
      className="inline-flex h-10 w-10 items-center justify-center rounded-full border border-line bg-surface text-ink-soft shadow-sm transition hover:bg-surface-2 focus:outline-none focus:ring-2 focus:ring-accent/40"
      aria-label={label}
      title={label}
    >
      <Icon aria-hidden="true" className="h-5 w-5" weight="duotone" />
    </button>
  );
}
