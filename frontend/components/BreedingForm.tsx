"use client";

import {
  useCallback,
  useEffect,
  useId,
  useMemo,
  useRef,
  useState,
  type Dispatch,
  type FormEvent,
  type PointerEvent,
  type SetStateAction,
} from "react";
import { z } from "zod";
import { fetchBreedColors, fetchBreeds, fetchColors, type CalculateInput } from "@/lib/api";
import type { ColorOption } from "@/lib/schema";
import { BREED_READING_JA } from "@/lib/breedReadingJa";
import { filterColorsByAllowedNames, normalizeKey } from "@/lib/colorMatch";
import { UI_TEXT, type Language } from "@/lib/i18n";
import { getLocusTone } from "@/lib/lociGlossary";
import { ColorCombobox } from "./ColorCombobox";

// 計算モード。explicit_carrier のときのみキャリア入力欄を表示する。
const MODES = [
  { value: "normal", labelKey: "normal" },
  { value: "explicit_carrier", labelKey: "explicitCarrier" },
  { value: "carrier_exploration", labelKey: "carrierExploration" },
] as const;

type CalculationMode = (typeof MODES)[number]["value"];

function isCalculationMode(value: string): value is CalculationMode {
  return MODES.some((option) => option.value === value);
}

type CarrierParent = "sire" | "dam";

type CarrierOption = {
  value: string;
  label: Record<Language, string>;
};

type CarrierLocus =
  | "A"
  | "B"
  | "C"
  | "D"
  | "I"
  | "O"
  | "S"
  | "W"
  | "Mc"
  | "Ta"
  | "Sp"
  | "Wb";

type CarrierLocusDefinition = {
  locus: CarrierLocus;
  name: Record<Language, string>;
  options: readonly CarrierOption[];
  sireOptions?: readonly CarrierOption[];
  damOptions?: readonly CarrierOption[];
};

type CarrierSelection = Partial<Record<CarrierLocus, string>>;
/**
 * 選択済み遺伝子型の短い補足文を座位と値ごとに保持する。
 */
type CarrierDescriptionMap = Partial<
  Record<CarrierLocus, Record<string, Record<Language, string>>>
>;

const carrierOptions = (values: readonly string[]): readonly CarrierOption[] =>
  values.map((value) => ({ value, label: { ja: value, en: value } }));

