"use client";

import { ChatCircleText } from "@phosphor-icons/react";
import { useCallback, useEffect, useRef, useState } from "react";
import type { PointerEvent as ReactPointerEvent } from "react";
import { submitFeedback } from "@/lib/api";
import {
  LANGUAGE_STORAGE_KEY,
  UI_TEXT,
  isLanguage,
  languageFromBrowser,
  type Language,
} from "@/lib/i18n";

const POSITION_KEY = "cbs:feedbackPosition";
const MAX_LENGTH = 200;
const DRAG_THRESHOLD = 5; // この距離を超えて動いたらドラッグと判定 (クリックと区別)
const BUTTON_SIZE = 52;

type Position = { x: number; y: number };
type SendStatus = "idle" | "sending" | "sent" | "error";

function readFeedbackLanguage(): Language {
  try {
    const stored = window.localStorage.getItem(LANGUAGE_STORAGE_KEY);
    if (isLanguage(stored)) return stored;
  } catch {
    // 言語保存が読めない場合はブラウザ言語へフォールバックする。
  }
  return languageFromBrowser(window.navigator.language);
}

function clampToViewport(pos: Position): Position {
  if (typeof window === "undefined") return pos;
  const maxX = Math.max(0, window.innerWidth - BUTTON_SIZE);
  const maxY = Math.max(0, window.innerHeight - BUTTON_SIZE);
  return {
    x: Math.min(Math.max(0, pos.x), maxX),
    y: Math.min(Math.max(0, pos.y), maxY),
  };
}

/**
 * 常駐のフィードバック手紙アイコン。
 * - ドラッグで位置を移動でき、位置は localStorage に保存される。
 * - クリック (ドラッグでない) でフィードバックモーダルを開く。
 * - 送信で /api/v1/feedback (管理者宛メール) に届く。
 */
