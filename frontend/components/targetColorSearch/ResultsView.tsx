import type { ReverseLookupResponse } from "@/lib/schema";
import { UI_TEXT, type Language } from "@/lib/i18n";
import { CandidateCard } from "./CandidateCard";
import { NoCandidateAnalysis } from "./NoCandidateAnalysis";
import { CATEGORIES } from "./format";

// 逆引き結果を、カテゴリ (確定 / 条件付き / 判定難 / 確認不可) ごとに分類して並べる。
export function ResultsView({
  data,
  language,
}: {
  data: ReverseLookupResponse;
  language: Language;
}) {
  const text = UI_TEXT[language];
  const grouped = CATEGORIES.map((category) => ({
    category,
    candidates: data.candidates.filter((candidate) => candidate.category === category),
  }));
  const targetSex =
    data.target_sex === "male"
      ? text.common.male
      : data.target_sex === "female"
        ? text.common.female
        : text.common.any;

  function categoryLabel(category: (typeof CATEGORIES)[number]): string {
    if (category === "確定で期待できる") return text.targetForm.categories.confirmed;
    if (category === "条件付きで期待できる") {
      return text.targetForm.categories.conditional;
    }
    if (category === "現在の情報では判定が難しい") {
      return text.targetForm.categories.difficult;
    }
    return text.targetForm.categories.unavailable;
  }

  return (
    <section className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h3 className="text-lg font-semibold text-slate-800">
            {text.targetForm.ranking}
          </h3>
          <p className="mt-1 text-xs leading-5 text-slate-500">
            {text.onboarding.resultBody}
          </p>
        </div>
        <span className="rounded bg-slate-100 px-2 py-1 text-xs text-slate-600">
          {text.targetForm.targetSummary}: {targetSex} / {data.target_color}
        </span>
      </div>
      {data.candidates.length === 0 && (
        <NoCandidateAnalysis data={data} language={language} />
      )}
      {grouped.map((group) => (
        <section key={group.category} className="space-y-3">
          <div className="flex items-center justify-between border-b border-slate-200 pb-1">
            <h4 className="text-sm font-semibold text-slate-700">
              {categoryLabel(group.category)}
            </h4>
            <span className="text-xs text-slate-400">
              {language === "ja"
                ? `${group.candidates.length} 件`
                : group.candidates.length}
            </span>
          </div>
          {group.candidates.length > 0 ? (
            group.candidates.map((candidate, index) => (
              <CandidateCard
                key={`${candidate.sire.id}-${candidate.dam.id}-${group.category}`}
                candidate={candidate}
                index={index}
                language={language}
                categoryLabel={categoryLabel(group.category)}
              />
            ))
          ) : (
            <p className="text-sm text-slate-500">
              {text.targetForm.noCategoryCandidates}
            </p>
          )}
        </section>
      ))}
    </section>
  );
}