const CARRIER_CHOICE_DESCRIPTIONS: CarrierDescriptionMap = {
  A: {
    "A/A": { ja: "タビー固定", en: "Tabby fixed" },
    "A/a": { ja: "タビー・ソリッド因子", en: "Tabby, solid carrier" },
    "a/a": { ja: "ソリッド固定", en: "Solid fixed" },
  },
  B: {
    "B/B": { ja: "黒系固定", en: "Black fixed" },
    "B/b": { ja: "チョコ因子", en: "Chocolate carrier" },
    "B/bl": { ja: "シナモン因子", en: "Cinnamon carrier" },
    "b/b": { ja: "チョコ固定", en: "Chocolate fixed" },
    "b/bl": { ja: "チョコ・シナモン因子", en: "Choc/cinnamon carrier" },
    "bl/bl": { ja: "シナモン固定", en: "Cinnamon fixed" },
  },
  C: {
    "C/C": { ja: "フルカラー固定", en: "Full color fixed" },
    "C/cs": { ja: "ポイント因子", en: "Point carrier" },
    "C/cb": { ja: "セピア因子", en: "Sepia carrier" },
    "cs/cs": { ja: "ポイント固定", en: "Point fixed" },
    "cb/cs": { ja: "ミンク固定", en: "Mink fixed" },
    "cb/cb": { ja: "セピア固定", en: "Sepia fixed" },
  },
  D: {
    "D/D": { ja: "濃色固定", en: "Dense fixed" },
    "D/d": { ja: "希釈因子", en: "Dilution carrier" },
    "d/d": { ja: "希釈固定", en: "Dilute fixed" },
  },
  I: {
    "I/I": { ja: "シルバー固定", en: "Silver fixed" },
    "I/i": { ja: "シルバー・非銀因子", en: "Silver, non-silver carrier" },
    "i/i": { ja: "非シルバー固定", en: "Non-silver fixed" },
  },
  O: {
    "O/Y": { ja: "レッド系オス", en: "Red-series male" },
    "o/Y": { ja: "非レッド系オス", en: "Non-red male" },
    "O/O": { ja: "レッド系固定", en: "Red fixed" },
    "O/o": { ja: "トーティ系", en: "Tortie-series" },
    "o/o": { ja: "非レッド固定", en: "Non-red fixed" },
  },
  S: {
    "S/S": { ja: "高白斑固定", en: "High white fixed" },
    "S/s": { ja: "白斑あり", en: "White spotting" },
    "s/s": { ja: "白斑なし", en: "No white spotting" },
  },
  W: {
    "W/W": { ja: "白固定", en: "White fixed" },
    "W/w": { ja: "白・非白因子", en: "White, non-white carrier" },
    "w/w": { ja: "優性白なし", en: "No dominant white" },
  },
  Mc: {
    "Mc/Mc": { ja: "マッカレル固定", en: "Mackerel fixed" },
    "Mc/mc": { ja: "クラシック因子", en: "Classic carrier" },
    "mc/mc": { ja: "クラシック固定", en: "Classic fixed" },
  },
  Ta: {
    "Ta/Ta": { ja: "ティックド固定", en: "Ticked fixed" },
    "Ta/ta": { ja: "非ティックド因子", en: "Non-ticked carrier" },
    "ta/ta": { ja: "ティックドなし", en: "No ticked pattern" },
  },
  Sp: {
    "Sp/Sp": { ja: "スポット固定", en: "Spotted fixed" },
    "Sp/sp": { ja: "スポット因子", en: "Spotted carrier" },
    "sp/sp": { ja: "スポットなし", en: "No spotted modifier" },
  },
  Wb: {
    "Wb/Wb": { ja: "ワイドバンド固定", en: "Wide band fixed" },
    "Wb/wb": { ja: "広帯因子", en: "Wide band carrier" },
    "wb/wb": { ja: "広帯なし", en: "No wide band" },
  },
};

const CARRIER_LOCI = [
  {
    locus: "A",
    name: { ja: "アグーチ / タビー", en: "Agouti / tabby" },
    options: carrierOptions(["A/A", "A/a", "a/a"]),
  },
  {
    locus: "B",
    name: { ja: "ブラック系列", en: "Black series" },
    options: carrierOptions(["B/B", "B/b", "B/bl", "b/b", "b/bl", "bl/bl"]),
  },
  {
    locus: "C",
    name: { ja: "発色 / ポイント", en: "Color restriction" },
    options: carrierOptions(["C/C", "C/cs", "C/cb", "cs/cs", "cb/cs", "cb/cb"]),
  },
  {
    locus: "D",
    name: { ja: "希釈", en: "Dilution" },
    options: carrierOptions(["D/D", "D/d", "d/d"]),
  },
  {
    locus: "I",
    name: { ja: "シルバー", en: "Silver inhibitor" },
    options: carrierOptions(["I/I", "I/i", "i/i"]),
  },
  {
    locus: "O",
    name: { ja: "オレンジ", en: "Orange" },
    options: carrierOptions([]),
    sireOptions: carrierOptions(["O/Y", "o/Y"]),
    damOptions: carrierOptions(["O/O", "O/o", "o/o"]),
  },
  {
    locus: "S",
    name: { ja: "白斑", en: "White spotting" },
    options: carrierOptions(["S/S", "S/s", "s/s"]),
  },
  {
    locus: "W",
    name: { ja: "優性白", en: "Dominant white" },
    options: carrierOptions(["W/W", "W/w", "w/w"]),
  },
  {
    locus: "Mc",
    name: { ja: "縞型", en: "Tabby pattern" },
    options: carrierOptions(["Mc/Mc", "Mc/mc", "mc/mc"]),
  },
  {
    locus: "Ta",
    name: { ja: "ティックド", en: "Ticked" },
    options: carrierOptions(["Ta/Ta", "Ta/ta", "ta/ta"]),
  },
  {
    locus: "Sp",
    name: { ja: "スポテッド", en: "Spotted modifier" },
    options: carrierOptions(["Sp/Sp", "Sp/sp", "sp/sp"]),
  },
  {
    locus: "Wb",
    name: { ja: "ワイドバンド", en: "Wide band" },
    options: carrierOptions(["Wb/Wb", "Wb/wb", "wb/wb"]),
  },
] as const satisfies readonly CarrierLocusDefinition[];

