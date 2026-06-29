import type { ReverseLookupResponse } from "@/lib/schema";
import { CandidateCard } from "./CandidateCard";
import { NoCandidateAnalysis } from "./NoCandidateAnalysis";
import { CATEGORIES, targetSexLabel } from "./format";

// 逆引き結果を、カテゴリ (確定 / 条件付き / 判定難 / 確認不可) ごとに分類して並べる。
export function ResultsView({ data }: { data: ReverseLookupResponse }) {
  const grouped = CATEGORIES.map((category) => ({
    category,
    candidates: data.candidates.filter((candidate) => candidate.category === category),
  }));

  return (
    <section className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 className="text-lg font-semibold text-slate-800">結果ランキング</h3>
        <span className="rounded bg-slate-100 px-2 py-1 text-xs text-slate-600">
          目標: {targetSexLabel(data.target_sex)} / {data.target_color}
        </span>
      </div>
      {data.candidates.length === 0 && <NoCandidateAnalysis data={data} />}
      {grouped.map((group) => (
        <section key={group.category} className="space-y-3">
          <div className="flex items-center justify-between border-b border-slate-200 pb-1">
            <h4 className="text-sm font-semibold text-slate-700">{group.category}</h4>
            <span className="text-xs text-slate-400">{group.candidates.length} 件</span>
          </div>
          {group.candidates.length > 0 ? (
            group.candidates.map((candidate, index) => (
              <CandidateCard
                key={`${candidate.sire.id}-${candidate.dam.id}-${group.category}`}
                candidate={candidate}
                index={index}
              />
            ))
          ) : (
            <p className="text-sm text-slate-500">
              このカテゴリで確認できる交配候補はまだありません。
            </p>
          )}
        </section>
      ))}
    </section>
  );
}
