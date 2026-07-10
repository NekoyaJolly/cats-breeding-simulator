"use client";

import { CaretRight, DotsSixVertical, GenderFemale, GenderMale, Star } from "@phosphor-icons/react";
import {
  useCallback,
  useEffect,
  useId,
  useRef,
  useState,
  type CSSProperties,
  type ReactNode,
} from "react";
import {
  DndContext,
  KeyboardSensor,
  PointerSensor,
  closestCenter,
  useSensor,
  useSensors,
  type DragEndEvent,
} from "@dnd-kit/core";
import {
  SortableContext,
  sortableKeyboardCoordinates,
  useSortable,
  verticalListSortingStrategy,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
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
import {
  DEFAULT_SECTION_ORDER,
  loadSectionOpen,
  loadSectionOrder,
  saveSectionOpen,
  saveSectionOrder,
  type SectionId,
} from "@/lib/resultSections";

// レポートの配色トークン (--r-*) は globals.css で light/dark 両対応に定義している
// (ResultView 内では var(--r-*) を直接参照する)。

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

// 統一アコーディオンセクション。全結果セクション共通のヘッダー (ドラッグハンドル + 色付き
// ティック + タイトル + シェブロン) を提供する。@dnd-kit で並び替え可能。
function AccordionSection({
  id,
  title,
  tick,
  open,
  onToggle,
  dragLabel,
  count,
  countLabel,
  children,
}: {
  id: SectionId;
  title: string;
  tick: string;
  open: boolean;
  onToggle: () => void;
  dragLabel: string;
  count?: number;
  countLabel?: string;
  children: ReactNode;
}) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } =
    useSortable({ id });
  // 開閉トグルと展開コンテンツを aria-controls / id で紐付ける (SR での領域追跡)。
  // region には見出し (titleId) を aria-labelledby で名付け、無名 region を避ける。
  const contentId = `result-section-${id}`;
  const titleId = `${contentId}-title`;
  const style: CSSProperties = {
    transform: CSS.Transform.toString(transform),
    transition,
    background: "var(--r-surface)",
    border: "1px solid var(--r-hairline)",
    opacity: isDragging ? 0.6 : 1,
    zIndex: isDragging ? 10 : undefined,
  };
  return (
    <section ref={setNodeRef} style={style} className="rounded-xl">
      <div className="flex items-center gap-1">
        {/* ドラッグハンドル (並び替え)。touch-none でモバイルのスクロール干渉を防ぐ。 */}
        <button
          type="button"
          {...attributes}
          {...listeners}
          aria-label={`${dragLabel}: ${title}`}
          className="flex h-9 w-7 shrink-0 cursor-grab touch-none items-center justify-center rounded active:cursor-grabbing"
          style={{ color: "var(--r-muted)" }}
        >
          <DotsSixVertical aria-hidden="true" className="h-4 w-4" weight="bold" />
        </button>
        {/* タイトル (クリックで展開/折りたたみ)。 */}
        <button
          type="button"
          onClick={onToggle}
          aria-expanded={open}
          aria-controls={open ? contentId : undefined}
          className="flex flex-1 items-center gap-2 py-2 pr-2.5 text-left"
        >
          <span
            aria-hidden="true"
            className="h-2 w-2 shrink-0 rounded-[2px]"
            style={{ background: tick }}
          />
          <span
            id={titleId}
            className="text-[11px] font-bold uppercase tracking-wider"
            style={{ color: tick }}
          >
            {title}
          </span>
          {/* 結果件数バッジ (トグル手前に右寄せ)。計算直後であることを示し、トグルの意味も立てる。 */}
          {count != null && (
            <span
              className="ml-auto shrink-0 rounded-full px-1.5 py-0.5 text-[10px] font-semibold tabular-nums"
              style={{ background: "var(--r-surface-2)", color: "var(--r-muted)" }}
              aria-label={countLabel}
            >
              {count}
            </span>
          )}
          <CaretRight
            aria-hidden="true"
            className={`${count != null ? "ml-1.5" : "ml-auto"} h-3.5 w-3.5 shrink-0 transition-transform`}
            weight="bold"
            style={{ color: "var(--r-muted)", transform: open ? "rotate(90deg)" : "none" }}
          />
        </button>
      </div>
      {open && (
        <div id={contentId} role="region" aria-labelledby={titleId} className="px-2.5 pb-2.5">
          {children}
        </div>
      )}
    </section>
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
  // ♂/♀ のテキストグリフはフォントのベースライン基準でスウォッチ/テキストより下に
  // 見えていた。SVG アイコン (viewBox 中央基準) にして確実に行内中央へ揃える。
  const Icon = isMale ? GenderMale : GenderFemale;
  return (
    <>
      <Icon
        aria-hidden="true"
        className="h-3.5 w-3.5 shrink-0"
        // 全分布ヘッダーの性別アイコンと表現を揃える (duotone)。
        weight="duotone"
        style={{ color: isMale ? "var(--r-male)" : "var(--r-female)" }}
      />
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

// --- 確定色 (confirmed_results): 保因に依らず必ず出る色。チップで一覧する (body のみ)。 ---
// AOC は優性白由来で confirmed_results には入らない (White は確定色が空) ため、AocInfo は
// 全分布側のみに置く。
function ConfirmedBody({
  rows,
  language,
}: {
  rows: ResultEntry[];
  language: Language;
}) {
  // -White を合算せず各色をそのままチップ化する (白斑を隠さない)。オス→メス、確率降順。
  const sorted = [...rows].sort(
    (a, b) => sexRank(a.sex) - sexRank(b.sex) || b.probability_pct - a.probability_pct,
  );
  return (
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
  );
}

// --- 全分布 (results): 1性別ぶんの周辺確率。スウォッチ + 確率バー。1%未満も集約しない。 ---
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
  const groups = groupByBase(rows);
  const total = rows.reduce((sum, row) => sum + row.probability_pct, 0);
  const tint = sex === "Male" ? "var(--r-male)" : "var(--r-female)";
  // この性別で最も出やすい色を強調する。確率最大値と一致する行 (同率トップは全て、
  // 単色ならその1色) を最有力として扱う。
  const maxTotal = groups.reduce((acc, group) => Math.max(acc, group.total), 0);

  // 1%未満も集約せず全色をそのまま行にする (微小確率でも「出得る色」を隠さない)。
  const renderRow = (group: ColorGroup) => {
    const isTop = maxTotal > 0 && group.total === maxTotal;
    return (
    <li key={group.base} className="py-[3px]">
      <div className="flex items-center gap-2">
        <Swatch color={group.base} size={14} />
        <span
          className={`min-w-0 flex-1 truncate text-xs ${isTop ? "font-semibold" : ""}`}
          style={{ color: "var(--r-ink)" }}
          title={group.base}
        >
          {group.base}
          {group.base === "AOC" && (
            <AocInfo whiteSide={whiteSide} language={language} />
          )}
        </span>
        <span
          className={`shrink-0 tabular-nums text-[11px] ${isTop ? "font-semibold" : ""}`}
          style={{ color: isTop ? "var(--r-ink)" : "var(--r-ink-soft)" }}
        >
          {formatPctInt(group.total)}
        </span>
        {/* この性別の最有力色に小さな星マーカー。名前を圧迫しないよう % の後ろに置く。
            記号は装飾なので aria-hidden、意味は sr-only テキストで補う。 */}
        {isTop && (
          <>
            <Star
              aria-hidden="true"
              weight="fill"
              className="h-3 w-3 shrink-0"
              style={{ color: tint }}
            />
            <span className="sr-only">{text.parentResult.mostLikely}</span>
          </>
        )}
      </div>
      {/* 確率メーター: 列内の最大値で正規化せず、絶対確率 (0〜100%) スケールでトラック上に
          描く。バー長がそのまま確率を表すので、〜35% が満杯 (右端) にならない。
          (数値ラベルは formatPctInt で丸め、バーは未丸めの group.total を使うため厳密一致
          ではないが、読み取り上のスケールは 0〜100%。) */}
      <div
        data-testid="dist-meter-track"
        role="meter"
        aria-valuemin={0}
        aria-valuemax={100}
        // valuenow は 0〜100 にクランプ (端数/誤差対策)。valuetext で表示と同じ文字列
        // (<1% 等) を読み上げ、丸めた数値との齟齬を防ぐ。
        aria-valuenow={Math.min(100, Math.max(0, Math.round(group.total)))}
        aria-valuetext={formatPctInt(group.total)}
        aria-label={`${title} ${group.base}`}
        className="mt-[3px] h-[3px] w-full overflow-hidden rounded"
        style={{ background: "var(--r-hairline-soft)" }}
      >
        <div
          data-testid="dist-meter-fill"
          className="h-full rounded"
          style={{
            // 幅は絶対確率そのもの。%下限はスケールを大きく歪めるので使わない。
            // 極小確率でも見えるよう最小幅を px で確保する (この 2px 分だけ極小確率は
            // 実際より僅かに長く見えるが、可視性優先の意図的なトレードオフ)。
            width: `${Math.min(100, group.total)}%`,
            minWidth: "2px",
            background: tint,
            // 最有力色はフィルを不透明にして視覚的に立たせる。
            opacity: isTop ? 1 : 0.85,
          }}
        />
      </div>
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
  };

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
        <ul>{groups.map((group) => renderRow(group))}</ul>
      )}
    </div>
  );
}

