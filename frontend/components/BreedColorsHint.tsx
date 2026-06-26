"use client";

import { useEffect, useState } from "react";
import { fetchBreedColors } from "@/lib/api";

// 猫種ミスマッチのエラー文の後ろに「その猫種で使える毛色」をコピペ可能な形で出す。
// 各色チップはクリックでクリップボードへコピー。制約なし猫種 / 取得失敗時は何も描画しない。
export function BreedColorsHint({ breed }: { breed: string }) {
  const [colors, setColors] = useState<string[] | null>(null);
  const [copied, setCopied] = useState<string | null>(null);

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

  if (!colors || colors.length === 0) return null;

  async function copy(text: string, label: string) {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(label);
      window.setTimeout(
        () => setCopied((current) => (current === label ? null : current)),
        1200,
      );
    } catch {
      // クリップボード非対応 / 権限なしは黙って無視する。
    }
  }

  return (
    <div className="mt-3 rounded-md border border-slate-200 bg-white p-3 text-slate-700">
      <div className="mb-2 flex items-center justify-between gap-2">
        <span className="text-xs font-semibold">
          「{breed}」で使える毛色（クリックでコピー）
        </span>
        <button
          type="button"
          onClick={() => copy(colors.join("\n"), "__all__")}
          className="shrink-0 text-xs text-blue-600 hover:underline"
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
            className="rounded border border-slate-300 bg-slate-50 px-2 py-1 text-xs hover:bg-slate-100"
            title="クリックでコピー"
          >
            {copied === color ? "✓ コピー" : color}
          </button>
        ))}
      </div>
    </div>
  );
}
