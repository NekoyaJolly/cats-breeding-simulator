"use client";

import { useState } from "react";
import { BreedingForm } from "@/components/BreedingForm";
import { BreedColorsHint } from "@/components/BreedColorsHint";
import { ResultView } from "@/components/ResultView";
import { TargetColorSearch } from "@/components/TargetColorSearch";
import { calculate, type CalculateInput } from "@/lib/api";
import type { CalculationResponse } from "@/lib/schema";

type ActiveView = "simulator" | "target";

export default function HomePage() {
  const [activeView, setActiveView] = useState<ActiveView>("simulator");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<CalculationResponse | null>(null);
  // 直近の送信で指定された猫種 (認定カラー案内ポップアップの対象)。
  const [submittedBreed, setSubmittedBreed] = useState<string | null>(null);

  async function handleSubmit(input: CalculateInput) {
    setLoading(true);
    setError(null);
    setSubmittedBreed(input.breed ?? null);
    const outcome = await calculate(input);
    if (outcome.ok) {
      setResult(outcome.data);
    } else {
      setResult(null);
      setError(outcome.message);
    }
    setLoading(false);
  }

  return (
    <main className="mx-auto max-w-3xl px-4 py-10">
      <header className="mb-8">
        <h1 className="text-2xl font-bold">猫毛色シミュレーター</h1>
        <p className="mt-1 text-sm text-slate-600">
          父猫・母猫の毛色から、子猫の毛色出現確率を計算します。
        </p>
      </header>

      <div className="mb-6 flex gap-2 rounded-md bg-slate-100 p-1">
        <button
          type="button"
          className={`flex-1 rounded px-3 py-2 text-sm font-medium ${
            activeView === "simulator"
              ? "bg-white text-slate-900 shadow-sm"
              : "text-slate-500 hover:text-slate-800"
          }`}
          onClick={() => setActiveView("simulator")}
        >
          通常シミュレーター
        </button>
        <button
          type="button"
          className={`flex-1 rounded px-3 py-2 text-sm font-medium ${
            activeView === "target"
              ? "bg-white text-slate-900 shadow-sm"
              : "text-slate-500 hover:text-slate-800"
          }`}
          onClick={() => setActiveView("target")}
        >
          目標カラーから探す
        </button>
      </div>

      {activeView === "simulator" ? (
        <>
          <div className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
            <BreedingForm onSubmit={handleSubmit} loading={loading} />
          </div>

          {error && (
            <div className="mt-6 rounded-md border border-red-200 bg-red-50 p-4 text-sm text-red-700">
              {error}
              {/* 猫種の認定カラーに無い旨のエラーなら、使える毛色をコピペ可能に案内する。 */}
              {submittedBreed && error.includes("認定カラー") && (
                <BreedColorsHint breed={submittedBreed} />
              )}
            </div>
          )}

          {result && (
            <div className="mt-6 rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
              <ResultView data={result} />
            </div>
          )}
        </>
      ) : (
        <TargetColorSearch />
      )}
    </main>
  );
}
