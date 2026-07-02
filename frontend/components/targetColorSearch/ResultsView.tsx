import type { ReverseLookupResponse } from "@/lib/schema";
import { UI_TEXT, type Language } from "@/lib/i18n";
import { CandidateCard } from "./CandidateCard";
import { NoCandidateAnalysis } from "./NoCandidateAnalysis";
import { PUBLIC_CATEGORIES } from "./format";

// 逆引き結果を、ユーザーに見せる産出条件 (条件無し / 条件付き) ごとに分類して並べる。
export function ResultsView({
  data,
  language,
}: {
  data: ReverseLookupResponse;
  language: Language;
}) {
  const text = UI_TEXT[language];
  const grouped = PUBLIC_CATEGORIES.map((category) => ({
    category,
    candidates: data.candidates.filter((candidate) => candidate.category === category),
  })).filter((group) => group.candidates.length > 0);
  const hasVisibleCandidates = grouped.length > 0;
  const targetSex =
    data.target_sex === "male"
      ? text.common.male
      : data.target_sex === "female"
        ? text.common.female
        : text.common.any;

  function categoryLabel(category: (typeof PUBLIC_CATEGORIES)[number]): string {
    if (category === "確定で期待できる") return text.targetForm.categories.confirmed;
    return text.targetForm.categories.conditional;
  }

  function categoryDescription(category: (typeof PUBLIC_CATEGORIES)[number]): string {
    if (category === "確定で期待できる") {
      return text.targetForm.categoryDescriptions.confirmed;
    }
    return text.targetForm.categoryDescriptions.conditional;
  }

  return (
    <section className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 className="text-lg font-semibold text-slate-800">
          {text.targetForm.ranking}
        </h3>
        <span className="rounded bg-slate-100 px-2 py-1 text-xs leading-5 text-slate-600">
          {text.targetForm.targetSummary}: {targetSex} / {data.target_color}
        </span>
      </div>
      {!hasVisibleCandidates && (
        <NoCandidateAnalysis data={data} language={language} />
      )}
      {grouped.map((group) => (
        <section key={group.category} className="space-y-3">
          <div className="flex items-start justify-between gap-3 border-b border-slate-200 pb-1">
            <div>
              <p className="text-[11px] font-medium text-slate-400">
                {text.targetForm.productionCondition}
              </p>
              <h4 className="text-sm font-semibold text-slate-700">
                {categoryLabel(group.category)}
              </h4>
              <p className="text-xs leading-5 text-slate-500">
                {categoryDescription(group.category)}
              </p>
            </div>
            <span className="text-xs text-slate-400">
              {language === "ja"
                ? `${group.candidates.length} 件`
                : group.candidates.length}
            </span>
          </div>
          {group.candidates.map((candidate, index) => (
            <CandidateCard
              key={`${candidate.sire.id}-${candidate.dam.id}-${group.category}`}
              candidate={candidate}
              index={index}
              language={language}
              categoryLabel={categoryLabel(group.category)}
            />
          ))}
        </section>
      ))}
    </section>
  );
}
