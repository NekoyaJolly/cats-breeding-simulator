"use client";

import { useEffect, useId, useRef, useState } from "react";
import { LOCUS_GLOSSARY, getLocusTone } from "@/lib/lociGlossary";

// 診断情報の座位記号 (A / D / Mc …) を、タップ/ホバーで解説ポップオーバーが出る
// チップにする。普段は1文字だけで邪魔にならず、気になったらその場で読める。
export function LocusChip({ locus }: { locus: string }) {
  const entry = LOCUS_GLOSSARY[locus];
  const tone = getLocusTone(locus);
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
    return <span className="tabular-nums text-ink-soft">{locus}</span>;
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
        className={`cursor-help rounded border border-dashed px-1 leading-tight decoration-dotted ${tone.chipClass}`}
        aria-expanded={open}
        // describedby は常時付与 (フォーカス瞬間に関連付けが無いと読み上げを取りこぼすため)。
        aria-describedby={tooltipId}
        aria-label={`${entry.symbol} ${entry.name} の解説`}
      >
        {locus}
      </button>
      {/* tooltip は常に DOM に置き aria-describedby を常時有効化。表示だけ open で切替。 */}
      <span
        role="tooltip"
        id={tooltipId}
        className={`absolute left-0 top-full z-20 mt-1 w-56 max-w-[80vw] rounded-md border border-line bg-surface p-2 text-left text-xs font-normal text-ink-soft shadow-lg ${
          open ? "block" : "hidden"
        }`}
      >
        <span className="block font-semibold text-ink">
          {entry.symbol} — {entry.name}
        </span>
        <span className="mt-0.5 block text-[11px] text-muted">
          {entry.inheritance}
        </span>
        {entry.layers ? (
          <span className="mt-1 block space-y-1">
            {entry.layers.map((layer) => (
              <span key={layer.label} className="block leading-relaxed">
                <span className="block text-[11px] font-semibold text-muted">
                  {layer.label}
                </span>
                <span className="block">{layer.text}</span>
              </span>
            ))}
          </span>
        ) : (
          <span className="mt-0.5 block leading-relaxed">
            {entry.description}
          </span>
        )}
      </span>
    </span>
  );
}
