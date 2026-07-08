"use client";

import {
  useCallback,
  useEffect,
  useMemo,
  useState,
  type Dispatch,
  type FormEvent,
  type SetStateAction,
} from "react";
import { z } from "zod";
import { fetchBreedColors, fetchBreeds, fetchColors, type CalculateInput } from "@/lib/api";
import type { ColorOption } from "@/lib/schema";
import { BREED_READING_JA } from "@/lib/breedReadingJa";
import { filterColorsByAllowedNames, normalizeKey } from "@/lib/colorMatch";
import { UI_TEXT, type Language } from "@/lib/i18n";
import {
  CarrierSelectorButton,
  carrierSelectionCount,
  carrierSelectionToInput,
  hasCarrierSelection,
  type CarrierParent,
  type CarrierSelection,
} from "./CarrierSelector";
import { ColorCombobox } from "./ColorCombobox";
import { FloatingSelect } from "./FloatingField";

// 計算モード。explicit_carrier のときのみキャリア入力欄を表示する。
const MODES = [
  { value: "normal", labelKey: "normal" },
  { value: "explicit_carrier", labelKey: "explicitCarrier" },
] as const;

type CalculationMode = (typeof MODES)[number]["value"];

function isCalculationMode(value: string): value is CalculationMode {
  return MODES.some((option) => option.value === value);
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

export function BreedingForm({ onSubmit, loading, language }: Props) {
  const text = UI_TEXT[language];
  const [sireColor, setSireColor] = useState("");
  const [damColor, setDamColor] = useState("");
  const [breed, setBreed] = useState("");
  const [mode, setMode] = useState<CalculationMode>("normal");
  const [sireCarriers, setSireCarriers] = useState<CarrierSelection>({});
  const [damCarriers, setDamCarriers] = useState<CarrierSelection>({});
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

  function syncModeForCarriers(
    nextSireCarriers: CarrierSelection,
    nextDamCarriers: CarrierSelection,
  ) {
    setMode(
      hasCarrierSelection(nextSireCarriers) || hasCarrierSelection(nextDamCarriers)
        ? "explicit_carrier"
        : "normal",
    );
  }

  function updateSireCarriers(nextSelection: CarrierSelection) {
    setSireCarriers(nextSelection);
    syncModeForCarriers(nextSelection, damCarriers);
  }

  function updateDamCarriers(nextSelection: CarrierSelection) {
    setDamCarriers(nextSelection);
    syncModeForCarriers(sireCarriers, nextSelection);
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

  function renderCarrierButton(parent: CarrierParent) {
    const label =
      parent === "sire"
        ? text.parentForm.carrierSelector.sireButton
        : text.parentForm.carrierSelector.damButton;
    const title =
      parent === "sire"
        ? text.parentForm.carrierSelector.sireTitle
        : text.parentForm.carrierSelector.damTitle;
    return (
      <CarrierSelectorButton
        parent={parent}
        value={parent === "sire" ? sireCarriers : damCarriers}
        onChange={parent === "sire" ? updateSireCarriers : updateDamCarriers}
        language={language}
        buttonLabel={label}
        modalTitle={title}
      />
    );
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-3 sm:space-y-4">
      <div
        data-tour="parent-carriers"
        className="grid grid-cols-1 gap-3 sm:grid-cols-2 sm:gap-4"
      >
        <ColorCombobox
          id="sire-color"
          label={text.parentForm.sireCoat}
          labelAction={renderCarrierButton("sire")}
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
        <ColorCombobox
          id="dam-color"
          label={text.parentForm.damCoat}
          labelAction={renderCarrierButton("dam")}
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

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 sm:gap-4">
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
        <FloatingSelect
          id="mode"
          label={text.parentForm.mode}
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
        </FloatingSelect>
      </div>

      {hasExplicitCarriers && (
        <div className="rounded-md bg-surface-2 px-3 py-2 text-xs leading-5 text-ink-soft">
          {text.parentForm.carrierSelector.modeNote}
        </div>
      )}

      <button
        type="submit"
        disabled={!canSubmit}
        className="w-full rounded-md bg-accent px-4 py-2 text-sm font-semibold text-accent-ink shadow-sm transition hover:bg-accent/90 disabled:cursor-not-allowed disabled:opacity-50 sm:w-auto"
      >
        {loading ? text.parentForm.loading : text.parentForm.button}
      </button>
    </form>
  );
}