export function FeedbackWidget() {
  const [language, setLanguage] = useState<Language>("ja");
  const [position, setPosition] = useState<Position | null>(null);
  const [open, setOpen] = useState(false);
  const [message, setMessage] = useState("");
  const [status, setStatus] = useState<SendStatus>("idle");
  const text = UI_TEXT[language].feedback;

  const positionRef = useRef<Position | null>(null);
  const dragStartRef = useRef<{ px: number; py: number; x: number; y: number } | null>(null);
  const movedRef = useRef(false);

  useEffect(() => {
    setLanguage(readFeedbackLanguage());
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
    window.addEventListener("ccp:language-change", onLanguageChange);
    window.addEventListener("storage", onStorage);
    return () => {
      window.removeEventListener("ccp:language-change", onLanguageChange);
      window.removeEventListener("storage", onStorage);
    };
  }, []);

  // 初期位置 (localStorage か既定値=右下) を復元する。
  useEffect(() => {
    let initial: Position | null = null;
    try {
      const stored = localStorage.getItem(POSITION_KEY);
      if (stored) {
        const parsed = JSON.parse(stored) as Partial<Position>;
        if (typeof parsed.x === "number" && typeof parsed.y === "number") {
          initial = { x: parsed.x, y: parsed.y };
        }
      }
    } catch {
      // ignore
    }
    if (!initial) {
      initial = {
        x: window.innerWidth - BUTTON_SIZE - 20,
        y: window.innerHeight - BUTTON_SIZE - 120,
      };
    }
    const clamped = clampToViewport(initial);
    positionRef.current = clamped;
    setPosition(clamped);
  }, []);

  // リサイズ時に画面内へ収める。
  useEffect(() => {
    const onResize = () =>
      setPosition((prev) => {
        if (!prev) return prev;
        const clamped = clampToViewport(prev);
        positionRef.current = clamped;
        return clamped;
      });
    window.addEventListener("resize", onResize);
    return () => window.removeEventListener("resize", onResize);
  }, []);

  const handlePointerDown = useCallback((e: ReactPointerEvent<HTMLButtonElement>) => {
    const pos = positionRef.current;
    if (!pos) return;
    e.currentTarget.setPointerCapture(e.pointerId);
    dragStartRef.current = { px: e.clientX, py: e.clientY, x: pos.x, y: pos.y };
    movedRef.current = false;
  }, []);

  const handlePointerMove = useCallback((e: ReactPointerEvent<HTMLButtonElement>) => {
    const start = dragStartRef.current;
    if (!start) return;
    const dx = e.clientX - start.px;
    const dy = e.clientY - start.py;
    if (!movedRef.current && Math.hypot(dx, dy) > DRAG_THRESHOLD) {
      movedRef.current = true;
    }
    if (movedRef.current) {
      const next = clampToViewport({ x: start.x + dx, y: start.y + dy });
      positionRef.current = next;
      setPosition(next);
    }
  }, []);

  const handlePointerUp = useCallback((e: ReactPointerEvent<HTMLButtonElement>) => {
    const start = dragStartRef.current;
    dragStartRef.current = null;
    if (!start) return;
    if (e.currentTarget.hasPointerCapture(e.pointerId)) {
      e.currentTarget.releasePointerCapture(e.pointerId);
    }
    if (movedRef.current) {
      try {
        if (positionRef.current) {
          localStorage.setItem(POSITION_KEY, JSON.stringify(positionRef.current));
        }
      } catch {
        // ignore
      }
    } else {
      setStatus("idle");
      setOpen(true);
    }
  }, []);

  const close = useCallback(() => {
    setStatus((current) => {
      if (current === "sending") return current; // 送信中は閉じない
      setOpen(false);
      return current;
    });
  }, []);

  const send = useCallback(async () => {
    const trimmed = message.trim();
    if (!trimmed) return;
    setStatus("sending");
    try {
      await submitFeedback(trimmed);
      setMessage("");
      setStatus("sent");
      window.setTimeout(() => setOpen(false), 1200);
    } catch {
      setStatus("error");
    }
  }, [message]);

  // Escape で閉じる。
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") close();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, close]);

  if (!position) return null;

  return (
    <>
      <button
        type="button"
        aria-label={text.trigger}
        title={text.trigger}
        onPointerDown={handlePointerDown}
        onPointerMove={handlePointerMove}
        onPointerUp={handlePointerUp}
        className="fixed z-[150] flex items-center justify-center rounded-full bg-accent text-accent-ink shadow-lg hover:bg-accent"
        style={{
          left: position.x,
          top: position.y,
          width: BUTTON_SIZE,
          height: BUTTON_SIZE,
          touchAction: "none",
          cursor: "grab",
        }}
      >
        <ChatCircleText
          aria-hidden="true"
          className="h-6 w-6"
          weight="duotone"
        />
      </button>

      {open && (
        <div
          className="fixed inset-0 z-[200] flex items-center justify-center bg-black/40 p-4"
          onClick={close}
          role="presentation"
        >
          <div
            role="dialog"
            aria-modal="true"
            aria-label={text.title}
            className="w-full max-w-md rounded-lg bg-surface p-5 shadow-xl"
            onClick={(e) => e.stopPropagation()}
          >
            <h2 className="text-base font-bold text-ink">{text.title}</h2>
            <p className="mt-1 text-sm text-ink-soft">
              {text.description}
              {MAX_LENGTH}
              {text.descriptionSuffix}
            </p>
            <textarea
              value={message}
              onChange={(e) => setMessage(e.currentTarget.value.slice(0, MAX_LENGTH))}
              maxLength={MAX_LENGTH}
              rows={4}
              autoFocus
              placeholder={text.placeholder}
              className="mt-3 w-full resize-none rounded-md border border-line bg-surface p-2 text-sm text-ink placeholder:text-muted focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent/40"
            />
            <div className="mt-1 text-right text-xs text-muted">
              {message.length} / {MAX_LENGTH}
            </div>
            {status === "error" && (
              <p className="mt-1 text-sm text-danger">
                {text.error}
              </p>
            )}
            {status === "sent" && (
              <p className="mt-1 text-sm text-accent">
                {text.sent}
              </p>
            )}
            <div className="mt-4 flex justify-end gap-2">
              <button
                type="button"
                onClick={close}
                disabled={status === "sending"}
                className="rounded-md border border-line px-3 py-1.5 text-sm text-ink-soft hover:bg-surface-2 disabled:opacity-50"
              >
                {text.cancel}
              </button>
              <button
                type="button"
                onClick={send}
                disabled={!message.trim() || status === "sending"}
                className="rounded-md bg-accent px-3 py-1.5 text-sm text-accent-ink hover:bg-accent disabled:opacity-50"
              >
                {status === "sending" ? text.sending : text.send}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
