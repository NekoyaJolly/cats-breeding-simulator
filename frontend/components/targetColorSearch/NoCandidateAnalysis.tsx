import type { ReverseLookupResponse } from "@/lib/schema";
import { UI_TEXT, type Language } from "@/lib/i18n";
import { InfoList } from "./InfoList";

// 交配候補が 1 件も無いときに、目標カラーの必要条件と確認すべき項目を案内する。
export function NoCandidateAnalysis({
  data,
  language,
}: {
  data: ReverseLookupResponse;
  language: Language;
}) {
  const text = UI_TEXT[language];
  return (
    <div className="rounded-md border border-conditional/30 bg-conditional-bg p-4 text-sm text-conditional">
      <p className="font-semibold">{text.targetForm.noCandidateMessage}</p>
      <div className="mt-3 grid grid-cols-1 gap-3 md:grid-cols-3">
        <InfoList
          title={text.targetForm.targetConditions}
          items={data.target_conditions}
        />
        <InfoList
          title={text.targetForm.uncheckedConditions}
          items={data.unchecked_conditions}
        />
        <InfoList
          title={text.targetForm.recommendedChecks}
          items={data.recommended_checks}
        />
      </div>
      <p className="mt-3 text-xs leading-5 text-conditional">
        {text.targetForm.complexScopeNote}
      </p>
    </div>
  );
}
