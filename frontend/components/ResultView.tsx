"use client";

import { useState } from "react";
import type {
  CalculationResponse,
  CarrierScenarioEntry,
  ResultEntry,
} from "@/lib/schema";
import { LocusChip } from "./LocusChip";

// 確率を小数1桁の % 文字列に整形する (診断値など正確さ優先の箇所で使う)。
function formatPct(value: number): string {
  return `${value.toFixed(1)}%`;
}

// 確率を整数 % に丸める (結果表示用)。0 超で四捨五入が 0 になる微小値は "<1%"。
function formatPctInt(value: number): string {
  if (value <= 0) return "0%";
  const rounded = Math.round(value);
  return rounded === 0 ? "<1%" : `${rounded}%`;
}

// 各性別グループで常時表示する上位件数 (ベース色グループ単位)。残りは「詳細を見る」。
const TOP_N = 5;

// 白斑サフィックス。長い順に判定する ("-White Van" を "-White" より先に)。
const WHITE_SUFFIXES = ["-White Van", "-White"] as const;

type WhitePortion = { label: string; pct: number };
type ColorGroup = { base: string; total: number; whites: WhitePortion[] };

// 色名から白斑サフィックスを剥がし、ベース色と白斑ラベルに分ける。
// 例: "Silver Patched Tabby-White" -> { base: "Silver Patched Tabby", whiteLabel: "-White" }
function splitWhite(color: string): { base: string; whiteLabel: string | null } {
  for (const suffix of WHITE_SUFFIXES) {
    if (color.endsWith(suffix)) {
      return { base: color.slice(0, color.length - suffix.length), whiteLabel: suffix };
    }
  }
  return { base: color, whiteLabel: null };
}

// 結果をベース色でまとめる。白斑あり (-White / -White Van) は副次内訳として保持する。
// グループは合計確率の降順、白斑内訳も確率降順で並べる。
function groupByBase(rows: ResultEntry[]): ColorGroup[] {
  const map = new Map<string, ColorGroup>();
  for (const row of rows) {
    const { base, whiteLabel } = splitWhite(row.color);
    const group = map.get(base) ?? { base, total: 0, whites: [] };
    group.total += row.probability_pct;
    if (whiteLabel) {
      group.whites.push({ label: whiteLabel, pct: row.probability_pct });
    }
    map.set(base, group);
  }
  const groups = [...map.values()];
  for (const group of groups) {
    group.whites.sort((a, b) => b.pct - a.pct);
  }
  groups.sort((a, b) => b.total - a.total || a.base.localeCompare(b.base));
  return groups;
}

// 1 性別ぶんの結果カード。ベース色でまとめた上位 TOP_N グループを常に見せ、
// 残りは「詳細を見る (残り N 件)」で展開 / 「閉じる」で折りたたむ (性別ごとに独立)。
function SexResultGroup({
  title,
  accentClass,
  rows,
}: {
  title: string;
  accentClass: string;
  rows: ResultEntry[];
}) {
  const [expanded, setExpanded] = useState(false);
  const groups = groupByBase(rows);
  const total = rows.reduce((sum, row) => sum + row.probability_pct, 0);
  const visible = expanded ? groups : groups.slice(0, TOP_N);
  const hiddenCount = groups.length - visible.length;

  return (
    <div className="overflow-hidden rounded-md border border-slate-200">
      <div
        className={`flex items-baseline justify-between px-4 py-2 ${accentClass}`}
      >
        <h3 className="text-sm font-semibold">{title}</h3>
        {/* 各行は整数丸めのため合計が厳密一致しない。概算であることを「約」で明示する。 */}
        <span className="text-xs tabular-nums opacity-80">
          合計 約{formatPctInt(total)}
        </span>
      </div>
      {groups.length === 0 ? (
        <p className="px-4 py-3 text-sm text-slate-500">
          該当する表現型がありません。
        </p>
      ) : (
        <>
          <ul className="divide-y divide-slate-100">
            {visible.map((group) => (
              <li key={group.base} className="px-4 py-1.5">
                <div className="flex items-center justify-between gap-2 text-sm">
                  <span className="min-w-0 break-words text-slate-700">
                    {group.base}
                  </span>
                  <span className="shrink-0 tabular-nums text-slate-600">
                    {formatPctInt(group.total)}
                  </span>
                </div>
                {group.whites.map((white) => (
                  <div
                    key={white.label}
                    className="flex items-center justify-between gap-2 pl-3 text-xs text-slate-400"
                  >
                    <span>└ {white.label}</span>
                    <span className="shrink-0 tabular-nums">
                      {formatPctInt(white.pct)}
                    </span>
                  </div>
                ))}
              </li>
            ))}
          </ul>
          {groups.length > TOP_N && (
            <button
              type="button"
              onClick={() => setExpanded((value) => !value)}
              className="w-full border-t border-slate-100 px-4 py-2 text-xs font-medium text-slate-500 hover:bg-slate-50"
              aria-expanded={expanded}
            >
              {expanded ? "閉じる" : `詳細を見る (残り ${hiddenCount} 件)`}
            </button>
          )}
        </>
      )}
    </div>
  );
}

