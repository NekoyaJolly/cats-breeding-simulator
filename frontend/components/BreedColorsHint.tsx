"use client";

import { useEffect, useRef, useState } from "react";
import { fetchBreedColors } from "@/lib/api";

// 猫種ミスマッチのエラー文の後ろに「その猫種で使える毛色」をコピペ可能な形で出す。
// 各色チップはクリックでクリップボードへコピー。制約なし猫種 / 取得失敗時は何も描画しない。
export function BreedColorsHint({ breed }: { breed: string }) {
  const [colors, setColors] = useState<string[] | null>(null);
  const [copied, setCopied] = useState<string | null>(null);
  // 「✓ コピー」表示を戻すタイマー。連打で多重化しないよう 1 本に保持し、
  // 次回コピー時とアンマウント時に必ず解除する。
  const resetTimerRef = useRef<number | null>(null);

  useEffect(() => {
    let active = true;
    setColors(null);
    fetchBreedColors(breed).then((list) => {
      if (active) setColors(list);
    });
    return () => {
      active = false;
    };
  }, [breed]);

  useEffect(() => {
    // アンマウント時にタイマーを解除 (解除漏れで setState が走るのを防ぐ)。
    return () => {
      if (resetTimerRef.current !== null) {
        window.clearTimeout(resetTimerRef.current);
      }
    };
  }, []);

  if (!colors || colors.length === 0) return null;

  async function copy(text: string, label: string) {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(label);
      if (resetTimerRef.current !== null) {
        window.clearTimeout(resetTimerRef.current);
      }
      resetTimerRef.current = window.setTimeout(() => {
        setCopied((current) => (current === label ? null : current));
        resetTimerRef.current = null;
      }, 1200);
    } catch {
      // クリップボード非対応 / 権限なしは黙って無視する。
    }
  }

  return (
    <div className="mt-3 rounded-md border border-line bg-surface p-3 text-ink-soft">
      <div className="mb-2 flex items-center justify-between gap-2">
        <span className="text-xs font-semibold">
          「{breed}」で使える毛色（クリックでコピー）
        </span>
        <button
          type="button"
          onClick={() => copy(colors.join("\n"), "__all__")}
          className="shrink-0 text-xs text-accent hover:underline"
        >
          {copied === "__all__" ? "✓ コピーしました" : "一覧をコピー"}
        </button>
      </div>
      <div className="flex flex-wrap gap-1.5">
        {colors.map((color) => (
          <button
            key={color}
            type="button"
            onClick={() => copy(color, color)}
            className="rounded border border-line bg-bg px-2 py-1 text-xs hover:bg-surface-2"
            title="クリックでコピー"
          >
            {copied === color ? "✓ コピー" : color}
          </button>
        ))}
      </div>
    </div>
  );
}