// 全分布 (results) の body。オス/メスの周辺確率を横並び (body のみ、トグル/枠は Accordion 側)。
function DistributionBody({
  rows,
  whiteSide,
  language,
}: {
  rows: ResultEntry[];
  whiteSide: WhiteSide;
  language: Language;
}) {
  const text = UI_TEXT[language];
  const male = rows.filter((row) => row.sex === "Male");
  const female = rows.filter((row) => row.sex === "Female");
  return (
    // HTML レポート同様、オス/メスを常に2カラムで水平に並べる (モバイルでも縦積みにしない)。
    // モバイルは gap を詰めて各列の横幅を確保する。
    <div className="grid grid-cols-2 gap-x-3 gap-y-3 sm:gap-x-5">
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
  );
}

// --- 推定色 (conditional_color_groups): 隠れキャリア仮定時のみ出る色。 ---
// 遺伝子座アイコン (D/A 等) は分かりにくいため、「父 D/d」のようなキャリア推定バッジで表示する。
type CarrierBadge = { who: string; geno: string };
type CarrierConditionalGroup = {
  scenario: string;
  reverseLabel: string;
  badges: CarrierBadge[];
  colors: Map<string, Set<string>>;
  pct: number;
};

// assumed_carriers から表示用のキャリア推定バッジを作る。父母が同一遺伝子型のときだけ「両親」に
// 集約し、異なる/片方のみのときは父・母を個別に表示する (キー順・座位数に依存しない)。
// 1親が複数座位を持つ場合は遺伝子型をまとめて表示する。
function carrierBadges(
  assumed: Record<string, Record<string, string>>,
  language: Language,
): CarrierBadge[] {
  const text = UI_TEXT[language];
  const genoOf = (loci: Record<string, string> | undefined): string =>
    Object.values(loci ?? {})
      .filter((value) => value)
      .join(", ");
  const sireGeno = genoOf(assumed.sire);
  const damGeno = genoOf(assumed.dam);
  if (sireGeno && damGeno && sireGeno === damGeno) {
    return [{ who: text.parentResult.carrierBoth, geno: sireGeno }];
  }
  const badges: CarrierBadge[] = [];
  if (sireGeno) badges.push({ who: text.parentResult.carrierSire, geno: sireGeno });
  if (damGeno) badges.push({ who: text.parentResult.carrierDam, geno: damGeno });
  return badges;
}

