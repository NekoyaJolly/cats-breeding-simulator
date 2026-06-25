"use client";

import { useState } from "react";
import type { CalculateInput } from "@/lib/api";

// 計算モード。explicit_carrier のときのみキャリア入力欄を表示する。
const MODES = [
  { value: "normal", label: "通常 (normal)" },
  { value: "explicit_carrier", label: "明示キャリア (explicit_carrier)" },
  { value: "carrier_exploration", label: "全キャリア探索 (carrier_exploration)" },
] as const;

type Props = {
  onSubmit: (input: CalculateInput) => void;
  loading: boolean;
};

// "C:C/cs, B:B/b" 形式のテキストを座位→遺伝子型の辞書へ変換する。
// 入力が空、または有効なペアが無い場合は undefined を返す。
function parseCarriers(text: string): Record<string, string> | undefined {
  const trimmed = text.trim();
  if (!trimmed) return undefined;
  const entries: Record<string, string> = {};
  for (const part of trimmed.split(",")) {
    const [locus, genotype] = part.split(":").map((token) => token.trim());
    if (locus && genotype) entries[locus] = genotype;
  }
  return Object.keys(entries).length > 0 ? entries : undefined;
}

const inputClass =
  "w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm shadow-sm focus:border-slate-500 focus:outline-none focus:ring-1 focus:ring-slate-500";
const labelClass = "block text-sm font-medium text-slate-700";

export function BreedingForm({ onSubmit, loading }: Props) {
  const [sireColor, setSireColor] = useState("");
  const [damColor, setDamColor] = useState("");
  const [breed, setBreed] = useState("");
  const [mode, setMode] = useState<string>("normal");
  const [sireCarriers, setSireCarriers] = useState("");
  const [damCarriers, setDamCarriers] = useState("");

  // 親色は必須。breed は任意。
  const canSubmit =
    sireColor.trim().length > 0 && damColor.trim().length > 0 && !loading;

  function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!canSubmit) return;
    const input: CalculateInput = {
      sire_color: sireColor.trim(),
      dam_color: damColor.trim(),
      mode,
    };
    const trimmedBreed = breed.trim();
    if (trimmedBreed) input.breed = trimmedBreed;
    // キャリアは明示キャリアモードのときのみ送る。
    if (mode === "explicit_carrier") {
      input.sire_carriers = parseCarriers(sireCarriers);
      input.dam_carriers = parseCarriers(damCarriers);
    }
    onSubmit(input);
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div className="space-y-1">
          <label htmlFor="sire-color" className={labelClass}>
            父猫の毛色 <span className="text-red-500">*</span>
          </label>
          <input
            id="sire-color"
            className={inputClass}
            value={sireColor}
            onChange={(event) => setSireColor(event.target.value)}
            placeholder="例: Silver Tabby"
            autoComplete="off"
          />
        </div>
        <div className="space-y-1">
          <label htmlFor="dam-color" className={labelClass}>
            母猫の毛色 <span className="text-red-500">*</span>
          </label>
          <input
            id="dam-color"
            className={inputClass}
            value={damColor}
            onChange={(event) => setDamColor(event.target.value)}
            placeholder="例: Brown Tabby"
            autoComplete="off"
          />
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div className="space-y-1">
          <label htmlFor="breed" className={labelClass}>
            猫種 (任意)
          </label>
          <input
            id="breed"
            className={inputClass}
            value={breed}
            onChange={(event) => setBreed(event.target.value)}
            placeholder="例: Abyssinian"
            autoComplete="off"
          />
        </div>
        <div className="space-y-1">
          <label htmlFor="mode" className={labelClass}>
            計算モード
          </label>
          <select
            id="mode"
            className={inputClass}
            value={mode}
            onChange={(event) => setMode(event.target.value)}
          >
            {MODES.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      {mode === "explicit_carrier" && (
        <div className="grid grid-cols-1 gap-4 rounded-md bg-slate-100 p-4 sm:grid-cols-2">
          <p className="sm:col-span-2 text-xs text-slate-500">
            隠れキャリアを「座位:遺伝子型」のカンマ区切りで指定 (例:{" "}
            <code className="rounded bg-white px-1">C:C/cs, B:B/b</code>)。
          </p>
          <div className="space-y-1">
            <label htmlFor="sire-carriers" className={labelClass}>
              父猫のキャリア
            </label>
            <input
              id="sire-carriers"
              className={inputClass}
              value={sireCarriers}
              onChange={(event) => setSireCarriers(event.target.value)}
              placeholder="C:C/cs"
              autoComplete="off"
            />
          </div>
          <div className="space-y-1">
            <label htmlFor="dam-carriers" className={labelClass}>
              母猫のキャリア
            </label>
            <input
              id="dam-carriers"
              className={inputClass}
              value={damCarriers}
              onChange={(event) => setDamCarriers(event.target.value)}
              placeholder="B:B/b"
              autoComplete="off"
            />
          </div>
        </div>
      )}

      <button
        type="submit"
        disabled={!canSubmit}
        className="w-full rounded-md bg-slate-800 px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-50 sm:w-auto"
      >
        {loading ? "計算中…" : "子猫の毛色を計算"}
      </button>
    </form>
  );
}
