import type { ReverseLookupCandidate } from "@/lib/schema";
import { InfoList } from "./InfoList";
import { colorRows, formatPct } from "./format";

// 1 件の交配候補 (父 × 母) を、確率・成立条件・座位別根拠つきで折りたたみ表示する。
export function CandidateCard({
  candidate,
  index,
}: {
  candidate: ReverseLookupCandidate;
  index: number;
}) {
  // サマリーに出す代表確率は、確定確率があればそれ、無ければ条件付き最大確率。
  const summaryProbability =
    candidate.confirmed_probability_pct > 0
      ? candidate.confirmed_probability_pct
      : candidate.conditional_max_probability_pct;

  return (
    <details className="rounded-md border border-slate-200 bg-white">
      <summary className="flex cursor-pointer flex-wrap items-center justify-between gap-3 px-4 py-3">
        <div>
          <p className="text-xs font-medium text-slate-400">組み合わせ {index + 1}</p>
          <h4 className="text-base font-semibold text-slate-800">
            {candidate.sire.name} × {candidate.dam.name}
          </h4>
          <p className="mt-1 text-xs text-slate-500">
            {candidate.sire.color} ♂ / {candidate.dam.color} ♀
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className="rounded bg-slate-100 px-2 py-1 text-xs font-medium text-slate-600">
            {candidate.category}
          </span>
          <span className="text-lg font-semibold tabular-nums text-slate-800">
            {formatPct(summaryProbability)}
          </span>
        </div>
      </summary>

      <div className="border-t border-slate-100 p-4">
        <div className="grid grid-cols-2 gap-3">
          <div className="rounded-md bg-emerald-50 p-3">
            <p className="text-xs text-emerald-700">確定確率</p>
            <p className="text-xl font-semibold tabular-nums text-emerald-900">
              {formatPct(candidate.confirmed_probability_pct)}
            </p>
          </div>
          <div className="rounded-md bg-amber-50 p-3">
            <p className="text-xs text-amber-700">条件付き最大確率</p>
            <p className="text-xl font-semibold tabular-nums text-amber-900">
              {formatPct(candidate.conditional_max_probability_pct)}
            </p>
          </div>
        </div>

        <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-2">
          <InfoList title="成立条件" items={candidate.establishment_conditions} />
          <InfoList
            title="確認が必要な条件"
            items={
              candidate.confirmation_needed.length > 0
                ? candidate.confirmation_needed
                : ["追加確認なしで評価できます。"]
            }
          />
          <InfoList
            title="推奨検査"
            items={
              candidate.recommended_tests.length > 0
                ? candidate.recommended_tests
                : ["現時点で追加検査の提案はありません。"]
            }
          />
          <div className="rounded-md bg-slate-50 p-3 text-sm">
            <p className="font-medium text-slate-700">
              目標カラー以外に生まれる可能性のあるカラー
            </p>
            <p className="mt-1 text-xs leading-5 text-slate-600">
              {colorRows(candidate.other_possible_colors)}
            </p>
          </div>
        </div>

        <div className="mt-4 overflow-hidden rounded-md border border-slate-200">
          <table className="min-w-full text-left text-xs">
            <thead className="bg-slate-50 text-slate-500">
              <tr>
                <th className="px-3 py-2 font-medium">座位</th>
                <th className="px-3 py-2 font-medium">目標条件</th>
                <th className="px-3 py-2 font-medium">父猫側</th>
                <th className="px-3 py-2 font-medium">母猫側</th>
                <th className="px-3 py-2 font-medium">根拠</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {candidate.locus_evidence.map((evidence) => (
                <tr key={evidence.locus}>
                  <td className="px-3 py-2 font-medium text-slate-700">
                    {evidence.locus}
                  </td>
                  <td className="px-3 py-2 text-slate-600">{evidence.target}</td>
                  <td className="px-3 py-2 text-slate-600">{evidence.sire}</td>
                  <td className="px-3 py-2 text-slate-600">{evidence.dam}</td>
                  <td className="px-3 py-2 text-slate-500">{evidence.note}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </details>
  );
}
