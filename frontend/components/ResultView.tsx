"use client";

import { GenderFemale, GenderMale } from "@phosphor-icons/react";
import { useEffect, useId, useRef, useState, type ReactNode } from "react";
import type {
  CalculationResponse,
  ConditionalColorGroup,
  ParentColorNote,
  ResultEntry,
} from "@/lib/schema";
import { UI_TEXT, type Language } from "@/lib/i18n";
import { LocusChip } from "./LocusChip";
import { LOCUS_GLOSSARY } from "@/lib/lociGlossary";
import { coatSwatchBackground } from "@/lib/coatColorSwatch";

// レポートの配色トークン (--r-*) は globals.css で light/dark 両対応に定義している
// (ResultView 内では var(--r-*) を直接参照する)。

// 1%未満を集約する閾値。ユーザー指定 (低確率は畳んで一覧性を上げる)。
const LOW_PCT_THRESHOLD = 1;

// --- 確率整形 ---
function formatPct(value: number): string {
  return `${value.toFixed(1)}%`;
}

// 結果表示用: 0 超で四捨五入が 0 になる微小値は "<1%"。
function formatPctInt(value: number): string {
  if (value <= 0) return "0%";
  const rounded = Math.round(value);
  return rounded === 0 ? "<1%" : `${rounded}%`;
}

// AOC (Any Other Color) はどちらの親が White かで導線文言を切り替える。
type WhiteSide = "sire" | "dam" | "both" | "none";

function whiteSideOf(sireColor: string, damColor: string): WhiteSide {
  const isWhite = (color: string) => color.trim().toLowerCase() === "white";
  const sire = isWhite(sireColor);
  const dam = isWhite(damColor);
  if (sire && dam) return "both";
  if (sire) return "sire";
  if (dam) return "dam";
  return "none";
}

// 白斑サフィックス。長い順に判定する ("-White Van" を "-White" より先に)。
const WHITE_SUFFIXES = ["-White Van", "-White"] as const;

type WhitePortion = { label: string; pct: number };
type ColorGroup = { base: string; total: number; whites: WhitePortion[] };

// 色名から白斑サフィックスを剥がし、ベース色と白斑ラベルに分ける。
function splitWhite(color: string): { base: string; whiteLabel: string | null } {
  for (const suffix of WHITE_SUFFIXES) {
    if (color.endsWith(suffix)) {
      return { base: color.slice(0, color.length - suffix.length), whiteLabel: suffix };
    }
  }
  return { base: color, whiteLabel: null };
}

// 結果をベース色でまとめる。白斑あり (-White / -White Van) は副次内訳として保持する。
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

// 毛色の色見本。色系統の近似ではなく「その毛色そのもの」を視覚化する補助。
function Swatch({ color, size = 16 }: { color: string; size?: number }) {
  return (
    <span
      aria-hidden="true"
      className="inline-block shrink-0"
      style={{
        width: size,
        height: size,
        borderRadius: Math.max(3, Math.round(size * 0.28)),
        background: coatSwatchBackground(color),
        boxShadow: "inset 0 0 0 1px rgba(239,231,216,0.24)",
      }}
    />
  );
}

// セクション見出し (色付きの丸 + ラベル + 補足)。
// <button> や <span> の子として置くため、ブロック要素 (<p>) ではなくインラインの <span> を返す。
function SectionLabel({
  tick,
  children,
}: {
  tick: string;
  children: ReactNode;
}) {
  return (
    <span
      className="flex items-center gap-2 text-[11px] font-bold uppercase tracking-wider"
      style={{ color: tick }}
    >
      <span
        aria-hidden="true"
        className="h-2 w-2 shrink-0 rounded-[2px]"
        style={{ background: tick }}
      />
      {children}
    </span>
  );
}

