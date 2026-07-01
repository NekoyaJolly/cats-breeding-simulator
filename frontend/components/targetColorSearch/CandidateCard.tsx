import { GenderFemale, GenderMale } from "@phosphor-icons/react";
import type { ReverseLookupCandidate } from "@/lib/schema";
import { UI_TEXT, type Language } from "@/lib/i18n";
import { getLocusTone } from "@/lib/lociGlossary";
import { InfoList } from "./InfoList";
import { colorRows, formatPct } from "./format";
import { LocusChip } from "../LocusChip";

// 1 件の交配候補 (父 × 母) を、確率・成立条件・座位別根拠つきで折りたたみ表示する。
export function CandidateCard({
  candidate,
  index,
  language,
  categoryLabel,
}: {
  candidate: ReverseLookupCandidate;
  index: number;
  language: Language;
  categoryLabel: string;
}) {
  const text = UI_TEXT[language];
  // サマリーに出す代表確率は、確定確率があればそれ、無ければ条件付き最大確率。
  const summaryProbability =
    candidate.confirmed_probability_pct > 0
      ? candidate.confirmed_probability_pct
      : candidate.conditional_max_probability_pct;

  return (
    <details className="rounded-md border border-slate-200 bg-white">
      <summary className="flex cursor-pointer flex-wrap items-center justify-between gap-3 px-4 py-3">
        <div>
          <p className="text-xs font-medium text-slate-400">
            {text.targetForm.matchLabel} {index + 1}
          </p>
          <h4 className="text-base font-semibold text-slate-800">
            {candidate.sire.name} × {candidate.dam.name}
          </h4>
          <div className="mt-1 flex flex-wrap items-center gap-1.5 text-xs">
            <span className="inline-flex items-center gap-1 rounded bg-sky-50 px-1.5 py-0.5 font-medium text-sky-700">
              <GenderMale aria-hidden="true" className="h-3.5 w-3.5" weight="duotone" />
              {candidate.sire.color}
            </span>
            <span className="inline-flex items-center gap-1 rounded bg-rose-50 px-1.5 py-0.5 font-medium text-rose-700">
              <GenderFemale aria-hidden="true" className="h-3.5 w-3.5" weight="duotone" />
              {candidate.dam.color}
            </span>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <span className="rounded bg-slate-100 px-2 py-1 text-xs font-medium text-slate-600">
            {categoryLabel}
          </span>
          <span className="text-lg font-semibold tabular-nums text-slate-800">
            {formatPct(summaryProbability)}
          </span>
        </div>
      </summary>

      <div className="border-t border-slate-100 p-4">
        <div className="grid grid-cols-2 gap-3">
          <div className="rounded-md bg-emerald-50 p-3">
            <p className="text-xs text-emerald-700">
              {text.targetForm.confirmedProbability}
            </p>
            <p className="text-xl font-semibold tabular-nums text-emerald-900">
              {formatPct(candidate.confirmed_probability_pct)}
            </p>
          </div>
          <div className="rounded-md bg-amber-50 p-3">
            <p className="text-xs text-amber-700">
              {text.targetForm.conditionalMaxProbability}
            </p>
            <p className="text-xl font-semibold tabular-nums text-amber-900">
              {formatPct(candidate.conditional_max_probability_pct)}
            </p>
          </div>
        </div>

        <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-2">
          <InfoList
            title={text.targetForm.establishmentConditions}
            items={candidate.establishment_conditions}
          />
          <InfoList
            title={text.targetForm.confirmationNeeded}
            items={
              candidate.confirmation_needed.length > 0
                ? candidate.confirmation_needed
                : [text.targetForm.noConfirmationNeeded]
            }
          />
          <InfoList
            title={text.targetForm.recommendedTests}
            items={
              candidate.recommended_tests.length > 0
                ? candidate.recommended_tests
                : [text.targetForm.noRecommendedTests]
            }
          />
          <div className="rounded-md bg-slate-50 p-3 text-sm">
            <p className="font-medium text-slate-700">
              {text.targetForm.otherPossibleCoats}
            </p>
            <p className="mt-1 text-xs leading-5 text-slate-600">
              {colorRows(candidate.other_possible_colors, text.targetForm.noOtherCoats)}
            </p>
          </div>
        </div>

        <div className="mt-4 overflow-hidden rounded-md border border-slate-200">
          <table className="min-w-full text-left text-xs">
            <thead className="bg-slate-50 text-slate-500">
              <tr>
                <th className="px-3 py-2 font-medium">{text.targetForm.locus}</th>
                <th className="px-3 py-2 font-medium">
                  {text.targetForm.targetCondition}
                </th>
                <th className="px-3 py-2 font-medium">{text.targetForm.sireSide}</th>
                <th className="px-3 py-2 font-medium">{text.targetForm.damSide}</th>
                <th className="px-3 py-2 font-medium">{text.targetForm.basis}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {candidate.locus_evidence.map((evidence) => {
                const tone = getLocusTone(evidence.locus);
                return (
                  <tr key={evidence.locus}>
                    <td className={`px-3 py-2 font-medium ${tone.tableCellClass}`}>
                      <LocusChip locus={evidence.locus} />
                    </td>
                    <td className="px-3 py-2 text-slate-600">{evidence.target}</td>
                    <td className="px-3 py-2 text-slate-600">{evidence.sire}</td>
                    <td className="px-3 py-2 text-slate-600">{evidence.dam}</td>
                    <td className="px-3 py-2 text-slate-500">{evidence.note}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </details>
  );
}
