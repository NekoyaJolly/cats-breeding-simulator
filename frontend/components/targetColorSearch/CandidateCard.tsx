import { GenderFemale, GenderMale } from "@phosphor-icons/react";
import type { ReverseLookupCandidate } from "@/lib/schema";
import { UI_TEXT, type Language } from "@/lib/i18n";
import { getLocusTone } from "@/lib/lociGlossary";
import { InfoList } from "./InfoList";
import { colorRows, formatPct, groupedColorNameRows } from "./format";
import { LocusChip } from "../LocusChip";

function moreCountLabel(count: number, language: Language): string {
  return language === "ja" ? `他${count}件` : `${count} more`;
}

function OtherColorRows({
  rows,
  emptyText,
  language,
}: {
  rows: ReverseLookupCandidate["other_possible_colors"];
  emptyText: string;
  language: Language;
}) {
  const groups = groupedColorNameRows(rows);
  if (groups.length === 0) {
    return (
      <p className="mt-1 text-xs leading-5 text-ink-soft">
        {emptyText}
      </p>
    );
  }

  return (
    <div className="mt-1 space-y-1 text-xs leading-5 text-ink-soft">
      {groups.map((group) => (
        <p key={group.sex}>
          <span className="font-semibold text-ink-soft">{group.symbol}</span>{" "}
          <span>{group.colors.join(" / ")}</span>
          {group.hiddenCount > 0 && (
            <span className="ml-1 text-muted">
              {moreCountLabel(group.hiddenCount, language)}
            </span>
          )}
        </p>
      ))}
    </div>
  );
}

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
    <details className="rounded-md border border-line bg-surface">
      <summary className="flex cursor-pointer flex-wrap items-center justify-between gap-3 px-4 py-3">
        <div>
          <p className="text-xs font-medium text-muted">
            {text.targetForm.matchLabel} {index + 1}
          </p>
          <h4 className="text-base font-semibold text-ink">
            {candidate.sire.name} × {candidate.dam.name}
          </h4>
          <div className="mt-1 flex flex-wrap items-center gap-1.5 text-xs leading-5">
            <span className="inline-flex items-center gap-1 rounded bg-accent/10 px-1.5 py-0.5 font-medium leading-5 text-accent">
              <GenderMale aria-hidden="true" className="h-3.5 w-3.5" weight="duotone" />
              {candidate.sire.color}
            </span>
            <span className="inline-flex items-center gap-1 rounded bg-danger-bg px-1.5 py-0.5 font-medium leading-5 text-danger">
              <GenderFemale aria-hidden="true" className="h-3.5 w-3.5" weight="duotone" />
              {candidate.dam.color}
            </span>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <span className="rounded bg-surface-2 px-2 py-1 text-xs font-medium text-ink-soft">
            {categoryLabel}
          </span>
          <span className="text-lg font-semibold tabular-nums text-ink">
            {formatPct(summaryProbability)}
          </span>
        </div>
      </summary>

      <div className="border-t border-line-soft p-4">
        <div className="grid grid-cols-2 gap-3">
          <div className="rounded-md bg-confirmed-bg p-3">
            <p className="text-xs text-confirmed">
              {text.targetForm.confirmedProbability}
            </p>
            <p className="text-xl font-semibold tabular-nums text-confirmed">
              {formatPct(candidate.confirmed_probability_pct)}
            </p>
          </div>
          <div className="rounded-md bg-conditional-bg p-3">
            <p className="text-xs text-conditional">
              {text.targetForm.conditionalMaxProbability}
            </p>
            <p className="text-xl font-semibold tabular-nums text-conditional">
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
          <div className="rounded-md bg-bg p-3 text-sm">
            <p className="font-medium text-ink-soft">
              {text.targetForm.targetPossibleCoats}
            </p>
            <p className="mt-1 text-xs leading-5 text-ink-soft">
              {colorRows(candidate.target_possible_colors, text.targetForm.noTargetCoats)}
            </p>
          </div>
          <div className="rounded-md bg-bg p-3 text-sm">
            <p className="font-medium text-ink-soft">
              {text.targetForm.otherPossibleCoats}
            </p>
            <OtherColorRows
              rows={candidate.other_possible_colors}
              emptyText={text.targetForm.noOtherCoats}
              language={language}
            />
          </div>
        </div>

        <div className="mt-4 overflow-hidden rounded-md border border-line">
          <table className="min-w-full text-left text-xs">
            <thead className="bg-bg text-muted">
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
            <tbody className="divide-y divide-line-soft">
              {candidate.locus_evidence.map((evidence) => {
                const tone = getLocusTone(evidence.locus);
                return (
                  <tr key={evidence.locus}>
                    <td className={`px-3 py-2 font-medium ${tone.tableCellClass}`}>
                      <LocusChip locus={evidence.locus} />
                    </td>
                    <td className="px-3 py-2 text-ink-soft">{evidence.target}</td>
                    <td className="px-3 py-2 text-ink-soft">{evidence.sire}</td>
                    <td className="px-3 py-2 text-ink-soft">{evidence.dam}</td>
                    <td className="px-3 py-2 text-muted">{evidence.note}</td>
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
