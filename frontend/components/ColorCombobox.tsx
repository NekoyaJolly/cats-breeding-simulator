"use client";

import {
  useEffect,
  useId,
  useMemo,
  useRef,
  useState,
  type KeyboardEvent,
  type ReactNode,
} from "react";
import type { ColorOption } from "@/lib/schema";
import { filterColors } from "@/lib/colorMatch";

type Props = {
  id: string;
  label: string;
  labelAction?: ReactNode;
  required?: boolean;
  value: string;
  onValueChange: (value: string) => void;
  // 候補から確定した (または自由入力を Enter 確定した) ときに履歴へ積むためのコールバック。
  onCommit: (value: string) => void;
  colors: ColorOption[];
  // 履歴 (最近選んだ canonical 名)。query が空のとき優先表示する。
  recent: string[];
  placeholder?: string;
  recentLabel?: string;
  femaleOnlyLabel?: string;
  // 登録フォームでは候補が下の操作ボタンを覆わないよう、行内表示を選べる。
  suggestionLayout?: "overlay" | "inline";
};

const MAX_SUGGESTIONS = 20;

const inputClass =
  "h-11 w-full rounded-md border border-slate-300 bg-white py-2 text-base leading-6 shadow-sm transition focus:border-slate-500 focus:outline-none focus:ring-1 focus:ring-slate-500 sm:text-sm sm:leading-5";
const floatingLabelBaseClass =
  "absolute left-3 z-[1] truncate bg-white px-1 transition-all duration-150";
const floatingLabelClass =
  "top-0 -translate-y-1/2 text-[11px] leading-4 text-slate-600";
const restingLabelClass =
  "top-1/2 -translate-y-1/2 text-sm leading-5 text-slate-500";

// 履歴の文字列を ColorOption へ解決する。一覧に無い自由入力履歴は最小エントリで合成する。
function resolveRecent(recent: string[], byValue: Map<string, ColorOption>): ColorOption[] {
  return recent.map(
    (value) =>
      byValue.get(value) ?? {
        value,
        reading_ja: "",
        status: "",
        breed_context: "",
        sex_restriction: "",
        keywords: [],
      },
  );
}