// 結果を ♀ / ♂ に分割して表示する。デスクトップは横並び、モバイルは縦積み。
function SexSplitResults({ rows }: { rows: ResultEntry[] }) {
  const female = rows.filter((row) => row.sex === "Female");
  const male = rows.filter((row) => row.sex === "Male");
  return (
    <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
      <SexResultGroup
        title="♀ メス"
        accentClass="bg-pink-50 text-pink-800"
        rows={female}
      />
      <SexResultGroup
        title="♂ オス"
        accentClass="bg-sky-50 text-sky-800"
        rows={male}
      />
    </div>
  );
}

// carrier_exploration の 1 シナリオ。通常結果とは別枠で表示する。
function CarrierScenario({ scenario }: { scenario: CarrierScenarioEntry }) {
  const assumed = Object.entries(scenario.assumed_carriers);
  return (
    <div className="rounded-md border border-amber-200 bg-amber-50 p-4">
      <h4 className="text-sm font-semibold text-amber-900">{scenario.label}</h4>
      <p className="mt-1 text-xs text-amber-700">
        根拠: {scenario.probability_basis}
        {scenario.prior_probability_applied ? " / 事前確率あり" : " / 条件付き"}
      </p>
      {assumed.length > 0 && (
        <ul className="mt-2 space-y-0.5 text-xs text-amber-800">
          {assumed.map(([parent, loci]) => (
            <li key={parent}>
              <span className="font-medium">{parent}</span>:{" "}
              {Object.entries(loci)
                .map(([locus, genotype]) => `${locus}=${genotype}`)
                .join(", ")}
            </li>
          ))}
        </ul>
      )}
      {scenario.new_colors.length > 0 && (
        <p className="mt-2 text-xs text-amber-800">
          新規に出現する毛色: {scenario.new_colors.join(", ")}
        </p>
      )}
      <div className="mt-3">
        <SexSplitResults rows={scenario.results} />
      </div>
    </div>
  );
}

export function ResultView({ data }: { data: CalculationResponse }) {
  const { diagnostics, parameters } = data;
  const carrierScenarios = data.carrier_exploration_results ?? [];
  // 入力 (親色 / 猫種 / モード) が変わったら結果カードを remount し、
  // 展開状態 (詳細を見る) を初期 (折りたたみ) に戻す。
  const resultsKey = `${parameters.sire_color}|${parameters.dam_color}|${parameters.breed ?? ""}|${parameters.mode}`;
  return (
    <div className="space-y-6">
      <section>
        <div className="flex items-baseline justify-between">
          <h2 className="text-lg font-semibold">計算結果</h2>
          <span className="rounded bg-slate-200 px-2 py-0.5 text-xs text-slate-600">
            モード: {data.mode}
          </span>
        </div>
        <div className="mt-3">
          <SexSplitResults key={resultsKey} rows={data.results} />
        </div>
      </section>

      <section className="rounded-md bg-slate-100 p-4 text-sm">
        <h3 className="font-semibold text-slate-700">診断情報</h3>
        <p className="mt-0.5 text-xs text-slate-400">
          座位（A / B / D…）をタップ／ホバーすると遺伝子座の解説が出ます。
        </p>
        <dl className="mt-2 grid grid-cols-1 gap-y-1 sm:grid-cols-2">
          <dt className="text-slate-500">展開した座位</dt>
          <dd className="flex flex-wrap items-center gap-1">
            {diagnostics.opened_loci.length > 0
              ? diagnostics.opened_loci.map((locus) => (
                  <LocusChip key={locus} locus={locus} />
                ))
              : "なし"}
          </dd>
          <dt className="text-slate-500">固定した座位</dt>
          <dd className="flex flex-wrap items-center gap-1">
            {diagnostics.closed_loci.length > 0
              ? diagnostics.closed_loci.map((locus) => (
                  <LocusChip key={locus} locus={locus} />
                ))
              : "なし"}
          </dd>
          <dt className="text-slate-500">未分類の確率</dt>
          <dd className="tabular-nums">
            {formatPct(diagnostics.unmatched_probability)} (
            {diagnostics.unmatched_genotype_count} 遺伝子型)
          </dd>
        </dl>
        {diagnostics.assumptions.length > 0 && (
          <div className="mt-2">
            <p className="text-slate-500">前提:</p>
            <ul className="ml-4 list-disc text-slate-600">
              {diagnostics.assumptions.map((assumption, index) => (
                <li key={index}>{assumption}</li>
              ))}
            </ul>
          </div>
        )}
      </section>

      {carrierScenarios.length > 0 && (
        <section className="space-y-3">
          <h3 className="text-base font-semibold">
            全キャリア探索シナリオ (参考・通常結果とは分離)
          </h3>
          {carrierScenarios.map((scenario) => (
            <CarrierScenario
              key={`${resultsKey}-${scenario.scenario}`}
              scenario={scenario}
            />
          ))}
        </section>
      )}
    </div>
  );
}
