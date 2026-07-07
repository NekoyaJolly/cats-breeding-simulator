"use client";

import { GenderFemale, GenderMale } from "@phosphor-icons/react";
import { useEffect, useId, useRef, useState, type ReactNode } from "react";
import type {
  CalculationResponse,
  CarrierScenarioEntry,
  ConditionalColorGroup,
  ParentColorNote,
  ResultEntry,
} from "@/lib/schema";
import { UI_TEXT, type Language } from "@/lib/i18n";
import { LocusChip } from "./LocusChip";
import { LOCUS_GLOSSARY } from "@/lib/lociGlossary";
import { coatSwatchBackground } from "@/lib/coatColorSwatch";

// 入力した親色が子に出ないときの注釈。劣性形質の理解補助 (なぜ親の色が出ないか)。
function ParentColorNotes({
  notes,
  language,
}: {
  notes: ParentColorNote[];
  language: Language;
}) {
  const text = UI_TEXT[language];
  if (notes.length === 0) return null;
  return (
    <div className="mt-3 space-y-2">
      {notes.map((note) => {
        const parent = note.parent === "sire" ? text.parentResult.sire : text.parentResult.dam;
        const other = note.parent === "sire" ? text.parentResult.dam : text.parentResult.sire;
        return (
          <div
            key={note.parent}
            className="rounded-md border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900"
          >
            {language === "ja" ? (
              <>
                <span className="font-medium">
                  {parent}の色柄「{note.color}」
                </span>
                はこの組み合わせでは子猫に出現しません。
                {note.blocked_factors.length > 0 && (
                  <>
                    {other}が次の劣性因子を持たないためです:{" "}
                    <span className="font-medium">
                      {note.blocked_factors.join(" ・ ")}
                    </span>
                    。
                  </>
                )}
              </>
            ) : (
              <>
                <span className="font-medium">
                  The {parent.toLowerCase()} coat &quot;{note.color}&quot;
                </span>{" "}
                does not appear in this combination.
                {note.blocked_factors.length > 0 && (
                  <>
                    {" "}
                    The {other.toLowerCase()} does not carry these recessive
                    factors:{" "}
                    <span className="font-medium">
                      {note.blocked_factors.join(", ")}
                    </span>
                    .
                  </>
                )}
              </>
            )}
          </div>
        );
      })}
    </div>
  );
}

// 通常モードの計算範囲を平易に説明する畳める注記。
// 隠れ劣性キャリアを展開しない設計上、理論上は出るが確定できない毛色を出さないため、
// 「なぜ出ないのか」と回避策 (明示キャリアモード) を伝える。normal モードのときだけ表示する。
function NormalModeNote({ language }: { language: Language }) {
  const text = UI_TEXT[language];
  const [open, setOpen] = useState(false);
  return (
    <div className="mt-3 rounded-md border border-slate-200 bg-slate-50 p-3 text-sm text-slate-600">
      <div className="flex items-start justify-between gap-2">
        <p className="min-w-0">
          <span className="font-medium text-slate-700">
            {text.parentResult.normalScopeTitle}
          </span>
          {" — "}
          {text.parentResult.normalScopeSummary}
        </p>
        <button
          type="button"
          onClick={() => setOpen((value) => !value)}
          className="shrink-0 rounded px-2 py-0.5 text-xs font-medium text-slate-500 hover:bg-slate-100"
          aria-expanded={open}
        >
          {open ? text.parentResult.close : text.parentResult.normalScopeMore}
        </button>
      </div>
      {open && (
        <p className="mt-2 leading-relaxed">
          {text.parentResult.normalScopeDetails}
        </p>
      )}
    </div>
  );
}

// 確率を小数1桁の % 文字列に整形する (診断値など正確さ優先の箇所で使う)。
function formatPct(value: number): string {
  return `${value.toFixed(1)}%`;
}

// AOC (Any Other Color) は集約カテゴリ。どちらの親が White かで導線文言を切り替える。
type WhiteSide = "sire" | "dam" | "both" | "none";