// ♂/♀ の視覚記号 + スクリーンリーダー向けの性別テキスト (記号は aria-hidden なので
// sr-only テキストで性別を必ず読み上げ可能にする)。
// 性別の並び順キー: Male → Female。それ以外 (想定外の文字列) は末尾へ回す。
function sexRank(sex: string): number {
  return sex === "Male" ? 0 : sex === "Female" ? 1 : 9;
}

function SexMark({ sex, language }: { sex: string; language: Language }) {
  const text = UI_TEXT[language];
  // 想定外の性別文字列では何も描画しない (誤って Female 表示へ倒れるのを防ぐ)。
  if (sex !== "Male" && sex !== "Female") return null;
  const isMale = sex === "Male";
  return (
    <>
      <span
        aria-hidden="true"
        className="text-xs font-bold"
        style={{ color: isMale ? "var(--r-male)" : "var(--r-female)" }}
      >
        {isMale ? "♂" : "♀"}
      </span>
      <span className="sr-only">
        {isMale ? text.parentResult.male : text.parentResult.female}
      </span>
    </>
  );
}

// 毛色チップ: スウォッチ + ♂♀記号 + 色名 (+ 任意で確率)。確定色/推定色で共通に使う。
// -White (白斑) はベース色に合算せず、色名とスウォッチの白斑ウェッジでそのまま見せる。
function ColorChip({
  color,
  sexes,
  pct,
  language,
}: {
  color: string;
  sexes: string[];
  pct?: number;
  language: Language;
}) {
  // Male/Female のみに絞り、Male → Female の順に並べる (想定外値を除外・順序固定)。
  const marks = sexes
    .filter((sex) => sex === "Male" || sex === "Female")
    .sort((a, b) => sexRank(a) - sexRank(b));
  return (
    <span
      className="inline-flex items-center gap-1.5 rounded-lg px-2 py-1 text-xs"
      style={{ background: "var(--r-surface-2)", color: "var(--r-ink)" }}
    >
      <Swatch color={color} size={16} />
      {marks.map((sex) => (
        <SexMark key={sex} sex={sex} language={language} />
      ))}
      <span className="font-medium">{color}</span>
      {pct != null && (
        <span style={{ color: "var(--r-muted)" }} className="tabular-nums">
          {formatPctInt(pct)}
        </span>
      )}
    </span>
  );
}

// --- 確定色 (confirmed_results): 保因に依らず必ず出る色。チップで一覧する。 ---
// AOC は優性白由来で confirmed_results には入らない (White は確定色が空) ため、AocInfo は
// 全分布側のみに置く (確定色に置くとボタンが重複する)。
function ConfirmedColors({
  rows,
  language,
}: {
  rows: ResultEntry[];
  language: Language;
}) {
  const text = UI_TEXT[language];
  // -White を合算せず各色をそのままチップ化する (白斑を隠さない)。オス→メス、確率降順。
  const sorted = [...rows].sort(
    (a, b) => sexRank(a.sex) - sexRank(b.sex) || b.probability_pct - a.probability_pct,
  );
  return (
    <div
      className="flex flex-col gap-2 rounded-xl p-3"
      style={{
        background: "var(--r-confirmed-bg)",
        border: "1px solid color-mix(in srgb, var(--r-confirmed) 26%, transparent)",
      }}
    >
      <SectionLabel tick="var(--r-confirmed)">
        {text.parentResult.confirmedTitle}
      </SectionLabel>
      <div className="flex flex-wrap gap-1.5">
        {sorted.map((row) => (
          <ColorChip
            key={`${row.sex}-${row.color}`}
            color={row.color}
            sexes={[row.sex]}
            pct={row.probability_pct}
            language={language}
          />
        ))}
      </div>
    </div>
  );
}