// 両親キャリア推定 (conditional_color_groups) の body。scenario ごとのカードを並べる (body のみ)。
function ConditionalBody({
  groups,
  language,
}: {
  groups: ConditionalColorGroup[];
  language: Language;
}) {
  const text = UI_TEXT[language];
  const byScenario = new Map<string, CarrierConditionalGroup>();
  for (const group of groups) {
    const entry =
      byScenario.get(group.scenario) ??
      ({
        scenario: group.scenario,
        reverseLabel: group.reverse_inference_label,
        badges: carrierBadges(group.assumed_carriers, language),
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
    <div className="flex flex-col gap-2">
      <p className="text-[11px]" style={{ color: "var(--r-muted)" }}>
        {text.parentResult.conditionalHint}
      </p>
      {locusGroups.map((group) => (
        <div
          key={group.scenario}
          className="rounded-lg p-2.5"
          style={{ background: "var(--r-inset)", border: "1px solid var(--r-hairline)" }}
        >
          {/* ヘッダー: キャリア推定バッジ (例「父 D/d」) + 最大確率。 */}
          <div className="flex items-start justify-between gap-2">
            <span className="flex flex-wrap items-center gap-1">
              {group.badges.map((badge) => (
                <span
                  key={`${badge.who}-${badge.geno}`}
                  data-testid="carrier-badge"
                  className="inline-flex items-center gap-1 rounded-md px-2 py-0.5 text-[11px] font-bold"
                  style={{
                    color: "var(--r-conditional)",
                    background: "color-mix(in srgb, var(--r-conditional) 14%, transparent)",
                    border: "1px solid color-mix(in srgb, var(--r-conditional) 34%, transparent)",
                  }}
                >
                  <span>{badge.who}</span>
                  <span className="tabular-nums">{badge.geno}</span>
                </span>
              ))}
            </span>
            <span className="shrink-0 text-[11px] tabular-nums" style={{ color: "var(--r-conditional)" }}>
              {text.parentResult.conditionalMaxPct}
              {formatPctInt(group.pct)}
            </span>
          </div>
          {/* 出得る色柄 (確定色と同じチップ表現)。 */}
          <div className="mt-2 flex flex-wrap items-center gap-1.5">
            {[...group.colors.entries()].map(([color, sexes]) => (
              <ColorChip key={color} color={color} sexes={[...sexes]} language={language} />
            ))}
          </div>
          <p className="mt-1.5 text-[11px] leading-relaxed" style={{ color: "var(--r-ink-soft)" }}>
            {group.reverseLabel}
          </p>
        </div>
      ))}
    </div>
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

// 通常モードの計算範囲を平易に説明する body。
function NormalNoteBody({ language }: { language: Language }) {
  const text = UI_TEXT[language];
  return (
    <div className="text-xs leading-relaxed" style={{ color: "var(--r-ink-soft)" }}>
      <p>{text.parentResult.normalScopeSummary}</p>
      <p className="mt-2">{text.parentResult.normalScopeDetails}</p>
    </div>
  );
}

// 遺伝子座の診断 body (開いた/閉じた座位・未分類率・前提)。
function GeneticsBody({
  diagnostics,
  otherLoci,
  language,
}: {
  diagnostics: CalculationResponse["diagnostics"];
  otherLoci: string[];
  language: Language;
}) {
  const text = UI_TEXT[language];
  return (
    <div className="text-sm">
      <p className="text-xs" style={{ color: "var(--r-muted)" }}>
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
    </div>
  );
}

type ResultSection = {
  title: string;
  tick: string;
  visible: boolean;
  content: ReactNode;
  // タイトル右 (トグル手前) に出す結果件数。計算直後であることを示す。未指定なら出さない。
  count?: number;
};

export function ResultView({
  data,
  language,
}: {
  data: CalculationResponse;
  language: Language;
}) {
  const text = UI_TEXT[language];
  const { diagnostics, parameters } = data;
  const whiteSide = whiteSideOf(parameters.sire_color, parameters.dam_color);
  const hasConfirmed = Boolean(data.confirmed_results && data.confirmed_results.length > 0);
  const shownLoci = new Set([...diagnostics.opened_loci, ...diagnostics.closed_loci]);
  const otherLoci = Object.keys(LOCUS_GLOSSARY).filter((locus) => !shownLoci.has(locus));

  // セクションタイトルに出す結果件数。確定=チップ数 / 全分布=異なる毛色数 / 推定=グループ数。
  // 全分布の件数は「異なるベース色数」なので、groupByBase の割り当て/ソートを介さず
  // splitWhite + Set で O(n) に数える (件数のためだけに ColorGroup を作らない)。
  const confirmedCount = data.confirmed_results?.length ?? 0;
  const distributionCount = new Set(data.results.map((row) => splitWhite(row.color).base)).size;
  const conditionalCount = data.conditional_color_groups.length;
  const countLabelOf = (n: number): string =>
    language === "ja" ? `${n}件` : `${n} item${n === 1 ? "" : "s"}`;

  // 並び順・展開状態は localStorage に永続化 (既定は全非展開)。マウント後に読み込む。
  const [order, setOrder] = useState<SectionId[]>(() => [...DEFAULT_SECTION_ORDER]);
  const [openMap, setOpenMap] = useState<Partial<Record<SectionId, boolean>>>({});
  useEffect(() => {
    setOrder(loadSectionOrder());
    setOpenMap(loadSectionOpen());
  }, []);

  const toggle = useCallback((id: SectionId) => {
    setOpenMap((prev) => {
      const next = { ...prev, [id]: !prev[id] };
      saveSectionOpen(next);
      return next;
    });
  }, []);

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 6 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates }),
  );
  const handleDragEnd = useCallback((event: DragEndEvent) => {
    const { active, over } = event;
    if (!over || active.id === over.id) return;
    setOrder((prev) => {
      const from = prev.indexOf(active.id as SectionId);
      const to = prev.indexOf(over.id as SectionId);
      if (from < 0 || to < 0) return prev;
      const next = [...prev];
      const [moved] = next.splice(from, 1);
      next.splice(to, 0, moved);
      saveSectionOrder(next);
      return next;
    });
  }, []);

  const sections: Record<SectionId, ResultSection> = {
    confirmed: {
      title: text.parentResult.confirmedTitle,
      tick: "var(--r-confirmed)",
      visible: hasConfirmed,
      count: confirmedCount,
      content: <ConfirmedBody rows={data.confirmed_results ?? []} language={language} />,
    },
    distribution: {
      title: text.parentResult.distributionTitle,
      tick: "var(--r-accent)",
      visible: true,
      count: distributionCount,
      content: <DistributionBody rows={data.results} whiteSide={whiteSide} language={language} />,
    },
    conditional: {
      title: text.parentResult.conditionalTitle,
      tick: "var(--r-conditional)",
      visible: data.mode === "normal" && data.conditional_color_groups.length > 0,
      count: conditionalCount,
      content: <ConditionalBody groups={data.conditional_color_groups} language={language} />,
    },
    normalNote: {
      title: text.parentResult.normalScopeTitle,
      tick: "var(--r-muted)",
      visible: data.mode === "normal",
      content: <NormalNoteBody language={language} />,
    },
    genetics: {
      title: text.parentResult.geneticsTitle,
      tick: "var(--r-accent)",
      visible: true,
      content: <GeneticsBody diagnostics={diagnostics} otherLoci={otherLoci} language={language} />,
    },
  };
  const visibleOrder = order.filter((id) => sections[id].visible);

  return (
    <div className="flex flex-col gap-2">
      {/* 親色不在注釈は文脈依存の警告なのでアコーディオン対象外の固定表示。 */}
      <ParentColorNotes notes={data.parent_color_notes} language={language} />
      {/* id を固定して @dnd-kit の a11y 記述要素 ID を SSR/CSR で一致させる (ハイドレーション警告回避)。 */}
      <DndContext
        id="result-sections"
        sensors={sensors}
        collisionDetection={closestCenter}
        onDragEnd={handleDragEnd}
      >
        <SortableContext items={visibleOrder} strategy={verticalListSortingStrategy}>
          <div className="flex flex-col gap-2">
            {visibleOrder.map((id) => (
              <AccordionSection
                key={id}
                id={id}
                title={sections[id].title}
                tick={sections[id].tick}
                open={Boolean(openMap[id])}
                onToggle={() => toggle(id)}
                dragLabel={text.parentResult.sectionReorder}
                count={sections[id].count}
                countLabel={
                  sections[id].count != null ? countLabelOf(sections[id].count ?? 0) : undefined
                }
              >
                {sections[id].content}
              </AccordionSection>
            ))}
          </div>
        </SortableContext>
      </DndContext>
    </div>
  );
}