function optionsForParent(
  definition: CarrierLocusDefinition,
  parent: CarrierParent,
): readonly CarrierOption[] {
  if (parent === "sire" && definition.sireOptions) return definition.sireOptions;
  if (parent === "dam" && definition.damOptions) return definition.damOptions;
  return definition.options;
}

function carrierChoiceDescription(
  locus: CarrierLocus,
  value: string,
  language: Language,
): string {
  return CARRIER_CHOICE_DESCRIPTIONS[locus]?.[value]?.[language] ?? value;
}

function hasCarrierSelection(selection: CarrierSelection): boolean {
  return CARRIER_LOCI.some((definition) => Boolean(selection[definition.locus]));
}

function carrierSelectionCount(selection: CarrierSelection): number {
  return CARRIER_LOCI.filter((definition) => Boolean(selection[definition.locus])).length;
}

function carrierSelectionToInput(
  selection: CarrierSelection,
): Record<string, string> | undefined {
  const input: Record<string, string> = {};
  for (const definition of CARRIER_LOCI) {
    const value = selection[definition.locus];
    if (value) input[definition.locus] = value;
  }
  return Object.keys(input).length > 0 ? input : undefined;
}

function GeneIcon() {
  return (
    <svg
      aria-hidden="true"
      className="h-4 w-4"
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M7 3c6 4 4 14 10 18" />
      <path d="M17 3C11 7 13 17 7 21" />
      <path d="M8.5 6h7" />
      <path d="M7.5 10h9" />
      <path d="M7.5 14h9" />
      <path d="M8.5 18h7" />
    </svg>
  );
}

// 最近選んだ値 (履歴) の localStorage キーと保持件数。
// 履歴は入力欄ごとに 1 対 1 (父毛色 / 母毛色 / 猫種で別管理)。
const SIRE_RECENT_KEY = "cbs:recentSireColors";
const DAM_RECENT_KEY = "cbs:recentDamColors";
const BREED_RECENT_KEY = "cbs:recentBreeds";
// 旧・父母共有キー。履歴分離前のユーザー履歴を引き継ぐためのフォールバック読込用。
const LEGACY_COLOR_RECENT_KEY = "cbs:recentColors";
const RECENT_MAX = 8;
const recentSchema = z.array(z.string());

// localStorage から履歴を復元する (不可 / 壊れた JSON は空配列)。
function loadRecent(key: string): string[] {
  try {
    const raw = window.localStorage.getItem(key);
    if (raw === null) return [];
    const parsed = recentSchema.safeParse(JSON.parse(raw));
    return parsed.success ? parsed.data.slice(0, RECENT_MAX) : [];
  } catch {
    return [];
  }
}

function saveRecent(key: string, list: string[]): void {
  try {
    window.localStorage.setItem(key, JSON.stringify(list));
  } catch {
    // 保存不可でも UI 状態としては更新する。
  }
}

// 値を履歴の先頭へ積む (重複排除 + 上限) → state 更新 + localStorage 保存。
function commitRecent(
  setter: Dispatch<SetStateAction<string[]>>,
  key: string,
  value: string,
): void {
  const trimmed = value.trim();
  if (!trimmed) return;
  setter((prev) => {
    const next = [trimmed, ...prev.filter((item) => item !== trimmed)].slice(
      0,
      RECENT_MAX,
    );
    saveRecent(key, next);
    return next;
  });
}

type Props = {
  onSubmit: (input: CalculateInput) => void;
  loading: boolean;
  language: Language;
};