// --- 全分布 (results): 1性別ぶんの周辺確率。スウォッチ + 確率バー。<1% は集約。 ---
function SexDistribution({
  title,
  sex,
  icon,
  rows,
  whiteSide,
  language,
}: {
  title: string;
  sex: "Male" | "Female";
  icon: ReactNode;
  rows: ResultEntry[];
  whiteSide: WhiteSide;
  language: Language;
}) {
  const text = UI_TEXT[language];
  const [showLow, setShowLow] = useState(false);
  const groups = groupByBase(rows);
  const total = rows.reduce((sum, row) => sum + row.probability_pct, 0);
  const max = Math.max(...groups.map((group) => group.total), 1);
  const main = groups.filter((group) => group.total >= LOW_PCT_THRESHOLD);
  const low = groups.filter((group) => group.total < LOW_PCT_THRESHOLD);
  const tint = sex === "Male" ? "var(--r-male)" : "var(--r-female)";

  const renderRow = (group: ColorGroup, dim: boolean) => (
    <li key={group.base} className="py-[3px]">
      <div className="flex items-center gap-2">
        <Swatch color={group.base} size={14} />
        <span
          className="min-w-0 flex-1 truncate text-xs"
          style={{ color: dim ? "var(--r-muted)" : "var(--r-ink)" }}
          title={group.base}
        >
          {group.base}
          {group.base === "AOC" && (
            <AocInfo whiteSide={whiteSide} language={language} />
          )}
        </span>
        <span
          className="shrink-0 tabular-nums text-[11px]"
          style={{ color: dim ? "var(--r-muted)" : "var(--r-ink-soft)" }}
        >
          {formatPctInt(group.total)}
        </span>
      </div>
      {!dim && (
        <div
          className="mt-[3px] h-[3px] rounded"
          style={{
            width: `${Math.max(2, (group.total / max) * 100)}%`,
            background: tint,
            opacity: 0.8,
          }}
        />
      )}
      {/* 白斑レベル (-White / -White Van) の内訳。合算で消えないよう副次行で残す。 */}
      {group.whites.length > 0 && (
        <div className="mt-0.5 flex flex-col gap-0.5 pl-6">
          {group.whites.map((white) => (
            <div
              key={white.label}
              className="flex items-center justify-between gap-2 text-[10px]"
              style={{ color: "var(--r-muted)" }}
            >
              <span>└ {white.label}</span>
              <span className="shrink-0 tabular-nums">{formatPctInt(white.pct)}</span>
            </div>
          ))}
        </div>
      )}
    </li>
  );

  return (
    <div>
      <h4
        className="mb-1.5 flex items-center gap-1.5 border-b pb-1 text-xs font-bold"
        style={{ color: "var(--r-ink)", borderColor: "var(--r-hairline-soft)" }}
      >
        {icon}
        {title}
        <span
          className="ml-auto text-[10px] font-medium tabular-nums"
          style={{ color: "var(--r-muted)" }}
        >
          {text.parentResult.totalApprox}
          {formatPctInt(total)}
        </span>
      </h4>
      {groups.length === 0 ? (
        <p className="py-2 text-xs" style={{ color: "var(--r-muted)" }}>
          {text.parentResult.noPhenotype}
        </p>
      ) : (
        <ul>
          {main.map((group) => renderRow(group, false))}
          {low.length > 0 && (
            <li className="pt-0.5">
              <button
                type="button"
                onClick={() => setShowLow((value) => !value)}
                aria-expanded={showLow}
                className="text-[11px] font-medium"
                style={{ color: "var(--r-muted)" }}
              >
                {showLow
                  ? text.parentResult.close
                  : `${text.parentResult.belowOnePct} · ${low.length}${
                      language === "ja" ? "色" : ""
                    }`}
              </button>
              {showLow && <ul className="mt-1">{low.map((group) => renderRow(group, true))}</ul>}
            </li>
          )}
        </ul>
      )}
    </div>
  );
}