// パラメータの親色から White 側を判定する。White は入力サジェストの canonical 正式名なので
// 前後空白を除いた完全一致で見る (Black-White 等のバイカラーを誤検出しないため includes は使わない)。
function whiteSideOf(sireColor: string, damColor: string): WhiteSide {
  const isWhite = (color: string) => color.trim().toLowerCase() === "white";
  const sire = isWhite(sireColor);
  const dam = isWhite(damColor);
  if (sire && dam) return "both";
  if (sire) return "sire";
  if (dam) return "dam";
  return "none";
}

// AOC 行のフォーカス/ホバー時にだけ開く説明ポップオーバー (§2.3)。
// デフォルトは非表示。押し付けず、気になったときにだけ「未確定の理由」と「下の色を入力すれば
// 確定する」導線を出す (explicit_carrier への自然な誘導)。閉じるは外側クリック / Escape / blur。
function AocInfo({
  whiteSide,
  language,
}: {
  whiteSide: WhiteSide;
  language: Language;
}) {
  const text = UI_TEXT[language];
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLSpanElement>(null);
  const tooltipId = useId();

  useEffect(() => {
    if (!open) return;
    function onPointerDown(event: MouseEvent) {
      if (!containerRef.current?.contains(event.target as Node)) setOpen(false);
    }
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") setOpen(false);
    }
    document.addEventListener("mousedown", onPointerDown);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("mousedown", onPointerDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [open]);

  const hint =
    whiteSide === "sire"
      ? text.parentResult.aocHintSire
      : whiteSide === "dam"
        ? text.parentResult.aocHintDam
        : whiteSide === "both"
          ? text.parentResult.aocHintBoth
          : text.parentResult.aocHintGeneric;

  return (
    <span
      ref={containerRef}
      className="relative ml-1 inline-block align-middle"
      onMouseEnter={() => setOpen(true)}
      onMouseLeave={() => setOpen(false)}
    >
      <button
        type="button"
        // click / focus は「開く」に統一 (LocusChip と同じ運用)。閉じるは外側クリック等に任せる。
        onClick={() => setOpen(true)}
        onFocus={() => setOpen(true)}
        onBlur={() => setOpen(false)}
        className="flex h-4 w-4 cursor-help items-center justify-center rounded-full border border-slate-300 text-[10px] leading-none text-slate-400 hover:text-slate-600"
        aria-expanded={open}
        // aria-describedby は常時付与 (フォーカス瞬間に関連付けが無いと読み上げを取りこぼす)。
        aria-describedby={tooltipId}
        aria-label={text.parentResult.aocAria}
      >
        ?
      </button>
      <span
        role="tooltip"
        id={tooltipId}
        className={`absolute left-0 top-full z-20 mt-1 w-64 max-w-[80vw] rounded-md border border-slate-200 bg-white p-2 text-left text-xs font-normal text-slate-600 shadow-lg ${
          open ? "block" : "hidden"
        }`}
      >
        <span className="block font-semibold text-slate-800">
          {text.parentResult.aocTitle}
        </span>
        <span className="mt-0.5 block leading-relaxed">
          {text.parentResult.aocBody}
        </span>
        <span className="mt-1 block text-[11px] text-slate-400">
          {hint} {text.parentResult.aocMore}
        </span>
      </span>
    </span>
  );
}

// 確率を整数 % に丸める (結果表示用)。0 超で四捨五入が 0 になる微小値は "<1%"。
function formatPctInt(value: number): string {
  if (value <= 0) return "0%";
  const rounded = Math.round(value);
  return rounded === 0 ? "<1%" : `${rounded}%`;
}

// 各性別グループで常時表示する上位件数 (ベース色グループ単位)。残りは「詳細を見る」。
const TOP_N = 5;

// 白斑サフィックス。長い順に判定する ("-White Van" を "-White" より先に)。
const WHITE_SUFFIXES = ["-White Van", "-White"] as const;

type WhitePortion = { label: string; pct: number };
type ColorGroup = { base: string; total: number; whites: WhitePortion[] };

// 色名から白斑サフィックスを剥がし、ベース色と白斑ラベルに分ける。
// 例: "Silver Patched Tabby-White" -> { base: "Silver Patched Tabby", whiteLabel: "-White" }
function splitWhite(color: string): { base: string; whiteLabel: string | null } {
  for (const suffix of WHITE_SUFFIXES) {
    if (color.endsWith(suffix)) {
      return { base: color.slice(0, color.length - suffix.length), whiteLabel: suffix };
    }
  }
  return { base: color, whiteLabel: null };
}

// 結果をベース色でまとめる。白斑あり (-White / -White Van) は副次内訳として保持する。
// グループは合計確率の降順、白斑内訳も確率降順で並べる。
function groupByBase(rows: ResultEntry[]): ColorGroup[] {
  const map = new Map<string, ColorGroup>();
  for (const row of rows) {
    const { base, whiteLabel } = splitWhite(row.color);
    const group = map.get(base) ?? { base, total: 0, whites: [] };
    group.total += row.probability_pct;
    if (whiteLabel) {
      group.whites.push({ label: whiteLabel, pct: row.probability_pct });
    }
    map.set(base, group);
  }
  const groups = [...map.values()];
  for (const group of groups) {
    group.whites.sort((a, b) => b.pct - a.pct);
  }
  groups.sort((a, b) => b.total - a.total || a.base.localeCompare(b.base));
  return groups;
}

// 1 性別ぶんの結果カード。ベース色でまとめた上位 TOP_N グループを常に見せ、
// 残りは「詳細を見る (残り N 件)」で展開 / 「閉じる」で折りたたむ (性別ごとに独立)。
function SexResultGroup({
  title,
  icon,
  accentClass,
  rows,
  language,
  whiteSide,
}: {
  title: string;
  icon: ReactNode;
  accentClass: string;
  rows: ResultEntry[];
  language: Language;
  whiteSide: WhiteSide;
}) {
  const text = UI_TEXT[language];
  const [expanded, setExpanded] = useState(false);
  const groups = groupByBase(rows);
  const total = rows.reduce((sum, row) => sum + row.probability_pct, 0);
  const visible = expanded ? groups : groups.slice(0, TOP_N);
  const hiddenCount = groups.length - visible.length;

  return (
    <div className="overflow-hidden rounded-md border border-slate-200">
      <div
        className={`flex items-center justify-between gap-3 px-4 py-2 ${accentClass}`}
      >
        <div className="flex min-w-0 items-center gap-2">
          <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-white/80">
            {icon}
          </span>
          <h3 className="truncate text-sm font-semibold leading-5">{title}</h3>
        </div>
        {/* 各行は整数丸めのため合計が厳密一致しない。概算であることを「約」で明示する。 */}
        <span className="text-xs leading-5 tabular-nums opacity-80">
          {text.parentResult.totalApprox}
          {formatPctInt(total)}
        </span>
      </div>
      {groups.length === 0 ? (
        <p className="px-4 py-3 text-sm text-slate-500">
          {text.parentResult.noPhenotype}
        </p>
      ) : (
        <>
          <ul className="divide-y divide-slate-100">
            {visible.map((group) => (
              <li key={group.base} className="px-4 py-1.5">
                <div className="flex items-center justify-between gap-2 text-sm">
                  <span className="min-w-0 break-words text-slate-700">
                    {group.base}
                    {group.base === "AOC" && (
                      <AocInfo whiteSide={whiteSide} language={language} />
                    )}
                  </span>
                  <span className="shrink-0 tabular-nums text-slate-600">
                    {formatPctInt(group.total)}
                  </span>
                </div>
                {group.whites.map((white) => (
                  <div
                    key={white.label}
                    className="flex items-center justify-between gap-2 pl-3 text-xs text-slate-400"
                  >
                    <span>└ {white.label}</span>
                    <span className="shrink-0 tabular-nums">
                      {formatPctInt(white.pct)}
                    </span>
                  </div>
                ))}
              </li>
            ))}
          </ul>
          {groups.length > TOP_N && (
            <button
              type="button"
              onClick={() => setExpanded((value) => !value)}
              className="w-full border-t border-slate-100 px-4 py-2 text-xs font-medium text-slate-500 hover:bg-slate-50"
              aria-expanded={expanded}
            >
              {expanded
                ? text.parentResult.close
                : language === "ja"
                  ? `${text.parentResult.showDetails} (${text.parentResult.remaining} ${hiddenCount} 件)`
                  : `${text.parentResult.showDetails} (${hiddenCount} ${text.parentResult.remaining})`}
            </button>
          )}
        </>
      )}
    </div>
  );
}

// 結果を ♂ / ♀ に分割して表示する。デスクトップは横並び、モバイルは縦積み。
function SexSplitResults({
  rows,
  language,
  whiteSide,
}: {
  rows: ResultEntry[];
  language: Language;
  whiteSide: WhiteSide;
}) {
  const text = UI_TEXT[language];
  const female = rows.filter((row) => row.sex === "Female");
  const male = rows.filter((row) => row.sex === "Male");
  return (
    <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
      <SexResultGroup
        title={text.parentResult.male}
        icon={
          <GenderMale
            aria-hidden="true"
            className="h-4 w-4 text-sky-700"
            weight="duotone"
          />
        }
        accentClass="bg-sky-50 text-sky-800"
        rows={male}
        language={language}
        whiteSide={whiteSide}
      />
      <SexResultGroup
        title={text.parentResult.female}
        icon={
          <GenderFemale
            aria-hidden="true"
            className="h-4 w-4 text-pink-700"
            weight="duotone"
          />
        }
        accentClass="bg-pink-50 text-pink-800"
        rows={female}
        language={language}
        whiteSide={whiteSide}
      />
    </div>
  );
}

// carrier_exploration の 1 シナリオ。通常結果とは別枠で表示する。
function CarrierScenario({
  scenario,
  language,
}: {
  scenario: CarrierScenarioEntry;
  language: Language;
}) {
  const text = UI_TEXT[language];
  const assumed = Object.entries(scenario.assumed_carriers);
  return (
    <div className="rounded-md border border-amber-200 bg-amber-50 p-4">
      <h4 className="text-sm font-semibold text-amber-900">{scenario.label}</h4>
      <p className="mt-1 text-xs text-amber-700">
        {text.parentResult.basis}: {scenario.probability_basis}
        {scenario.prior_probability_applied
          ? ` / ${text.parentResult.priorApplied}`
          : ` / ${text.parentResult.conditional}`}
      </p>
      {assumed.length > 0 && (
        <ul className="mt-2 space-y-0.5 text-xs text-amber-800">
          {assumed.map(([parent, loci]) => (
            <li key={parent} className="flex flex-wrap items-center gap-1">
              <span className="font-medium">{parent}</span>:
              {Object.entries(loci).map(([locus, genotype]) => (
                <span key={`${parent}-${locus}`} className="inline-flex items-center gap-0.5">
                  <LocusChip locus={locus} />
                  <span>={genotype}</span>
                </span>
              ))}
            </li>
          ))}
        </ul>
      )}
      {scenario.new_colors.length > 0 && (
        <p className="mt-2 text-xs text-amber-800">
          {text.parentResult.newCoats}: {scenario.new_colors.join(", ")}
        </p>
      )}
      <div className="mt-3">
        {/* carrier_exploration は下の色を明示した正確計算のため AOC は出ない。導線は不要。 */}
        <SexSplitResults rows={scenario.results} language={language} whiteSide="none" />
      </div>
    </div>
  );
}

// 遺伝子座 (シナリオ) 単位でまとめた条件付きカラー。同一 scenario の色系統グループを統合する。
// colors は 基本色名 → 出得る性別集合 (バッジ枠線で♂♀を示すため)。
type LocusConditionalGroup = {
  scenario: string;
  reverseLabel: string;
  loci: string[];
  colors: Map<string, Set<string>>;
  pct: number;
};

// ♂♀の識別色 (結果カードの sky=♂ / pink=♀ に対応)。
const SEX_MALE_COLOR = "#38bdf8"; // sky-400
const SEX_FEMALE_COLOR = "#f472b6"; // pink-400

// 条件付きカラーの1バッジ。バッジ全面を毛色そのもの (下地→先端のレイヤー) で塗り、色名を重ねる。
// 枠線は出得る性別で色分けする (♂=sky / ♀=pink / 両方=左右で分割)。枠線は角丸を保つため外側の
// 塗りパディングで表現し、内側に毛色バッジを重ねる。任意の色/グラデでも読めるよう暗幕＋白文字＋影。
function ConditionalColorBadge({
  color,
  sexes,
}: {
  color: string;
  sexes: string[];
}) {
  const hasMale = sexes.includes("Male");
  const hasFemale = sexes.includes("Female");
  const borderBackground =
    hasMale && hasFemale
      ? `linear-gradient(90deg, ${SEX_MALE_COLOR} 50%, ${SEX_FEMALE_COLOR} 50%)`
      : hasMale
        ? SEX_MALE_COLOR
        : hasFemale
          ? SEX_FEMALE_COLOR
          : "rgba(0,0,0,0.12)";
  // 性別は枠線色だけでなく、色以外の手段 (aria-label / title) でも伝える (色覚多様性・スクリーン
  // リーダー対応)。♂=Male / ♀=Female。
  const sexLabel =
    hasMale && hasFemale
      ? "♂♀ Male & Female"
      : hasMale
        ? "♂ Male"
        : hasFemale
          ? "♀ Female"
          : "";
  const badgeLabel = sexLabel ? `${color} — ${sexLabel}` : color;
  return (
    <span
      className="inline-flex rounded-full p-[2px] shadow-sm"
      style={{ background: borderBackground }}
      title={badgeLabel}
      aria-label={badgeLabel}
    >
      <span
        className="inline-flex items-center rounded-full px-2 py-0.5 text-xs font-semibold"
        style={{
          // 純白は眩しいので気持ちだけ落とす (白さは保つ)。
          color: "rgba(255,255,255,0.97)",
          background: `linear-gradient(rgba(0,0,0,0.18) 0%, rgba(0,0,0,0.45) 100%), ${coatSwatchBackground(color)}`,
          // 影はオフセット無しの対称の縁取り (下方向オフセットは残像に見える)。ただし濃い影は細い
          // 文字に食い込んで白を鈍らせるため、1枚・軽めにして白を前に出す。
          textShadow: "0 0 1.5px rgba(0,0,0,0.7)",
          // 文字をグレースケールAAで描かせ、色つき背景での縁の色フリンジ (正面でのチラつき) を防ぐ。
          transform: "translateZ(0)",
          WebkitFontSmoothing: "antialiased",
          MozOsxFontSmoothing: "grayscale",
        }}
      >
        {color}
      </span>
    </span>
  );
}

// 「If This Color Appears」セクション。隠れキャリアを仮定した場合にのみ出る条件付きカラーを、
// 確定色 (メイン結果) とは分離して表示する。グルーピングは色系統ではなく「遺伝子座 (どの隠れキャリア
// が原因か)」単位にし、座位アイコンと色見本バッジを横並びに置く (色は毛色そのものを swatch で表現)。
function ConditionalColorSection({
  groups,
  language,
}: {
  groups: ConditionalColorGroup[];
  language: Language;
}) {
  const text = UI_TEXT[language];
  // デフォルトで開いておき、確定色と一緒に一覧で見えるようにする (畳みは任意で残す)。
  const [open, setOpen] = useState(true);

  // 遺伝子座 (scenario) 単位に統合する。色系統グループを潰し、原因座位と色を1カードにまとめる。
  const byScenario = new Map<string, LocusConditionalGroup>();
  for (const group of groups) {
    const loci = [
      ...new Set(
        Object.values(group.assumed_carriers).flatMap((genotypes) =>
          Object.keys(genotypes),
        ),
      ),
    ];
    const entry =
      byScenario.get(group.scenario) ??
      ({
        scenario: group.scenario,
        reverseLabel: group.reverse_inference_label,
        loci,
        colors: new Map<string, Set<string>>(),
        pct: 0,
      } satisfies LocusConditionalGroup);
    // 「もしこの色が出たら」では白斑 (-White / -White Van) は出さず基本色に集約する
    // (白斑は伝わるうえ、有無でバッジ幅が変わり同じ割合が違って見えるのを避ける)。
    // 併せて 基本色ごとに出得る性別を集約する (枠線の♂♀表示に使う)。
    for (const color of group.colors) {
      const base = splitWhite(color).base;
      const sexes = entry.colors.get(base) ?? new Set<string>();
      for (const sex of group.color_sexes?.[color] ?? []) sexes.add(sex);
      entry.colors.set(base, sexes);
    }
    entry.pct += group.conditional_probability_pct;
    byScenario.set(group.scenario, entry);
  }
  const locusGroups = [...byScenario.values()].sort((a, b) => b.pct - a.pct);

  return (
    <section className="rounded-md border border-amber-200 bg-amber-50/60">
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        className="flex w-full items-center justify-between gap-2 px-4 py-3 text-left"
        aria-expanded={open}
      >
        <span className="min-w-0">
          <span className="text-base font-semibold text-amber-900">
            {text.parentResult.conditionalTitle}
          </span>
          <span className="mt-0.5 block text-xs font-normal text-amber-700">
            {text.parentResult.conditionalHint}
          </span>
        </span>
        <span className="shrink-0 text-xs font-medium text-amber-700">
          {open ? text.parentResult.close : text.parentResult.conditionalOpen}
        </span>
      </button>
      {open && (
        <div className="space-y-3 px-4 pb-4">
          {locusGroups.map((group) => (
            <div
              key={group.scenario}
              className="rounded-md border border-amber-200 bg-white/70 p-3"
            >
              {/* 座位アイコン + 色見本バッジを横並び (原因の遺伝子座と、出る色) */}
              <div className="flex items-start justify-between gap-2">
                <div className="flex min-w-0 flex-wrap items-center gap-1.5">
                  {group.loci.map((locus) => (
                    <LocusChip key={locus} locus={locus} />
                  ))}
                  {[...group.colors.entries()].map(([color, sexes]) => (
                    <ConditionalColorBadge
                      key={color}
                      color={color}
                      sexes={[...sexes]}
                    />
                  ))}
                </div>
                <span className="shrink-0 text-xs tabular-nums text-amber-700">
                  {text.parentResult.conditionalMaxPct}
                  {formatPctInt(group.pct)}
                </span>
              </div>
              {/* 説明文 (どの遺伝子座がどう確定するか) */}
              <p className="mt-1.5 text-xs leading-relaxed text-amber-800">
                {group.reverseLabel}
              </p>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}

export function ResultView({
  data,
  language,
}: {
  data: CalculationResponse;
  language: Language;
}) {
  const text = UI_TEXT[language];
  const { diagnostics, parameters } = data;
  const carrierScenarios = data.carrier_exploration_results ?? [];
  // 入力 (親色 / 猫種 / モード) が変わったら結果カードを remount し、
  // 展開状態 (詳細を見る) を初期 (折りたたみ) に戻す。
  const resultsKey = `${parameters.sire_color}|${parameters.dam_color}|${parameters.breed ?? ""}|${parameters.mode}`;
  // AOC 行の導線 (どちらの親が White か) を判定する。AOC は White 親のときのみ出る。
  const whiteSide = whiteSideOf(parameters.sire_color, parameters.dam_color);
  // 展開/固定どちらにも出ない座位 (O=オレンジ・S=白斑・W=優性白・Sp 等) は
  // チップが描画されないため、解説を読めるよう「その他」行で補完する。
  const shownLoci = new Set([
    ...diagnostics.opened_loci,
    ...diagnostics.closed_loci,
  ]);
  const otherLoci = Object.keys(LOCUS_GLOSSARY).filter(
    (locus) => !shownLoci.has(locus),
  );
  return (
    <div className="space-y-6">
      {/* 「予測結果」は枠線上に乗るフローティングラベル (入力欄の FloatingField と同じ作法)。 */}
      <section className="relative rounded-lg border border-slate-300 bg-white px-4 pb-4 pt-5 shadow-sm">
        <h2 className="absolute -top-0 left-3 z-[1] -translate-y-1/2 bg-white px-1 text-[11px] font-semibold leading-4 text-slate-600">
          {text.parentResult.title}
        </h2>
        <span className="absolute -top-0 right-3 z-[1] -translate-y-1/2 rounded bg-white px-1 text-[11px] leading-4 text-slate-500">
          {text.parentResult.mode}: {data.mode}
        </span>
        {/* 確定カラー (基本確定事項) = オス / メス。すぐ下に条件付き (If…) を並べる。 */}
        <div>
          <h3 className="mb-2 text-sm font-semibold text-slate-600">
            {text.parentResult.confirmedTitle}
          </h3>
          <SexSplitResults
            key={resultsKey}
            rows={data.confirmed_results ?? data.results}
            language={language}
            whiteSide={whiteSide}
          />
        </div>
        {/* 「もしこの色が出たら」= オス・メス(確定色)のすぐ下にドッキングし、
            デフォルト展開で一覧できるようにする (normal かつ条件付きカラー群があるときだけ)。 */}
        {data.mode === "normal" && data.conditional_color_groups.length > 0 && (
          <div className="mt-3">
            <ConditionalColorSection
              groups={data.conditional_color_groups}
              language={language}
            />
          </div>
        )}
        {/* 入力色が子に出ない場合の注意書き → もし出たら の下、通常モード注記の上。 */}
        <ParentColorNotes notes={data.parent_color_notes} language={language} />
        {data.mode === "normal" && <NormalModeNote language={language} />}
      </section>

      <section className="rounded-md bg-slate-100 p-4 text-sm">
        <h3 className="font-semibold text-slate-700">
          {text.parentResult.geneticsTitle}
        </h3>
        <p className="mt-0.5 text-xs text-slate-400">
          {text.parentResult.geneticsDescription}
        </p>
        <dl className="mt-2 grid grid-cols-1 gap-y-1 sm:grid-cols-2">
          <dt className="text-slate-500">{text.parentResult.openedLoci}</dt>
          <dd className="flex flex-wrap items-center gap-1">
            {diagnostics.opened_loci.length > 0
              ? diagnostics.opened_loci.map((locus) => (
                  <LocusChip key={locus} locus={locus} />
                ))
              : text.parentResult.none}
          </dd>
          <dt className="text-slate-500">{text.parentResult.closedLoci}</dt>
          <dd className="flex flex-wrap items-center gap-1">
            {diagnostics.closed_loci.length > 0
              ? diagnostics.closed_loci.map((locus) => (
                  <LocusChip key={locus} locus={locus} />
                ))
              : text.parentResult.none}
          </dd>
          {otherLoci.length > 0 && (
            <>
              <dt className="text-slate-500">{text.parentResult.otherLoci}</dt>
              <dd className="flex flex-wrap items-center gap-1">
                {otherLoci.map((locus) => (
                  <LocusChip key={locus} locus={locus} />
                ))}
              </dd>
            </>
          )}
          <dt className="text-slate-500">
            {text.parentResult.unmatchedProbability}
          </dt>
          <dd className="tabular-nums">
            {formatPct(diagnostics.unmatched_probability)} (
            {diagnostics.unmatched_genotype_count} {text.parentResult.genotypeCount})
          </dd>
        </dl>
        {diagnostics.assumptions.length > 0 && (
          <div className="mt-2">
            <p className="text-slate-500">{text.parentResult.assumptions}</p>
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
            {text.parentResult.carrierScenarioTitle}
          </h3>
          {carrierScenarios.map((scenario) => (
            <CarrierScenario
              key={`${resultsKey}-${scenario.scenario}`}
              scenario={scenario}
              language={language}
            />
          ))}
        </section>
      )}
    </div>
  );
}
