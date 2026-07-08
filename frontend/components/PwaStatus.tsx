"use client";

import { ArrowClockwise, DownloadSimple, WifiSlash, X } from "@phosphor-icons/react";
import { useEffect, useMemo, useRef, useState } from "react";
import {
  LANGUAGE_STORAGE_KEY,
  isLanguage,
  languageFromBrowser,
  type Language,
} from "@/lib/i18n";

type BeforeInstallPromptChoice = {
  outcome: "accepted" | "dismissed";
  platform: string;
};

type BeforeInstallPromptEvent = Event & {
  prompt: () => Promise<void>;
  userChoice: Promise<BeforeInstallPromptChoice>;
};

type PwaNotice = "offline" | "update" | "install" | null;

const pwaText = {
  ja: {
    offlineTitle: "オフラインです",
    offlineBody: "保存済みデータは確認できます。計算には接続が必要です。",
    updateTitle: "新しいバージョンがあります",
    updateBody: "更新すると最新の画面に切り替わります。",
    updateAction: "更新する",
    installTitle: "ホーム画面に追加できます",
    installBody: "スマホからすぐ開けるようになります。",
    installAction: "追加する",
    close: "閉じる",
  },
  en: {
    offlineTitle: "Offline",
    offlineBody: "Saved data stays available. Calculations need a connection.",
    updateTitle: "Update available",
    updateBody: "Refresh to switch to the latest version.",
    updateAction: "Update",
    installTitle: "Add to Home Screen",
    installBody: "Open the planner quickly from your device.",
    installAction: "Add",
    close: "Close",
  },
} as const satisfies Record<Language, Record<string, string>>;

function readLanguage(): Language {
  try {
    const stored = window.localStorage.getItem(LANGUAGE_STORAGE_KEY);
    if (isLanguage(stored)) return stored;
  } catch {
    // 言語保存が読めない場合はブラウザ言語へフォールバックする。
  }
  return languageFromBrowser(window.navigator.language);
}

function isStandaloneDisplay(): boolean {
  const navigatorWithStandalone = window.navigator as Navigator & { standalone?: boolean };
  return (
    window.matchMedia("(display-mode: standalone)").matches ||
    navigatorWithStandalone.standalone === true
  );
}

function isBeforeInstallPromptEvent(event: Event): event is BeforeInstallPromptEvent {
  const candidate = event as Event & {
    prompt?: () => Promise<void>;
    userChoice?: Promise<BeforeInstallPromptChoice>;
  };
  return typeof candidate.prompt === "function" && candidate.userChoice instanceof Promise;
}