function FullDistribution({
  rows,
  whiteSide,
  language,
  defaultOpen,
}: {
  rows: ResultEntry[];
  whiteSide: WhiteSide;
  language: Language;
  defaultOpen: boolean;
}) {
  const text = UI_TEXT[language];
  // 確定色があるときは折りたたみ (確定色/推定色をまず見せる)。確定色が無いケース
  // (優性白など) は肝心の色が隠れないよう既定で開く。
  const [open, setOpen] = useState(defaultOpen);
  const male = rows.filter((row) => row.sex === "Male");
  const female = rows.filter((row) => row.sex === "Female");
  return (
    <div
      className="rounded-xl p-3"
      style={{ background: "var(--r-inset)", border: "1px solid var(--r-hairline)" }}
    >
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        aria-expanded={open}
        className="flex w-full items-center gap-2 text-left"
      >
        <SectionLabel tick="var(--r-accent)">
          {text.parentResult.distributionTitle}
        </SectionLabel>
        <span
          aria-hidden="true"
          className="ml-auto text-[10px] transition-transform"
          style={{ color: "var(--r-muted)", transform: open ? "rotate(90deg)" : "none" }}
        >
          ▶
        </span>
      </button>
      {open && (
        <div className="mt-3 grid grid-cols-1 gap-x-5 gap-y-3 sm:grid-cols-2">
          <SexDistribution
            title={text.parentResult.male}
            sex="Male"
            icon={
              <GenderMale aria-hidden="true" className="h-3.5 w-3.5" style={{ color: "var(--r-male)" }} weight="duotone" />
            }
            rows={male}
            whiteSide={whiteSide}
            language={language}
          />
          <SexDistribution
            title={text.parentResult.female}
            sex="Female"
            icon={
              <GenderFemale aria-hidden="true" className="h-3.5 w-3.5" style={{ color: "var(--r-female)" }} weight="duotone" />
            }
            rows={female}
            whiteSide={whiteSide}
            language={language}
          />
        </div>
      )}
    </div>
  );
}

// --- 推定色 (conditional_color_groups): 隠れキャリア仮定時のみ出る色。 ---
// 遺伝子座アイコン (D/A 等) は分かりにくいため、「父 D/d」のようなキャリア推定バッジで表示する。
type CarrierConditionalGroup = {
  scenario: string;
  reverseLabel: string;
  who: string; // "sire" / "dam" / "both"
  geno: string; // 例 "D/d"
  colors: Map<string, Set<string>>;
  pct: number;
};

// assumed_carriers から「どちらの親が・どの遺伝子型の保因か」を取り出す。
// キー順に依存しないよう sire/dam の有無を明示チェックし、geno は全値から取り出す。
function carrierHypothesis(assumed: Record<string, Record<string, string>>): {
  who: string;
  geno: string;
} {
  const keys = Object.keys(assumed);
  const hasSire = keys.includes("sire");
  const hasDam = keys.includes("dam");
  const who = hasSire && hasDam ? "both" : hasDam ? "dam" : "sire";
  // 1シナリオは単座位なので全親・全座位の値は同一。最初の非空値を取る (順序非依存)。
  const geno =
    Object.values(assumed)
      .flatMap((loci) => Object.values(loci))
      .find((value) => value) ?? "";
  return { who, geno };
}

function carrierWhoLabel(who: string, language: Language): string {
  const text = UI_TEXT[language];
  if (who === "both") return text.parentResult.carrierBoth;
  if (who === "dam") return text.parentResult.carrierDam;
  return text.parentResult.carrierSire;
}