export function ColorCombobox({
  id,
  label,
  labelAction,
  required = false,
  value,
  onValueChange,
  onCommit,
  colors,
  recent,
  placeholder,
  recentLabel = "最近の選択",
  femaleOnlyLabel = "♀ 限定",
  suggestionLayout = "overlay",
}: Props) {
  const [open, setOpen] = useState(false);
  const [focused, setFocused] = useState(false);
  const [activeIndex, setActiveIndex] = useState(-1);
  const containerRef = useRef<HTMLDivElement>(null);
  const listboxId = useId();

  const byValue = useMemo(() => {
    const map = new Map<string, ColorOption>();
    for (const color of colors) map.set(color.value, color);
    return map;
  }, [colors]);

  // query が空なら履歴、入力があれば絞り込み結果を出す。
  const suggestions = useMemo<ColorOption[]>(() => {
    if (value.trim().length === 0) return resolveRecent(recent, byValue);
    return filterColors(colors, value, MAX_SUGGESTIONS);
  }, [value, recent, byValue, colors]);

  const showingRecent = value.trim().length === 0;

  // 外側クリックで閉じる。click で閉じることで、行内候補表示時に mousedown で
  // レイアウトが縮み、フォームボタンの click が外れるのを避ける。
  useEffect(() => {
    function onDocumentClick(event: MouseEvent) {
      if (!containerRef.current?.contains(event.target as Node)) {
        setOpen(false);
        setActiveIndex(-1);
      }
    }
    document.addEventListener("click", onDocumentClick);
    return () => document.removeEventListener("click", onDocumentClick);
  }, []);

  function commitSelection(color: ColorOption) {
    onValueChange(color.value);
    onCommit(color.value);
    setOpen(false);
    setActiveIndex(-1);
  }

  function handleKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (event.key === "ArrowDown") {
      event.preventDefault();
      if (!open) {
        // 開くタイミングではハイライトを持ち越さない。
        setOpen(true);
        setActiveIndex(-1);
        return;
      }
      if (suggestions.length === 0) return;
      setActiveIndex((prev) => Math.min(prev + 1, suggestions.length - 1));
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      // 候補が無いときは -1 を維持し、不正な aria-activedescendant を作らない。
      if (suggestions.length === 0) return;
      setActiveIndex((prev) => (prev <= 0 ? 0 : prev - 1));
    } else if (event.key === "Enter") {
      if (open && activeIndex >= 0 && activeIndex < suggestions.length) {
        event.preventDefault();
        commitSelection(suggestions[activeIndex]);
      } else {
        const trimmed = value.trim();
        if (trimmed.length > 0) {
          // 自由入力を確定: 表示値・履歴・ARIA 状態を揃える (送信はフォーム側)。
          onValueChange(trimmed);
          onCommit(trimmed);
          setOpen(false);
          setActiveIndex(-1);
        }
      }
    } else if (event.key === "Escape") {
      setOpen(false);
      setActiveIndex(-1);
    }
  }

  const expanded = open && suggestions.length > 0;
  const floated = focused || value.trim().length > 0 || Boolean(placeholder);
  const labelWidthClass = labelAction
    ? "max-w-[calc(100%-4.5rem)]"
    : "max-w-[calc(100%-1.5rem)]";
  const inputPaddingClass = labelAction ? "pl-3 pr-12" : "px-3";
  const listboxClass =
    suggestionLayout === "inline"
      ? "mt-1 max-h-64 w-full overflow-auto rounded-md border border-slate-200 bg-white py-1 text-sm shadow-lg"
      : "absolute z-40 mt-1 max-h-64 w-full overflow-auto rounded-md border border-slate-200 bg-white py-1 text-sm shadow-lg";

  return (
    <div className="relative" ref={containerRef}>
      <div className="relative">
        <input
          id={id}
          className={`${inputClass} ${inputPaddingClass}`}
          value={value}
          onChange={(event) => {
            onValueChange(event.target.value);
            setOpen(true);
            setActiveIndex(-1);
          }}
          onFocus={() => {
            setFocused(true);
            setOpen(true);
            setActiveIndex(-1);
          }}
          onBlur={() => {
            setFocused(false);
            setOpen(false);
            setActiveIndex(-1);
          }}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          autoComplete="off"
          role="combobox"
          aria-expanded={expanded}
          // listbox は expanded のときだけ DOM に存在するため、その間だけ参照する。
          aria-controls={expanded ? listboxId : undefined}
          aria-autocomplete="list"
          aria-activedescendant={
            expanded && activeIndex >= 0
              ? `${listboxId}-opt-${activeIndex}`
              : undefined
          }
        />
        <label
          htmlFor={id}
          className={`${floatingLabelBaseClass} ${labelWidthClass} ${
            floated ? floatingLabelClass : restingLabelClass
          }`}
        >
          {label}
          {required && <span className="text-red-500"> *</span>}
        </label>
        {labelAction && (
          <div className="absolute right-2 top-1/2 -translate-y-1/2">
            {labelAction}
          </div>
        )}
        {expanded && (
          <ul
            id={listboxId}
            role="listbox"
            className={listboxClass}
          >
            {showingRecent && (
              <li className="px-3 py-1 text-xs font-medium text-slate-400">
                {recentLabel}
              </li>
            )}
            {suggestions.map((color, index) => {
              const active = index === activeIndex;
              return (
                <li
                  key={`${color.value}-${index}`}
                  id={`${listboxId}-opt-${index}`}
                  role="option"
                  aria-selected={active}
                  className={`flex cursor-pointer items-center justify-between gap-2 px-3 py-1.5 ${
                    active ? "bg-slate-100" : "hover:bg-slate-50"
                  }`}
                  // input の blur で閉じる前に選択を確定させるため mousedown を使う。
                  onMouseDown={(event) => {
                    event.preventDefault();
                    commitSelection(color);
                  }}
                  onMouseEnter={() => setActiveIndex(index)}
                >
                  <span className="min-w-0">
                    <span className="text-slate-800">{color.value}</span>
                    {color.reading_ja && (
                      <span className="ml-2 text-xs text-slate-400">
                        {color.reading_ja}
                      </span>
                    )}
                  </span>
                  <span className="flex shrink-0 items-center gap-1">
                    {color.sex_restriction === "female_only" && (
                      <span className="rounded bg-pink-50 px-1.5 py-0.5 text-[10px] font-medium leading-4 text-pink-600">
                        {femaleOnlyLabel}
                      </span>
                    )}
                    {color.breed_context && (
                      <span className="rounded bg-slate-100 px-1.5 py-0.5 text-[10px] leading-4 text-slate-500">
                        {color.breed_context}
                      </span>
                    )}
                  </span>
                </li>
              );
            })}
          </ul>
        )}
      </div>
    </div>
  );
}
