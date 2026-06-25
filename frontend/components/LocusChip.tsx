"use client";

import { useEffect, useId, useRef, useState } from "react";
import { LOCUS_GLOSSARY } from "@/lib/lociGlossary";

// 診断情報の座位記号 (A / D / Mc …) を、タップ/ホバーで解説ポップオーバーが出る
// チップにする。普段は1文字だけで邪魔にならず、気になったらその場で読める。
export function LocusChip({ locus }: { locus: string }) {
  const entry = LOCUS_GLOSSARY[locus];
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLSpanElement>(null);
  const tooltipId = useId();

  // 開いている間だけ外側クリック / Escape で閉じる (モバイルのタップ運用)。
  useEffect(() => {
    if (!open) return;
    function onPointerDown(event: MouseEvent) {
      if (!containerRef.current?.contains(event.target as Node)) setOpen(false);
    }
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") setOpen(false);
    }
    document.addEventListener("mousedown", onPointerDown);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("mousedown", onPointerDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [open]);

  // 解説が未登録の座位はプレーンなテキストで出す (解説なし)。
  if (!entry) {
    return <span className="tabular-nums text-slate-600">{locus}</span>;
  }

  return (
    <span
      ref={containerRef}
      className="relative inline-block"
      onMouseEnter={() => setOpen(true)}
      onMouseLeave={() => setOpen(false)}
    >
      <button
        type="button"
        // click は「開く」に統一する (focus も開くため toggle だと tap で開→閉と打ち消し合う)。
        // 閉じるのは外側クリック / Escape / blur / マウスアウトに任せる。
        onClick={() => setOpen(true)}
        onFocus={() => setOpen(true)}
        onBlur={() => setOpen(false)}
        className="cursor-help rounded border border-dashed border-slate-300 px-1 leading-tight text-slate-600 decoration-dotted hover:bg-slate-100"
        aria-expanded={open}
        aria-describedby={open ? tooltipId : undefined}
        aria-label={`${entry.symbol} ${entry.name} の解説`}
      >
        {locus}
      </button>
      {open && (
        <span
          role="tooltip"
          id={tooltipId}
          className="absolute left-0 top-full z-20 mt-1 block w-56 max-w-[80vw] rounded-md border border-slate-200 bg-white p-2 text-left text-xs font-normal text-slate-600 shadow-lg"
        >
          <span className="block font-semibold text-slate-800">
            {entry.symbol} — {entry.name}
          </span>
          <span className="mt-0.5 block leading-relaxed">
            {entry.description}
          </span>
        </span>
      )}
    </span>
  );
}
