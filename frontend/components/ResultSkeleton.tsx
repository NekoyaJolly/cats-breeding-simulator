import { UI_TEXT, type Language } from "@/lib/i18n";

// 計算中に結果レポートの代わりに出すスケルトン。折りたたみ状態のアコーディオン
// (見出しバー) を模した 5 枚のプレースホルダを淡くパルスさせる。
// prefers-reduced-motion では animate-skeleton が無効化される (globals.css)。
const ROWS = [0, 1, 2, 3, 4];

export function ResultSkeleton({ language }: { language: Language }) {
  const text = UI_TEXT[language];
  return (
    <div className="mt-6 flex flex-col gap-2">
      {/* スケルトン自体は装飾なので読み上げ対象外。状態は sr-only の live text で伝える。 */}
      <span className="sr-only" role="status" aria-live="polite">
        {text.parentResult.resultLoading}
      </span>
      {ROWS.map((row) => (
        <div
          key={row}
          aria-hidden="true"
          className="animate-skeleton rounded-xl"
          style={{ background: "var(--r-surface)", border: "1px solid var(--r-hairline)" }}
        >
          <div className="flex items-center gap-2 px-3 py-3.5">
            <span
              className="h-2 w-2 shrink-0 rounded-[2px]"
              style={{ background: "var(--r-hairline)" }}
            />
            <span
              className="h-3 rounded"
              style={{ width: `${38 + (row % 3) * 16}%`, background: "var(--r-hairline)" }}
            />
            <span
              className="ml-auto h-3 w-3.5 shrink-0 rounded"
              style={{ background: "var(--r-hairline)" }}
            />
          </div>
        </div>
      ))}
    </div>
  );
}
