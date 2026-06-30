"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { BreedingForm } from "@/components/BreedingForm";
import { BreedColorsHint } from "@/components/BreedColorsHint";
import { LitterInference } from "@/components/LitterInference";
import { ResultView } from "@/components/ResultView";
import { TargetColorSearch } from "@/components/TargetColorSearch";
import { calculate, type CalculateInput } from "@/lib/api";
import {
  LANGUAGE_OPTIONS,
  LANGUAGE_STORAGE_KEY,
  UI_TEXT,
  isLanguage,
  languageFromBrowser,
  type Language,
} from "@/lib/i18n";
import type { CalculationResponse } from "@/lib/schema";

type ActiveView = "parent" | "target" | "kitten";

const TAB_LABELS: Record<ActiveView, string> = {
  parent: "Parent Coats",
  target: "Target Coat",
  kitten: "Kitten Coats",
};

function GlobeIcon() {
  return (
    <svg
      aria-hidden="true"
      className="h-5 w-5"
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <circle cx="12" cy="12" r="9" />
      <path d="M3 12h18" />
      <path d="M12 3a14 14 0 0 1 0 18" />
      <path d="M12 3a14 14 0 0 0 0 18" />
    </svg>
  );
}

export default function HomePage() {
  const [activeView, setActiveView] = useState<ActiveView>("parent");
  const [language, setLanguage] = useState<Language>("ja");
  const [languageLoaded, setLanguageLoaded] = useState(false);
  const [languageMenuOpen, setLanguageMenuOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<CalculationResponse | null>(null);
  const languageMenuRef = useRef<HTMLDivElement>(null);
  // 直近の送信で指定された猫種 (認定カラー案内ポップアップの対象)。
  const [submittedBreed, setSubmittedBreed] = useState<string | null>(null);
  const text = UI_TEXT[language];
  const activeIntro = useMemo(() => {
    if (activeView === "parent") return text.tabs.parent;
    if (activeView === "target") return text.tabs.target;
    return text.tabs.kitten;
  }, [activeView, text]);

  useEffect(() => {
    try {
      const stored = window.localStorage.getItem(LANGUAGE_STORAGE_KEY);
      setLanguage(
        isLanguage(stored)
          ? stored
          : languageFromBrowser(window.navigator.language),
      );
    } catch {
      setLanguage(languageFromBrowser(window.navigator.language));
    }
    setLanguageLoaded(true);
  }, []);

  useEffect(() => {
    document.documentElement.lang = language;
    if (!languageLoaded) return;
    try {
      window.localStorage.setItem(LANGUAGE_STORAGE_KEY, language);
    } catch {
      // 保存できない環境でも、現在の画面上の言語切替は維持する。
    }
    window.dispatchEvent(new CustomEvent("ccp:language-change", { detail: language }));
  }, [language, languageLoaded]);

  useEffect(() => {
    if (!languageMenuOpen) return;
    function closeWhenOutside(event: MouseEvent) {
      if (!languageMenuRef.current?.contains(event.target as Node)) {
        setLanguageMenuOpen(false);
      }
    }
    function closeWithEscape(event: KeyboardEvent) {
      if (event.key === "Escape") setLanguageMenuOpen(false);
    }
    document.addEventListener("mousedown", closeWhenOutside);
    document.addEventListener("keydown", closeWithEscape);
    return () => {
      document.removeEventListener("mousedown", closeWhenOutside);
      document.removeEventListener("keydown", closeWithEscape);
    };
  }, [languageMenuOpen]);

  async function handleSubmit(input: CalculateInput) {
    setLoading(true);
    setError(null);
    setSubmittedBreed(input.breed ?? null);
    const outcome = await calculate(input);
    if (outcome.ok) {
      setResult(outcome.data);
    } else {
      setResult(null);
      setError(outcome.message);
    }
    setLoading(false);
  }

  return (
    <main className="mx-auto max-w-3xl px-4 py-8 sm:py-10">
      <header className="mb-7">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <h1 className="text-3xl font-bold tracking-normal text-slate-950">
              {text.app.name}
            </h1>
            <p className="mt-1 text-sm text-slate-600">{text.app.subtitle}</p>
          </div>
          <div className="relative shrink-0" ref={languageMenuRef}>
            <button
              type="button"
              className="inline-flex h-10 w-10 items-center justify-center rounded-full border border-slate-200 bg-white text-slate-700 shadow-sm transition hover:bg-slate-50 focus:outline-none focus:ring-2 focus:ring-slate-400"
              aria-label={text.app.languageLabel}
              aria-haspopup="menu"
              aria-expanded={languageMenuOpen}
              onClick={() => setLanguageMenuOpen((open) => !open)}
            >
              <GlobeIcon />
            </button>
            {languageMenuOpen && (
              <div
                role="menu"
                aria-label={text.app.languageLabel}
                className="absolute right-0 z-30 mt-2 w-40 overflow-hidden rounded-md border border-slate-200 bg-white py-1 text-sm shadow-lg"
              >
                {LANGUAGE_OPTIONS.map((option) => (
                  <button
                    key={option.value}
                    type="button"
                    role="menuitemradio"
                    aria-checked={language === option.value}
                    className={`flex w-full items-center justify-between gap-3 px-3 py-2 text-left ${
                      language === option.value
                        ? "bg-slate-100 font-semibold text-slate-900"
                        : "text-slate-600 hover:bg-slate-50 hover:text-slate-900"
                    }`}
                    onClick={() => {
                      setLanguage(option.value);
                      setLanguageMenuOpen(false);
                    }}
                  >
                    <span>{option.label}</span>
                    {language === option.value && (
                      <span className="text-xs text-slate-500" aria-hidden="true">
                        ✓
                      </span>
                    )}
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>
      </header>

      <div className="mb-5 grid grid-cols-3 gap-1 rounded-md bg-slate-100 p-1">
        {(["parent", "target", "kitten"] as const).map((view) => (
          <button
            key={view}
            type="button"
            className={`min-w-0 rounded px-1.5 py-2 text-center text-xs font-semibold sm:px-3 sm:text-sm ${
              activeView === view
                ? "bg-white text-slate-900 shadow-sm"
                : "text-slate-500 hover:text-slate-800"
            }`}
            onClick={() => setActiveView(view)}
          >
            <span className="block truncate">{TAB_LABELS[view]}</span>
          </button>
        ))}
      </div>

      <section className="mb-5">
        <p className="text-sm leading-6 text-slate-600">
          {activeIntro.description}
        </p>
      </section>

      {activeView === "parent" ? (
        <>
          <div className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
            <BreedingForm
              onSubmit={handleSubmit}
              loading={loading}
              language={language}
            />
          </div>

          {error && (
            <div className="mt-6 rounded-md border border-red-200 bg-red-50 p-4 text-sm text-red-700">
              {error}
              {/* 猫種の認定カラーに無い旨のエラーなら、使える毛色をコピペ可能に案内する。 */}
              {submittedBreed && error.includes("認定カラー") && (
                <BreedColorsHint breed={submittedBreed} />
              )}
            </div>
          )}

          {result && (
            <div className="mt-6 rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
              <ResultView data={result} language={language} />
            </div>
          )}
        </>
      ) : activeView === "target" ? (
        <TargetColorSearch language={language} />
      ) : (
        <LitterInference language={language} />
      )}
    </main>
  );
}