export function PwaStatus() {
  const [language, setLanguage] = useState<Language>("ja");
  const [offline, setOffline] = useState(false);
  const [installPrompt, setInstallPrompt] = useState<BeforeInstallPromptEvent | null>(null);
  const [installDismissed, setInstallDismissed] = useState(false);
  const [updateReady, setUpdateReady] = useState(false);
  const [updateDismissed, setUpdateDismissed] = useState(false);
  const [waitingWorker, setWaitingWorker] = useState<ServiceWorker | null>(null);
  const reloadingRef = useRef(false);

  useEffect(() => {
    setLanguage(readLanguage());
    setOffline(!window.navigator.onLine);

    const onLanguageChange = (event: Event) => {
      if (event instanceof CustomEvent) {
        const nextLanguage = String(event.detail);
        if (isLanguage(nextLanguage)) setLanguage(nextLanguage);
      }
    };
    const onStorage = (event: StorageEvent) => {
      if (event.key !== LANGUAGE_STORAGE_KEY) return;
      setLanguage(
        isLanguage(event.newValue)
          ? event.newValue
          : languageFromBrowser(window.navigator.language),
      );
    };
    const onOnline = () => setOffline(false);
    const onOffline = () => setOffline(true);

    window.addEventListener("ccp:language-change", onLanguageChange);
    window.addEventListener("storage", onStorage);
    window.addEventListener("online", onOnline);
    window.addEventListener("offline", onOffline);
    return () => {
      window.removeEventListener("ccp:language-change", onLanguageChange);
      window.removeEventListener("storage", onStorage);
      window.removeEventListener("online", onOnline);
      window.removeEventListener("offline", onOffline);
    };
  }, []);

  useEffect(() => {
    const onBeforeInstallPrompt = (event: Event) => {
      if (!isBeforeInstallPromptEvent(event) || isStandaloneDisplay()) return;
      event.preventDefault();
      setInstallPrompt(event);
      setInstallDismissed(false);
    };
    window.addEventListener("beforeinstallprompt", onBeforeInstallPrompt);
    return () => window.removeEventListener("beforeinstallprompt", onBeforeInstallPrompt);
  }, []);

  useEffect(() => {
    if (process.env.NODE_ENV !== "production") return;
    if (!("serviceWorker" in navigator)) return;

    let cancelled = false;
    navigator.serviceWorker
      .register("/sw.js")
      .then((registration) => {
        if (cancelled) return;
        if (registration.waiting) {
          setWaitingWorker(registration.waiting);
          setUpdateReady(true);
        }
        registration.addEventListener("updatefound", () => {
          const installingWorker = registration.installing;
          if (!installingWorker) return;
          installingWorker.addEventListener("statechange", () => {
            if (
              installingWorker.state === "installed" &&
              navigator.serviceWorker.controller
            ) {
              setWaitingWorker(installingWorker);
              setUpdateReady(true);
              setUpdateDismissed(false);
            }
          });
        });
      })
      .catch(() => {
        // Service Workerが登録できない環境でも、通常のWebアプリとして利用を継続する。
      });

    const onControllerChange = () => {
      if (reloadingRef.current) return;
      reloadingRef.current = true;
      window.location.reload();
    };
    navigator.serviceWorker.addEventListener("controllerchange", onControllerChange);
    return () => {
      cancelled = true;
      navigator.serviceWorker.removeEventListener("controllerchange", onControllerChange);
    };
  }, []);

  const notice = useMemo<PwaNotice>(() => {
    if (offline) return "offline";
    if (updateReady && !updateDismissed) return "update";
    if (installPrompt && !installDismissed) return "install";
    return null;
  }, [installDismissed, installPrompt, offline, updateDismissed, updateReady]);

  if (!notice) return null;

  const text = pwaText[language];
  const isUpdate = notice === "update";
  const isInstall = notice === "install";
  const title = notice === "offline"
    ? text.offlineTitle
    : isUpdate
      ? text.updateTitle
      : text.installTitle;
  const body = notice === "offline"
    ? text.offlineBody
    : isUpdate
      ? text.updateBody
      : text.installBody;
  const Icon = notice === "offline" ? WifiSlash : isUpdate ? ArrowClockwise : DownloadSimple;

  async function handleInstall() {
    if (!installPrompt) return;
    await installPrompt.prompt();
    const choice = await installPrompt.userChoice;
    if (choice.outcome === "accepted" || choice.outcome === "dismissed") {
      setInstallPrompt(null);
    }
  }

  function handleUpdate() {
    waitingWorker?.postMessage({ type: "SKIP_WAITING" });
  }

  function close() {
    if (isUpdate) setUpdateDismissed(true);
    if (isInstall) setInstallDismissed(true);
  }

  return (
    <aside className="fixed inset-x-3 bottom-3 z-[140] mx-auto max-w-md rounded-lg border border-line bg-surface/95 p-3 text-sm shadow-lg backdrop-blur">
      <div className="flex items-start gap-3">
        <div className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-surface-2 text-ink-soft">
          <Icon aria-hidden="true" className="h-4 w-4" weight="duotone" />
        </div>
        <div className="min-w-0 flex-1">
          <p className="font-semibold text-ink">{title}</p>
          <p className="mt-0.5 text-xs leading-5 text-ink-soft">{body}</p>
          {(isUpdate || isInstall) && (
            <button
              type="button"
              className="mt-2 rounded-md bg-accent px-3 py-1.5 text-xs font-semibold text-accent-ink shadow-sm hover:bg-accent/90"
              onClick={isUpdate ? handleUpdate : handleInstall}
            >
              {isUpdate ? text.updateAction : text.installAction}
            </button>
          )}
        </div>
        {!offline && (
          <button
            type="button"
            aria-label={text.close}
            title={text.close}
            className="rounded-full p-1 text-muted hover:bg-surface-2 hover:text-ink-soft"
            onClick={close}
          >
            <X aria-hidden="true" className="h-4 w-4" />
          </button>
        )}
      </div>
    </aside>
  );
}
