"use client";

import { Question } from "@phosphor-icons/react";
import { useCallback, useEffect, useRef } from "react";
import { driver, type Driver, type DriverHook, type DriveStep } from "driver.js";
import { UI_TEXT, type Language } from "@/lib/i18n";

export type AppTourView = "parent" | "target" | "kitten";

export const APP_TOUR_COMPLETED_KEY = "ccp:onboarding:v2:completed";

const AUTO_TOUR_DELAY_MS = 650;
const TAB_SWITCH_DELAY_MS = 180;

type TourMode = "full" | "current";

type AppTourProps = {
  language: Language;
  languageReady: boolean;
  activeView: AppTourView;
  onViewChange: (view: AppTourView) => void;
};

function hasCompletedTour(): boolean {
  try {
    return window.localStorage.getItem(APP_TOUR_COMPLETED_KEY) === "true";
  } catch {
    return false;
  }
}

function markTourCompleted(): void {
  try {
    window.localStorage.setItem(APP_TOUR_COMPLETED_KEY, "true");
  } catch {
    // localStorage が使えない環境でも、ツアー自体は継続できるようにする。
  }
}

export function AppTour({
  language,
  languageReady,
  activeView,
  onViewChange,
}: AppTourProps) {
  const text = UI_TEXT[language].onboarding;
  const autoStartedRef = useRef(false);
  const initialViewRef = useRef<AppTourView>("parent");
  const tourRef = useRef<Driver | null>(null);
  const startTimerRef = useRef<number | null>(null);

  const clearStartTimer = useCallback(() => {
    if (startTimerRef.current !== null) {
      window.clearTimeout(startTimerRef.current);
      startTimerRef.current = null;
    }
  }, []);

  const switchToView = useCallback(
    (view: AppTourView): DriverHook =>
      (_element, _step, options) => {
        onViewChange(view);
        window.setTimeout(() => {
          options.driver.moveNext();
        }, TAB_SWITCH_DELAY_MS);
      },
    [onViewChange],
  );

  const parentSteps = useCallback(
    (): DriveStep[] => [
      {
        element: "[data-tour='parent-panel']",
        popover: {
          title: text.steps.parent.title,
          description: text.steps.parent.description,
          side: "top",
          align: "start",
        },
      },
      {
        element: "[data-tour='parent-carriers']",
        popover: {
          title: text.steps.carriers.title,
          description: text.steps.carriers.description,
          side: "top",
          align: "start",
        },
      },
    ],
    [text],
  );

  const targetSteps = useCallback(
    (): DriveStep[] => [
      {
        element: "[data-tour='target-panel']",
        popover: {
          title: text.steps.target.title,
          description: text.steps.target.description,
          side: "top",
          align: "start",
        },
      },
    ],
    [text],
  );

  const kittenSteps = useCallback(
    (): DriveStep[] => [
      {
        element: "[data-tour='kitten-panel']",
        popover: {
          title: text.steps.kitten.title,
          description: text.steps.kitten.description,
          side: "top",
          align: "start",
        },
      },
    ],
    [text],
  );

  const helpStep = useCallback(
    (): DriveStep => ({
      element: "[data-tour='tour-help']",
      popover: {
        title: text.steps.help.title,
        description: text.steps.help.description,
        side: "bottom",
        align: "end",
      },
    }),
    [text],
  );

  const buildFullSteps = useCallback((): DriveStep[] => {
    const moveToTarget = switchToView("target");
    const moveToKitten = switchToView("kitten");

    return [
      {
        element: "[data-tour='app-tabs']",
        popover: {
          title: text.steps.tabs.title,
          description: text.steps.tabs.description,
          side: "bottom",
          align: "center",
        },
      },
      ...parentSteps(),
      {
        element: "[data-tour='target-tab']",
        popover: {
          title: text.steps.targetTab.title,
          description: text.steps.targetTab.description,
          side: "bottom",
          align: "center",
          onNextClick: moveToTarget,
        },
      },
      ...targetSteps(),
      {
        element: "[data-tour='kitten-tab']",
        popover: {
          title: text.steps.kittenTab.title,
          description: text.steps.kittenTab.description,
          side: "bottom",
          align: "center",
          onNextClick: moveToKitten,
        },
      },
      ...kittenSteps(),
      helpStep(),
    ];
  }, [helpStep, kittenSteps, parentSteps, switchToView, targetSteps, text]);

  const buildCurrentSteps = useCallback(
    (view: AppTourView): DriveStep[] => {
      if (view === "target") return [...targetSteps(), helpStep()];
      if (view === "kitten") return [...kittenSteps(), helpStep()];
      return [...parentSteps(), helpStep()];
    },
    [helpStep, kittenSteps, parentSteps, targetSteps],
  );

  const startTour = useCallback((mode: TourMode) => {
    clearStartTimer();
    tourRef.current?.destroy();
    initialViewRef.current = activeView;
    const startView = mode === "full" ? "parent" : activeView;
    const steps = mode === "full" ? buildFullSteps() : buildCurrentSteps(activeView);
    onViewChange(startView);

    startTimerRef.current = window.setTimeout(() => {
      const tour = driver({
        steps,
        animate: true,
        smoothScroll: true,
        allowClose: true,
        allowScroll: true,
        overlayClickBehavior: "close",
        overlayOpacity: 0.58,
        stagePadding: 8,
        stageRadius: 8,
        popoverClass: "ccp-driver-popover",
        showProgress: true,
        progressText: text.progress,
        nextBtnText: text.next,
        prevBtnText: text.previous,
        doneBtnText: text.done,
        onPopoverRender: (popover) => {
          popover.closeButton.textContent =
            mode === "full" ? text.skip : text.close;
          popover.closeButton.setAttribute(
            "aria-label",
            mode === "full" ? text.skipTour : text.close,
          );
          popover.closeButton.classList.add("ccp-driver-close-action");
        },
        onDestroyed: () => {
          markTourCompleted();
          onViewChange(initialViewRef.current);
          tourRef.current = null;
        },
      });

      tourRef.current = tour;
      tour.drive();
      startTimerRef.current = null;
    }, TAB_SWITCH_DELAY_MS);
  }, [
    activeView,
    buildCurrentSteps,
    buildFullSteps,
    clearStartTimer,
    onViewChange,
    text,
  ]);

  useEffect(() => {
    return () => {
      clearStartTimer();
      tourRef.current?.destroy();
    };
  }, [clearStartTimer]);

  useEffect(() => {
    if (!languageReady || autoStartedRef.current || hasCompletedTour()) {
      return;
    }

    autoStartedRef.current = true;
    const timerId = window.setTimeout(() => {
      startTour("full");
    }, AUTO_TOUR_DELAY_MS);

    return () => {
      window.clearTimeout(timerId);
    };
  }, [languageReady, startTour]);

  return (
    <button
      type="button"
      data-tour="tour-help"
      aria-label={text.helpButton}
      title={text.helpButton}
      onClick={() => startTour("current")}
      className="inline-flex h-10 items-center gap-1.5 rounded-full border border-slate-200 bg-white px-3 text-xs font-semibold text-slate-700 shadow-sm transition hover:border-emerald-200 hover:bg-emerald-50 hover:text-emerald-800 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-500"
    >
      <Question size={18} weight="duotone" aria-hidden="true" />
      <span className="hidden sm:inline">{text.helpButton}</span>
    </button>
  );
}
