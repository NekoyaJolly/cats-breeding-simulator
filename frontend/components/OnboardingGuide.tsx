"use client";

import {
  Baby,
  ChartBar,
  Crosshair,
  Dna,
  Info,
  ShieldCheck,
  X,
} from "@phosphor-icons/react";
import { useEffect, useState } from "react";
import { UI_TEXT, type Language } from "@/lib/i18n";

export type OnboardingView = "parent" | "target" | "kitten";

const viewTone = {
  parent: {
    Icon: Dna,
    shellClass: "border-emerald-200 bg-emerald-50/70",
    iconClass: "bg-white text-emerald-700",
    buttonClass: "border-emerald-200 text-emerald-800 hover:bg-white",
  },
  target: {
    Icon: Crosshair,
    shellClass: "border-violet-200 bg-violet-50/70",
    iconClass: "bg-white text-violet-700",
    buttonClass: "border-violet-200 text-violet-800 hover:bg-white",
  },
  kitten: {
    Icon: Baby,
    shellClass: "border-amber-200 bg-amber-50/70",
    iconClass: "bg-white text-amber-700",
    buttonClass: "border-amber-200 text-amber-800 hover:bg-white",
  },
} as const satisfies Record<
  OnboardingView,
  {
    Icon: typeof Dna;
    shellClass: string;
    iconClass: string;
    buttonClass: string;
  }
>;

const guideOrder = ["parent", "target", "kitten"] as const satisfies readonly OnboardingView[];

export function OnboardingGuide({
  activeView,
  language,
}: {
  activeView: OnboardingView;
  language: Language;
}) {
  const [open, setOpen] = useState(false);
  const text = UI_TEXT[language].onboarding;
  const activeGuide = text.views[activeView];
  const tone = viewTone[activeView];
  const Icon = tone.Icon;

  useEffect(() => {
    if (!open) return;
    function closeWithEscape(event: KeyboardEvent) {
      if (event.key === "Escape") setOpen(false);
    }
    document.addEventListener("keydown", closeWithEscape);
    return () => document.removeEventListener("keydown", closeWithEscape);
  }, [open]);

  return (
    <>
      <section className={`rounded-lg border px-3 py-3 sm:px-4 ${tone.shellClass}`}>
        <div className="flex items-start gap-3">
          <span
            className={`mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-full ${tone.iconClass}`}
          >
            <Icon aria-hidden="true" className="h-5 w-5" weight="duotone" />
          </span>
          <div className="min-w-0 flex-1">
            <p className="text-sm font-semibold text-slate-900">
              {activeGuide.purpose}
            </p>
            <p className="mt-1 text-xs leading-5 text-slate-600">
              {activeGuide.guide}
            </p>
          </div>
          <button
            type="button"
            className={`inline-flex shrink-0 items-center gap-1 rounded-md border bg-white/60 px-2.5 py-1.5 text-xs font-semibold shadow-sm ${tone.buttonClass}`}
            onClick={() => setOpen(true)}
          >
            <Info aria-hidden="true" className="h-4 w-4" weight="duotone" />
            {text.helpButton}
          </button>
        </div>
      </section>

      {open && (
        <div
          className="fixed inset-0 z-[160] flex items-end justify-center bg-slate-950/35 p-3 sm:items-center sm:p-6"
          role="presentation"
          onMouseDown={(event) => {
            if (event.target === event.currentTarget) setOpen(false);
          }}
        >
          <section
            role="dialog"
            aria-modal="true"
            aria-labelledby="onboarding-help-title"
            className="max-h-[88vh] w-full max-w-2xl overflow-y-auto rounded-lg border border-slate-200 bg-white p-4 shadow-xl sm:p-5"
          >
            <div className="flex items-start justify-between gap-3">
              <div>
                <h2 id="onboarding-help-title" className="text-lg font-semibold text-slate-900">
                  {text.modalTitle}
                </h2>
                <p className="mt-1 text-sm leading-6 text-slate-600">
                  {text.modalSubtitle}
                </p>
              </div>
              <button
                type="button"
                aria-label={text.close}
                className="rounded-full p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-700"
                onClick={() => setOpen(false)}
              >
                <X aria-hidden="true" className="h-5 w-5" />
              </button>
            </div>

            <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-3">
              {guideOrder.map((view) => {
                const guide = text.views[view];
                const GuideIcon = viewTone[view].Icon;
                return (
                  <article key={view} className="rounded-md border border-slate-200 p-3">
                    <div className="flex items-center gap-2">
                      <GuideIcon
                        aria-hidden="true"
                        className="h-4 w-4 text-slate-600"
                        weight="duotone"
                      />
                      <h3 className="text-sm font-semibold text-slate-800">
                        {guide.title}
                      </h3>
                    </div>
                    <p className="mt-2 text-xs leading-5 text-slate-600">
                      {guide.purpose}
                    </p>
                  </article>
                );
              })}
            </div>

            <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2">
              <div className="rounded-md bg-slate-50 p-3">
                <div className="flex items-center gap-2 text-sm font-semibold text-slate-800">
                  <ShieldCheck aria-hidden="true" className="h-4 w-4 text-emerald-700" weight="duotone" />
                  {text.carrierTitle}
                </div>
                <p className="mt-2 text-xs leading-5 text-slate-600">
                  {text.carrierBody}
                </p>
              </div>
              <div className="rounded-md bg-slate-50 p-3">
                <div className="flex items-center gap-2 text-sm font-semibold text-slate-800">
                  <ChartBar aria-hidden="true" className="h-4 w-4 text-sky-700" weight="duotone" />
                  {text.resultTitle}
                </div>
                <p className="mt-2 text-xs leading-5 text-slate-600">
                  {text.resultBody}
                </p>
              </div>
            </div>
          </section>
        </div>
      )}
    </>
  );
}