const inputClass =
  "w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm shadow-sm focus:border-slate-500 focus:outline-none focus:ring-1 focus:ring-slate-500";
const labelClass = "block text-sm font-medium text-slate-700";
const parentFieldAccentClass: Record<CarrierParent, string> = {
  sire: "border-sky-100 bg-sky-50/35 shadow-sky-100/60",
  dam: "border-rose-100 bg-rose-50/35 shadow-rose-100/60",
};
const inactiveCarrierButtonClass: Record<CarrierParent, string> = {
  sire: "border-sky-200 bg-sky-50 text-sky-700 hover:bg-sky-100",
  dam: "border-rose-200 bg-rose-50 text-rose-700 hover:bg-rose-100",
};
const activeCarrierButtonClass: Record<CarrierParent, string> = {
  sire: "border-sky-600 bg-sky-600 text-white hover:bg-sky-700",
  dam: "border-rose-600 bg-rose-600 text-white hover:bg-rose-700",
};

export function BreedingForm({ onSubmit, loading, language }: Props) {
  const text = UI_TEXT[language];
  const carrierModalTitleId = useId();
  const activeCarrierPointerId = useRef<number | null>(null);
  const [sireColor, setSireColor] = useState("");
  const [damColor, setDamColor] = useState("");
  const [breed, setBreed] = useState("");
  const [mode, setMode] = useState<CalculationMode>("normal");
  const [sireCarriers, setSireCarriers] = useState<CarrierSelection>({});
  const [damCarriers, setDamCarriers] = useState<CarrierSelection>({});
  const [carrierModalParent, setCarrierModalParent] = useState<CarrierParent | null>(
    null,
  );
  const [colors, setColors] = useState<ColorOption[]>([]);
  const [breedItems, setBreedItems] = useState<ColorOption[]>([]);
  const [breedAllowedColors, setBreedAllowedColors] = useState<string[]>([]);
  // 履歴は入力欄ごとに分離 (父毛色 / 母毛色 / 猫種)。
  const [sireRecent, setSireRecent] = useState<string[]>([]);
  const [damRecent, setDamRecent] = useState<string[]>([]);
  const [breedRecent, setBreedRecent] = useState<string[]>([]);

  // サジェスト候補 (毛色・猫種) をマウント時に取得する (失敗時は空 → 自由入力で動作)。
  useEffect(() => {
    let alive = true;
    fetchColors().then((list) => {
      if (alive) setColors(list);
    });
    // 猫種は ColorCombobox を再利用するため ColorOption 形へ写す
    // (reading_ja=日本語名 / breed_context=遺伝影響バッジ)。
    fetchBreeds().then((list) => {
      if (!alive) return;
      setBreedItems(
        list.map((breedOption) => {
          const reading = BREED_READING_JA[breedOption.value] ?? "";
          return {
            value: breedOption.value,
            reading_ja: reading,
            status: "",
            breed_context: breedOption.affects_genetics ? text.common.geneticsAffects : "",
            sex_restriction: "",
            keywords: [breedOption.value, reading].filter(Boolean),
          };
        }),
      );
    });
    return () => {
      alive = false;
    };
  }, [text.common.geneticsAffects]);

  // 猫種指定時は、その猫種のカラー方針に沿って毛色サジェストを絞る。
  useEffect(() => {
    const trimmedBreed = breed.trim();
    if (!trimmedBreed) {
      setBreedAllowedColors([]);
      return;
    }
    let alive = true;
    fetchBreedColors(trimmedBreed).then((list) => {
      if (alive) setBreedAllowedColors(list);
    });
    return () => {
      alive = false;
    };
  }, [breed]);

  // 履歴を localStorage から復元する (入力欄ごと)。
  // 新キーが空の既存ユーザーは、旧・父母共有キーをフォールバックで引き継ぐ
  // (以後、各欄で確定すると新キーが優先される)。
  useEffect(() => {
    const legacy = loadRecent(LEGACY_COLOR_RECENT_KEY);
    const sire = loadRecent(SIRE_RECENT_KEY);
    const dam = loadRecent(DAM_RECENT_KEY);
    setSireRecent(sire.length > 0 ? sire : legacy);
    setDamRecent(dam.length > 0 ? dam : legacy);
    setBreedRecent(loadRecent(BREED_RECENT_KEY));
  }, []);

  function pushSireRecent(value: string) {
    commitRecent(setSireRecent, SIRE_RECENT_KEY, value);
  }
  function pushDamRecent(value: string) {
    commitRecent(setDamRecent, DAM_RECENT_KEY, value);
  }
  function pushBreedRecent(value: string) {
    commitRecent(setBreedRecent, BREED_RECENT_KEY, value);
  }

  const breedFilteredColors = useMemo(
    () => filterColorsByAllowedNames(colors, breedAllowedColors),
    [colors, breedAllowedColors],
  );
  const breedAllowedKeys = useMemo(
    () => new Set(breedAllowedColors.map((colorName) => normalizeKey(colorName))),
    [breedAllowedColors],
  );
  const isBreedAllowedRecent = useCallback(
    (value: string): boolean =>
      breedAllowedKeys.size === 0 || breedAllowedKeys.has(normalizeKey(value)),
    [breedAllowedKeys],
  );

  // female_only (パッチド/トーティ系) はオス親では遺伝的に成立しないため、
  // 父猫欄のサジェスト候補・履歴から除外する (母猫欄は全色のまま)。
  const femaleOnly = useMemo(
    () =>
      new Set(
        breedFilteredColors
          .filter((color) => color.sex_restriction === "female_only")
          .map((color) => color.value),
      ),
    [breedFilteredColors],
  );
  const sireColors = useMemo(
    () => breedFilteredColors.filter((color) => !femaleOnly.has(color.value)),
    [breedFilteredColors, femaleOnly],
  );
  const sireRecentShown = useMemo(
    () => sireRecent.filter((value) => !femaleOnly.has(value) && isBreedAllowedRecent(value)),
    [sireRecent, femaleOnly, isBreedAllowedRecent],
  );
  const damRecentShown = useMemo(
    () => damRecent.filter((value) => isBreedAllowedRecent(value)),
    [damRecent, isBreedAllowedRecent],
  );
  const sireCarrierCount = useMemo(
    () => carrierSelectionCount(sireCarriers),
    [sireCarriers],
  );
  const damCarrierCount = useMemo(
    () => carrierSelectionCount(damCarriers),
    [damCarriers],
  );
  const hasExplicitCarriers =
    sireCarrierCount > 0 || damCarrierCount > 0;
  const activeCarrierSelection =
    carrierModalParent === "sire" ? sireCarriers : damCarriers;
  const activeCarrierCount =
    carrierModalParent === "sire" ? sireCarrierCount : damCarrierCount;
  const activeCarrierTitle =
    carrierModalParent === "sire"
      ? text.parentForm.carrierSelector.sireTitle
      : text.parentForm.carrierSelector.damTitle;

  useEffect(() => {
    if (!carrierModalParent) return;
    function closeWithEscape(event: KeyboardEvent) {
      if (event.key === "Escape") setCarrierModalParent(null);
    }
    document.addEventListener("keydown", closeWithEscape);
    return () => document.removeEventListener("keydown", closeWithEscape);
  }, [carrierModalParent]);

  function updateCarrier(
    parent: CarrierParent,
    locus: CarrierLocus,
    value: string,
  ) {
    const current = parent === "sire" ? sireCarriers : damCarriers;
    const other = parent === "sire" ? damCarriers : sireCarriers;
    const next: CarrierSelection = { ...current };
    if (value) {
      next[locus] = value;
      setMode("explicit_carrier");
    } else {
      delete next[locus];
      if (!hasCarrierSelection(next) && !hasCarrierSelection(other)) {
        setMode("normal");
      }
    }
    if (parent === "sire") {
      setSireCarriers(next);
    } else {
      setDamCarriers(next);
    }
  }

  function updateCarrierFromPointer(
    event: PointerEvent<HTMLDivElement>,
    parent: CarrierParent,
    locus: CarrierLocus,
    groupName: string,
  ) {
    const element = document.elementFromPoint(event.clientX, event.clientY);
    const label = element?.closest("label");
    if (!(label instanceof HTMLLabelElement)) return;
    if (label.dataset.carrierGroup !== groupName) return;
    updateCarrier(parent, locus, label.dataset.carrierValue ?? "");
  }

  function stopCarrierPointer(event: PointerEvent<HTMLDivElement>) {
    if (activeCarrierPointerId.current !== event.pointerId) return;
    activeCarrierPointerId.current = null;
    if (event.currentTarget.hasPointerCapture(event.pointerId)) {
      event.currentTarget.releasePointerCapture(event.pointerId);
    }
  }

  function clearCarrierSelection(parent: CarrierParent) {
    const other = parent === "sire" ? damCarriers : sireCarriers;
    if (parent === "sire") {
      setSireCarriers({});
    } else {
      setDamCarriers({});
    }
    if (!hasCarrierSelection(other)) setMode("normal");
  }

  // 親色は必須。breed は任意。
  const canSubmit =
    sireColor.trim().length > 0 && damColor.trim().length > 0 && !loading;

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!canSubmit) return;
    pushSireRecent(sireColor);
    pushDamRecent(damColor);
    const input: CalculateInput = {
      sire_color: sireColor.trim(),
      dam_color: damColor.trim(),
      mode,
    };
    const trimmedBreed = breed.trim();
    if (trimmedBreed) {
      input.breed = trimmedBreed;
      pushBreedRecent(trimmedBreed);
    }
    // キャリアは明示キャリアモードのときのみ送る。
    if (hasExplicitCarriers) {
      input.mode = "explicit_carrier";
      input.sire_carriers = carrierSelectionToInput(sireCarriers);
      input.dam_carriers = carrierSelectionToInput(damCarriers);
    }
    onSubmit(input);
  }

  function renderCarrierButton(parent: CarrierParent, count: number) {
    const active = count > 0;
    const label =
      parent === "sire"
        ? text.parentForm.carrierSelector.sireButton
        : text.parentForm.carrierSelector.damButton;
    return (
      <button
        type="button"
        className={`inline-flex h-8 items-center gap-1 rounded-full border px-2 text-xs font-medium shadow-sm transition focus:outline-none focus:ring-2 focus:ring-slate-400 ${
          active
            ? activeCarrierButtonClass[parent]
            : inactiveCarrierButtonClass[parent]
        }`}
        aria-label={label}
        title={label}
        onClick={() => setCarrierModalParent(parent)}
      >
        <GeneIcon />
        {active && (
          <span className="min-w-4 text-center" aria-label={text.parentForm.carrierSelector.configured}>
            {count}
          </span>
        )}
      </button>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div className={`rounded-lg border p-3 shadow-sm ${parentFieldAccentClass.sire}`}>
          <ColorCombobox
            id="sire-color"
            label={text.parentForm.sireCoat}
            labelAction={renderCarrierButton("sire", sireCarrierCount)}
            required
            value={sireColor}
            onValueChange={setSireColor}
            onCommit={pushSireRecent}
            colors={sireColors}
            recent={sireRecentShown}
            placeholder={text.parentForm.sirePlaceholder}
            recentLabel={text.common.recent}
            femaleOnlyLabel={text.common.femaleOnly}
          />
        </div>
        <div className={`rounded-lg border p-3 shadow-sm ${parentFieldAccentClass.dam}`}>
          <ColorCombobox
            id="dam-color"
            label={text.parentForm.damCoat}
            labelAction={renderCarrierButton("dam", damCarrierCount)}
            required
            value={damColor}
            onValueChange={setDamColor}
            onCommit={pushDamRecent}
            colors={breedFilteredColors}
            recent={damRecentShown}
            placeholder={text.parentForm.damPlaceholder}
            recentLabel={text.common.recent}
            femaleOnlyLabel={text.common.femaleOnly}
          />
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        {/* 猫種は任意。ColorCombobox を再利用 (候補=猫種、日本語名で絞り込み可)。 */}
        <ColorCombobox
          id="breed"
          label={text.common.breed}
          value={breed}
          onValueChange={setBreed}
          onCommit={pushBreedRecent}
          colors={breedItems}
          recent={breedRecent}
          placeholder={text.parentForm.breedPlaceholder}
          recentLabel={text.common.recent}
          femaleOnlyLabel={text.common.femaleOnly}
        />
        <div className="space-y-1">
          <label htmlFor="mode" className={labelClass}>
            {text.parentForm.mode}
          </label>
          <select
            id="mode"
            className={inputClass}
            value={mode}
            onChange={(event) => {
              if (isCalculationMode(event.target.value)) {
                setMode(event.target.value);
              }
            }}
          >
            {MODES.map((option) => (
              <option key={option.value} value={option.value}>
                {text.parentForm.modes[option.labelKey]}
              </option>
            ))}
          </select>
        </div>
      </div>

      {hasExplicitCarriers && (
        <div className="rounded-md bg-slate-100 px-3 py-2 text-xs leading-5 text-slate-600">
          {text.parentForm.carrierSelector.modeNote}
        </div>
      )}

      {carrierModalParent && (
        <div
          className="fixed inset-0 z-50 flex items-end bg-slate-900/40 px-2 pb-2 pt-4 sm:items-center sm:p-4"
          onClick={() => setCarrierModalParent(null)}
        >
          <div
            role="dialog"
            aria-modal="true"
            aria-labelledby={carrierModalTitleId}
            className="max-h-[88vh] w-full overflow-hidden rounded-lg bg-white shadow-xl sm:mx-auto sm:max-w-2xl"
            onClick={(event) => event.stopPropagation()}
          >
            <div className="border-b border-slate-200 px-4 py-3">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <h2
                    id={carrierModalTitleId}
                    className="text-base font-semibold text-slate-900"
                  >
                    {activeCarrierTitle}
                  </h2>
                  <p className="mt-1 text-xs leading-5 text-slate-500">
                    {text.parentForm.carrierSelector.description}
                  </p>
                </div>
                <button
                  type="button"
                  className="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-full border border-slate-200 text-lg leading-none text-slate-500 transition hover:bg-slate-50 hover:text-slate-800 focus:outline-none focus:ring-2 focus:ring-slate-400"
                  aria-label={text.parentForm.carrierSelector.close}
                  onClick={() => setCarrierModalParent(null)}
                >
                  ×
                </button>
              </div>
            </div>

            <div className="max-h-[62vh] space-y-3 overflow-y-auto px-4 py-4">
              {CARRIER_LOCI.map((definition) => {
                const options = optionsForParent(definition, carrierModalParent);
                const choices = [
                  {
                    value: "",
                    label: text.parentForm.carrierSelector.none,
                  },
                  ...options.map((option) => ({
                    value: option.value,
                    label: option.label[language],
                  })),
                ];
                const selectedValue = activeCarrierSelection[definition.locus] ?? "";
                const selectedDescription = selectedValue
                  ? carrierChoiceDescription(definition.locus, selectedValue, language)
                  : definition.locus;
                const groupName = `carrier-${carrierModalParent}-${definition.locus}`;
                const tone = getLocusTone(definition.locus);

                return (
                  <div
                    key={definition.locus}
                    className="rounded-lg border border-slate-200 bg-white p-2.5 shadow-sm transition hover:border-slate-300"
                  >
                    <div className="grid grid-cols-[minmax(6.5rem,9rem)_minmax(0,1fr)] items-center gap-2 sm:grid-cols-[minmax(10rem,13rem)_minmax(0,1fr)] sm:gap-3">
                      <div className="flex min-w-0 items-center gap-2">
                        <div
                          className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-md text-xs font-semibold shadow-sm ${tone.iconClass}`}
                        >
                          {definition.locus}
                        </div>
                        <div className="min-w-0">
                          <div className="truncate text-sm font-semibold text-slate-900">
                            {definition.name[language]}
                          </div>
                          <div
                            className={`mt-0.5 truncate text-xs ${
                              selectedValue ? tone.textClass : "text-slate-500"
                            }`}
                            title={selectedDescription}
                          >
                            {selectedDescription}
                          </div>
                        </div>
                      </div>
                      <fieldset className="min-w-0">
                        <legend className="sr-only">
                          {definition.locus} {text.parentForm.carrierSelector.selected}
                        </legend>
                        <div
                          className="inline-flex max-w-full touch-pan-y select-none flex-wrap gap-1 rounded-lg border border-slate-200 bg-slate-100 p-1 shadow-inner"
                          onPointerDown={(event) => {
                            event.preventDefault();
                            activeCarrierPointerId.current = event.pointerId;
                            event.currentTarget.setPointerCapture(event.pointerId);
                            updateCarrierFromPointer(
                              event,
                              carrierModalParent,
                              definition.locus,
                              groupName,
                            );
                          }}
                          onPointerMove={(event) => {
                            if (activeCarrierPointerId.current !== event.pointerId) return;
                            event.preventDefault();
                            updateCarrierFromPointer(
                              event,
                              carrierModalParent,
                              definition.locus,
                              groupName,
                            );
                          }}
                          onPointerUp={stopCarrierPointer}
                          onPointerCancel={stopCarrierPointer}
                        >
                          {choices.map((choice, index) => {
                            const isSelected = selectedValue === choice.value;
                            const isExplicitChoice = choice.value.length > 0;
                            const selectedClass = isExplicitChoice
                              ? tone.selectedClass
                              : "bg-white text-slate-600 shadow-sm ring-1 ring-slate-200";
                            const inputId = `${groupName}-${index}`;

                            return (
                              <label
                                key={`${definition.locus}-${index}-${choice.value || "none"}`}
                                htmlFor={inputId}
                                data-carrier-group={groupName}
                                data-carrier-value={choice.value}
                                className={`relative flex min-h-8 min-w-11 cursor-ew-resize items-center justify-center rounded-md px-1.5 text-center text-xs font-semibold leading-tight transition has-[:focus-visible]:ring-2 has-[:focus-visible]:ring-emerald-500 has-[:focus-visible]:ring-offset-1 ${
                                  isSelected
                                    ? selectedClass
                                    : "text-slate-600 hover:bg-white/70 hover:text-slate-900"
                                }`}
                              >
                                <input
                                  id={inputId}
                                  type="radio"
                                  name={groupName}
                                  value={choice.value}
                                  checked={isSelected}
                                  className="sr-only"
                                  aria-label={`${definition.locus} ${choice.label}`}
                                  onChange={() =>
                                    updateCarrier(
                                      carrierModalParent,
                                      definition.locus,
                                      choice.value,
                                    )
                                  }
                                />
                                <span className="min-w-0 break-words">
                                  {choice.label}
                                </span>
                              </label>
                            );
                          })}
                        </div>
                      </fieldset>
                    </div>
                  </div>
                );
              })}
            </div>

            <div className="flex items-center justify-between gap-3 border-t border-slate-200 px-4 py-3">
              <button
                type="button"
                className="rounded-md border border-slate-200 px-3 py-2 text-xs font-medium text-slate-600 transition hover:bg-slate-50 focus:outline-none focus:ring-2 focus:ring-slate-400"
                disabled={activeCarrierCount === 0}
                onClick={() => clearCarrierSelection(carrierModalParent)}
              >
                {text.parentForm.carrierSelector.clear}
              </button>
              <button
                type="button"
                className="rounded-md bg-slate-800 px-4 py-2 text-sm font-semibold text-white transition hover:bg-slate-700 focus:outline-none focus:ring-2 focus:ring-slate-400"
                onClick={() => setCarrierModalParent(null)}
              >
                {text.parentForm.carrierSelector.close}
              </button>
            </div>
          </div>
        </div>
      )}

      <button
        type="submit"
        disabled={!canSubmit}
        className="w-full rounded-md bg-slate-800 px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-50 sm:w-auto"
      >
        {loading ? text.parentForm.loading : text.parentForm.button}
      </button>
    </form>
  );
}
