import type { ReverseLookupResponse } from "@/lib/schema";
import { InfoList } from "./InfoList";

// 交配候補が 1 件も無いときに、目標カラーの必要条件と確認すべき項目を案内する。
export function NoCandidateAnalysis({ data }: { data: ReverseLookupResponse }) {
  return (
    <div className="rounded-md border border-amber-200 bg-amber-50 p-4 text-sm text-amber-950">
      <p className="font-semibold">
        現在の登録情報では、目標カラーの成立条件を満たす交配候補を確認できません。
      </p>
      <div className="mt-3 grid grid-cols-1 gap-3 md:grid-cols-3">
        <InfoList title="目標カラーに必要な主な条件" items={data.target_conditions} />
        <InfoList title="現在確認できない条件" items={data.unchecked_conditions} />
        <InfoList title="確認するとよい項目" items={data.recommended_checks} />
      </div>
      <p className="mt-3 text-xs leading-5 text-amber-800">
        ゴールデン / ワイドバンド / CORIN系は品種・系統で扱いが複雑なため、
        現在の対応範囲では登録情報と既存ルールに基づく確認結果として表示します。
      </p>
    </div>
  );
}
