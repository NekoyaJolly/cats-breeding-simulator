"use client";

import {
  Baby,
  CheckCircle,
  Crosshair,
  Dna,
  GlobeHemisphereEast,
} from "@phosphor-icons/react";
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

const TAB_ITEMS = [
  {
    view: "parent",
    label: "Parent Coats",
    Icon: Dna,
    iconClass: "text-emerald-600",
  },
  {
    view: "target",
    label: "Target Coat",
    Icon: Crosshair,
    iconClass: "text-violet-600",
  },
  {
    view: "kitten",
    label: "Kitten Coats",
    Icon: Baby,
    iconClass: "text-amber-600",
  },
] as const satisfies readonly {
  view: ActiveView;
  label: string;
  Icon: typeof Dna;
  iconClass: string;
}[];

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
    <main className="mx-auto max-w-3xl px-3 py-5 sm:px-4 sm:py-10">
      <header className="mb-4 sm:mb-7">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <h1 className="text-2xl font-bold tracking-normal text-slate-950 sm:text-3xl">
              {text.app.name}
            </h1>
            <p className="mt-1 text-sm text-slate-600">{text.app.subtitle}</p>
          </div>
          <div className="relative shrink-0" ref={languageMenuRef}>
            <button
              type="button"
              className="inline-flex h-10 w-10 items-center justify-center rounded-full border border-sky-100 bg-white shadow-sm transition hover:bg-sky-50 focus:outline-none focus:ring-2 focus:ring-sky-300"
              aria-label={text.app.languageLabel}
              aria-expanded={languageMenuOpen}
              onClick={() => setLanguageMenuOpen((open) => !open)}
            >
              <GlobeHemisphereEast
                aria-hidden="true"
                className="h-5 w-5 text-sky-600"
                weight="duotone"
              />
            </button>
            {languageMenuOpen && (
              <div
                aria-label={text.app.languageLabel}
                className="absolute right-0 z-30 mt-2 w-40 overflow-hidden rounded-md border border-slate-200 bg-white py-1 text-sm shadow-lg"
              >
                {LANGUAGE_OPTIONS.map((option) => (
                  <button
                    key={option.value}
                    type="button"
                    aria-pressed={language === option.value}
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
                      <CheckCircle
                        aria-hidden="true"
                        className="h-4 w-4 text-emerald-600"
                        weight="fill"
                      />
                    )}
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>
      </header>

      <div className="mb-3 grid grid-cols-3 gap-1 rounded-md bg-slate-100 p-1 sm:mb-5">
        {TAB_ITEMS.map((tab) => {
          const Icon = tab.Icon;
          const active = activeView === tab.view;
          return (
            <button
              key={tab.view}
              type="button"
              className={`min-w-0 rounded px-1 py-1.5 text-center text-xs font-semibold sm:px-3 sm:py-2 sm:text-sm ${
                active
                  ? "bg-white text-slate-900 shadow-sm"
                  : "text-slate-500 hover:text-slate-800"
              }`}
              onClick={() => setActiveView(tab.view)}
            >
              <span className="flex min-w-0 items-center justify-center gap-1.5">
                <Icon
                  aria-hidden="true"
                  className={`h-4 w-4 shrink-0 ${active ? tab.iconClass : "text-slate-400"}`}
                  weight={active ? "duotone" : "regular"}
                />
                <span className="truncate">{tab.label}</span>
              </span>
            </button>
          );
        })}
      </div>

      <section className="mb-4 sm:mb-5">
        <p className="text-xs leading-5 text-slate-600 sm:text-sm sm:leading-6">
          {activeIntro.description}
        </p>
      </section>

      {activeView === "parent" ? (
        <>
          <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm sm:p-6">
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
            <div className="mt-6 rounded-lg border border-slate-200 bg-white p-4 shadow-sm sm:p-6">
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