function ConditionalColorSection({
  groups,
  language,
}: {
  groups: ConditionalColorGroup[];
  language: Language;
}) {
  const text = UI_TEXT[language];
  const [open, setOpen] = useState(true);

  const byScenario = new Map<string, CarrierConditionalGroup>();
  for (const group of groups) {
    const { who, geno } = carrierHypothesis(group.assumed_carriers);
    const entry =
      byScenario.get(group.scenario) ??
      ({
        scenario: group.scenario,
        reverseLabel: group.reverse_inference_label,
        who,
        geno,
        colors: new Map<string, Set<string>>(),
        pct: 0,
      } satisfies CarrierConditionalGroup);
    // -White を合算せず、色名そのまま (白斑バリアントを別個に) 保持する。
    for (const color of group.colors) {
      const sexes = entry.colors.get(color) ?? new Set<string>();
      for (const sex of group.color_sexes?.[color] ?? []) sexes.add(sex);
      entry.colors.set(color, sexes);
    }
    entry.pct += group.conditional_probability_pct;
    byScenario.set(group.scenario, entry);
  }
  const locusGroups = [...byScenario.values()].sort((a, b) => b.pct - a.pct);

  return (
    <section
      className="rounded-xl"
      style={{
        background: "var(--r-conditional-bg)",
        border: "1px solid color-mix(in srgb, var(--r-conditional) 26%, transparent)",
      }}
    >
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        className="flex w-full items-start justify-between gap-2 px-3 py-3 text-left"
        aria-expanded={open}
      >
        <span className="min-w-0">
          <SectionLabel tick="var(--r-conditional)">
            {text.parentResult.conditionalTitle}
          </SectionLabel>
          <span className="mt-1 block text-[11px]" style={{ color: "var(--r-muted)" }}>
            {text.parentResult.conditionalHint}
          </span>
        </span>
        <span className="shrink-0 text-[11px] font-medium" style={{ color: "var(--r-conditional)" }}>
          {open ? text.parentResult.close : text.parentResult.conditionalOpen}
        </span>
      </button>
      {open && (
        <div className="space-y-2 px-3 pb-3">
          {locusGroups.map((group) => (
            <div
              key={group.scenario}
              className="rounded-lg p-2.5"
              style={{ background: "var(--r-surface)", border: "1px solid var(--r-hairline)" }}
            >
              {/* ヘッダー: キャリア推定バッジ (例「父 D/d」) + 最大確率。 */}
              <div className="flex items-center justify-between gap-2">
                <span
                  className="inline-flex items-center gap-1 rounded-md px-2 py-0.5 text-[11px] font-bold"
                  style={{
                    color: "var(--r-conditional)",
                    background: "color-mix(in srgb, var(--r-conditional) 14%, transparent)",
                    border: "1px solid color-mix(in srgb, var(--r-conditional) 34%, transparent)",
                  }}
                >
                  {carrierWhoLabel(group.who, language)}
                  <span className="tabular-nums">{group.geno}</span>
                </span>
                <span className="shrink-0 text-[11px] tabular-nums" style={{ color: "var(--r-conditional)" }}>
                  {text.parentResult.conditionalMaxPct}
                  {formatPctInt(group.pct)}
                </span>
              </div>
              {/* 出得る色柄 (確定色と同じチップ表現)。 */}
              <div className="mt-2 flex flex-wrap items-center gap-1.5">
                {[...group.colors.entries()].map(([color, sexes]) => (
                  <ColorChip
                    key={color}
                    color={color}
                    sexes={[...sexes]}
                    language={language}
                  />
                ))}
              </div>
              <p className="mt-1.5 text-[11px] leading-relaxed" style={{ color: "var(--r-ink-soft)" }}>
                {group.reverseLabel}
              </p>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}

// --- 補助情報 (プロトタイプに無いが有用なため体裁を合わせて残す) ---

// AOC の説明ポップオーバー (§2.3)。フォーカス/ホバーで開く。
function AocInfo({ whiteSide, language }: { whiteSide: WhiteSide; language: Language }) {
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
        onClick={() => setOpen(true)}
        onFocus={() => setOpen(true)}
        onBlur={() => setOpen(false)}
        className="flex h-4 w-4 cursor-help items-center justify-center rounded-full text-[10px] leading-none"
        style={{ border: "1px solid var(--r-hairline)", color: "var(--r-muted)" }}
        aria-expanded={open}
        aria-describedby={tooltipId}
        aria-label={text.parentResult.aocAria}
      >
        ?
      </button>
      <span
        role="tooltip"
        id={tooltipId}
        className={`absolute left-0 top-full z-20 mt-1 w-64 max-w-[80vw] rounded-md p-2 text-left text-xs font-normal shadow-lg ${
          open ? "block" : "hidden"
        }`}
        style={{
          background: "var(--r-surface-2)",
          border: "1px solid var(--r-hairline)",
          color: "var(--r-ink-soft)",
        }}
      >
        <span className="block font-semibold" style={{ color: "var(--r-ink)" }}>
          {text.parentResult.aocTitle}
        </span>
        <span className="mt-0.5 block leading-relaxed">{text.parentResult.aocBody}</span>
        <span className="mt-1 block text-[11px]" style={{ color: "var(--r-muted)" }}>
          {hint} {text.parentResult.aocMore}
        </span>
      </span>
    </span>
  );
}

// 入力した親色が子に出ないときの注釈。
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
    <div className="flex flex-col gap-2">
      {notes.map((note) => {
        const parent = note.parent === "sire" ? text.parentResult.sire : text.parentResult.dam;
        const other = note.parent === "sire" ? text.parentResult.dam : text.parentResult.sire;
        return (
          <div
            key={note.parent}
            className="rounded-lg p-3 text-xs leading-relaxed"
            style={{
              background: "var(--r-conditional-bg)",
              border: "1px solid color-mix(in srgb, var(--r-conditional) 22%, transparent)",
              color: "var(--r-ink-soft)",
            }}
          >
            {language === "ja" ? (
              <>
                <span className="font-medium" style={{ color: "var(--r-ink)" }}>
                  {parent}の色柄「{note.color}」
                </span>
                はこの組み合わせでは子猫に出現しません。
                {note.blocked_factors.length > 0 && (
                  <>
                    {other}が次の劣性因子を持たないためです:{" "}
                    <span className="font-medium">{note.blocked_factors.join(" ・ ")}</span>。
                  </>
                )}
              </>
            ) : (
              <>
                <span className="font-medium" style={{ color: "var(--r-ink)" }}>
                  The {parent.toLowerCase()} coat &quot;{note.color}&quot;
                </span>{" "}
                does not appear in this combination.
                {note.blocked_factors.length > 0 && (
                  <>
                    {" "}
                    The {other.toLowerCase()} does not carry these recessive factors:{" "}
                    <span className="font-medium">{note.blocked_factors.join(", ")}</span>.
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
function NormalModeNote({ language }: { language: Language }) {
  const text = UI_TEXT[language];
  const [open, setOpen] = useState(false);
  return (
    <div
      className="rounded-lg p-3 text-xs"
      style={{ background: "var(--r-surface-2)", color: "var(--r-ink-soft)" }}
    >
      <div className="flex items-start justify-between gap-2">
        <p className="min-w-0">
          <span className="font-medium" style={{ color: "var(--r-ink)" }}>
            {text.parentResult.normalScopeTitle}
          </span>
          {" — "}
          {text.parentResult.normalScopeSummary}
        </p>
        <button
          type="button"
          onClick={() => setOpen((value) => !value)}
          className="shrink-0 rounded px-2 py-0.5 text-[11px] font-medium"
          style={{ color: "var(--r-muted)" }}
          aria-expanded={open}
        >
          {open ? text.parentResult.close : text.parentResult.normalScopeMore}
        </button>
      </div>
      {open && <p className="mt-2 leading-relaxed">{text.parentResult.normalScopeDetails}</p>}
    </div>
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
  // 入力が変わったら結果カードを remount して展開状態を初期化する。
  const resultsKey = `${parameters.sire_color}|${parameters.dam_color}|${parameters.breed ?? ""}|${parameters.mode}`;
  const whiteSide = whiteSideOf(parameters.sire_color, parameters.dam_color);
  const hasConfirmed = Boolean(data.confirmed_results && data.confirmed_results.length > 0);
  const shownLoci = new Set([...diagnostics.opened_loci, ...diagnostics.closed_loci]);
  const otherLoci = Object.keys(LOCUS_GLOSSARY).filter((locus) => !shownLoci.has(locus));

  return (
    // 外枠セクション (「予測結果」「モード」フローティングラベル付き) は撤去し、
    // 各サブセクションを直接並べてネストを浅く・横幅を活かす (モバイルの可読性改善)。
    <div key={resultsKey} className="flex flex-col gap-2.5">
      {/* ① 確定色 (normal モードで確定色があるときのみ。White は空なので出さない) */}
      {hasConfirmed && (
        <ConfirmedColors rows={data.confirmed_results ?? []} language={language} />
      )}

      {/* ② 全分布 (周辺確率)。確定色があるときは畳み、無いとき (White 等) は開く。 */}
      <FullDistribution
        rows={data.results}
        whiteSide={whiteSide}
        language={language}
        defaultOpen={!hasConfirmed}
      />

      {/* ③ 推定色 (両親キャリア推定) */}
      {data.mode === "normal" && data.conditional_color_groups.length > 0 && (
        <ConditionalColorSection groups={data.conditional_color_groups} language={language} />
      )}

      {/* 補助: 親色不在注釈 / 通常モード注記 */}
      <ParentColorNotes notes={data.parent_color_notes} language={language} />
      {data.mode === "normal" && <NormalModeNote language={language} />}

      {/* 遺伝子座の診断 (開いた/閉じた座位・未分類率・前提)。 */}
      <section
        className="rounded-xl p-3 text-sm"
        style={{ background: "var(--r-surface)", border: "1px solid var(--r-hairline)" }}
      >
        <h3 className="font-semibold" style={{ color: "var(--r-ink)" }}>
          {text.parentResult.geneticsTitle}
        </h3>
        <p className="mt-0.5 text-xs" style={{ color: "var(--r-muted)" }}>
          {text.parentResult.geneticsDescription}
        </p>
        <dl className="mt-2 grid grid-cols-1 gap-y-1 sm:grid-cols-2">
          <dt style={{ color: "var(--r-muted)" }}>{text.parentResult.openedLoci}</dt>
          <dd className="flex flex-wrap items-center gap-1">
            {diagnostics.opened_loci.length > 0
              ? diagnostics.opened_loci.map((locus) => <LocusChip key={locus} locus={locus} />)
              : text.parentResult.none}
          </dd>
          <dt style={{ color: "var(--r-muted)" }}>{text.parentResult.closedLoci}</dt>
          <dd className="flex flex-wrap items-center gap-1">
            {diagnostics.closed_loci.length > 0
              ? diagnostics.closed_loci.map((locus) => <LocusChip key={locus} locus={locus} />)
              : text.parentResult.none}
          </dd>
          {otherLoci.length > 0 && (
            <>
              <dt style={{ color: "var(--r-muted)" }}>{text.parentResult.otherLoci}</dt>
              <dd className="flex flex-wrap items-center gap-1">
                {otherLoci.map((locus) => (
                  <LocusChip key={locus} locus={locus} />
                ))}
              </dd>
            </>
          )}
          <dt style={{ color: "var(--r-muted)" }}>{text.parentResult.unmatchedProbability}</dt>
          <dd className="tabular-nums" style={{ color: "var(--r-ink-soft)" }}>
            {formatPct(diagnostics.unmatched_probability)} ({diagnostics.unmatched_genotype_count}{" "}
            {text.parentResult.genotypeCount})
          </dd>
        </dl>
        {diagnostics.assumptions.length > 0 && (
          <div className="mt-2">
            <p style={{ color: "var(--r-muted)" }}>{text.parentResult.assumptions}</p>
            <ul className="ml-4 list-disc" style={{ color: "var(--r-ink-soft)" }}>
              {diagnostics.assumptions.map((assumption, index) => (
                <li key={index}>{assumption}</li>
              ))}
            </ul>
          </div>
        )}
      </section>
    </div>
  );
}
