import type {
  CalculationResponse,
  CarrierScenarioEntry,
  ResultEntry,
} from "@/lib/schema";

// 確率を小数1桁の % 文字列に整形する。
function formatPct(value: number): string {
  return `${value.toFixed(1)}%`;
}

// 表現型の確率テーブル。results / シナリオ results で共用する。
function ResultTable({ rows }: { rows: ResultEntry[] }) {
  if (rows.length === 0) {
    return <p className="text-sm text-slate-500">該当する表現型がありません。</p>;
  }
  return (
    <table className="w-full border-collapse text-sm">
      <thead>
        <tr className="border-b border-slate-300 text-left text-slate-500">
          <th className="py-2 pr-4 font-medium">性別</th>
          <th className="py-2 pr-4 font-medium">毛色</th>
          <th className="py-2 text-right font-medium">確率</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((row, index) => (
          <tr
            key={`${row.sex}-${row.color}-${index}`}
            className="border-b border-slate-100"
          >
            <td className="py-2 pr-4">{row.sex}</td>
            <td className="py-2 pr-4">{row.color}</td>
            <td className="py-2 text-right tabular-nums">
              {formatPct(row.probability_pct)}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
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
        <ResultTable rows={scenario.results} />
      </div>
    </div>
  );
}

export function ResultView({ data }: { data: CalculationResponse }) {
  const { diagnostics } = data;
  const carrierScenarios = data.carrier_exploration_results ?? [];
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
          <ResultTable rows={data.results} />
        </div>
      </section>

      <section className="rounded-md bg-slate-100 p-4 text-sm">
        <h3 className="font-semibold text-slate-700">診断情報</h3>
        <dl className="mt-2 grid grid-cols-1 gap-y-1 sm:grid-cols-2">
          <dt className="text-slate-500">展開した座位</dt>
          <dd>{diagnostics.opened_loci.join(", ") || "なし"}</dd>
          <dt className="text-slate-500">固定した座位</dt>
          <dd>{diagnostics.closed_loci.join(", ") || "なし"}</dd>
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
            <CarrierScenario key={scenario.scenario} scenario={scenario} />
          ))}
        </section>
      )}
    </div>
  );
}
