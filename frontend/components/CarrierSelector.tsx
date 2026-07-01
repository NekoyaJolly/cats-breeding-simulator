"use client";

import { Dna, X } from "@phosphor-icons/react";
import { useEffect, useId, useRef, useState, type PointerEvent } from "react";
import { UI_TEXT, type Language } from "@/lib/i18n";
import { getLocusTone } from "@/lib/lociGlossary";

export type CarrierParent = "sire" | "dam";

type CarrierOption = {
  value: string;
  label: Record<Language, string>;
};

export type CarrierLocus =
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

export type CarrierSelection = Partial<Record<CarrierLocus, string>>;

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

const inactiveCarrierButtonClass: Record<CarrierParent, string> = {
  sire: "border-sky-200 bg-sky-50 text-sky-700 hover:bg-sky-100",
  dam: "border-rose-200 bg-rose-50 text-rose-700 hover:bg-rose-100",
};

const activeCarrierButtonClass: Record<CarrierParent, string> = {
  sire: "border-sky-600 bg-sky-600 text-white hover:bg-sky-700",
  dam: "border-rose-600 bg-rose-600 text-white hover:bg-rose-700",
};

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

export function hasCarrierSelection(selection: CarrierSelection): boolean {
  return CARRIER_LOCI.some((definition) => Boolean(selection[definition.locus]));
}

export function carrierSelectionCount(selection: CarrierSelection): number {
  return CARRIER_LOCI.filter((definition) => Boolean(selection[definition.locus])).length;
}

export function carrierSelectionToInput(
  selection: CarrierSelection,
): Record<string, string> | undefined {
  const input: Record<string, string> = {};
  for (const definition of CARRIER_LOCI) {
    const value = selection[definition.locus];
    if (value) input[definition.locus] = value;
  }
  return Object.keys(input).length > 0 ? input : undefined;
}

export function carrierSelectionFromInput(
  input: Record<string, string> | undefined,
): CarrierSelection {
  const selection: CarrierSelection = {};
  if (!input) return selection;
  for (const definition of CARRIER_LOCI) {
    const value = input[definition.locus];
    if (value) selection[definition.locus] = value;
  }
  return selection;
}

export function clearSexDependentCarrierSelection(
  selection: CarrierSelection,
): CarrierSelection {
  const nextSelection: CarrierSelection = { ...selection };
  // O座位は父猫/母猫で選択肢が異なるため、性別変更時は不整合を避ける。
  delete nextSelection.O;
  return nextSelection;
}

export function CarrierSelectorButton({
  parent,
  value,
  onChange,
  language,
  buttonLabel,
  modalTitle,
}: {
  parent: CarrierParent;
  value: CarrierSelection;
  onChange: (nextSelection: CarrierSelection) => void;
  language: Language;
  buttonLabel: string;
  modalTitle: string;
}) {
  const text = UI_TEXT[language];
  const modalTitleId = useId();
  const activePointerId = useRef<number | null>(null);
  const [open, setOpen] = useState(false);
  const selectedCount = carrierSelectionCount(value);
  const active = selectedCount > 0;

  useEffect(() => {
    if (!open) return;
    function closeWithEscape(event: KeyboardEvent) {
      if (event.key === "Escape") setOpen(false);
    }
    document.addEventListener("keydown", closeWithEscape);
    return () => document.removeEventListener("keydown", closeWithEscape);
  }, [open]);

  function updateCarrier(locus: CarrierLocus, nextValue: string) {
    const nextSelection: CarrierSelection = { ...value };
    if (nextValue) {
      nextSelection[locus] = nextValue;
    } else {
      delete nextSelection[locus];
    }
    onChange(nextSelection);
  }

  function updateCarrierFromPointer(
    event: PointerEvent<HTMLDivElement>,
    locus: CarrierLocus,
    groupName: string,
  ) {
    const element = document.elementFromPoint(event.clientX, event.clientY);
    const label = element?.closest("label");
    if (!(label instanceof HTMLLabelElement)) return;
    if (label.dataset.carrierGroup !== groupName) return;
    updateCarrier(locus, label.dataset.carrierValue ?? "");
  }

  function stopCarrierPointer(event: PointerEvent<HTMLDivElement>) {
    if (activePointerId.current !== event.pointerId) return;
    activePointerId.current = null;
    if (event.currentTarget.hasPointerCapture(event.pointerId)) {
      event.currentTarget.releasePointerCapture(event.pointerId);
    }
  }

  return (
    <>
      <button
        type="button"
        className={`inline-flex h-8 items-center gap-1 rounded-full border px-2 text-xs font-medium shadow-sm transition focus:outline-none focus:ring-2 focus:ring-slate-400 ${
          active ? activeCarrierButtonClass[parent] : inactiveCarrierButtonClass[parent]
        }`}
        aria-label={buttonLabel}
        title={buttonLabel}
        onClick={() => setOpen(true)}
      >
        <Dna aria-hidden="true" className="h-4 w-4" weight="duotone" />
        {active && (
          <span
            className="min-w-4 text-center"
            aria-label={text.parentForm.carrierSelector.configured}
          >
            {selectedCount}
          </span>
        )}
      </button>

      {open && (
        <div
          className="fixed inset-0 z-50 flex items-end bg-slate-900/40 px-2 pb-2 pt-4 sm:items-center sm:p-4"
          onClick={() => setOpen(false)}
        >
          <div
            role="dialog"
            aria-modal="true"
            aria-labelledby={modalTitleId}
            className="max-h-[88vh] w-full overflow-hidden rounded-lg bg-white shadow-xl sm:mx-auto sm:max-w-2xl"
            onClick={(event) => event.stopPropagation()}
          >
            <div className="border-b border-slate-200 px-4 py-3">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <h2
                    id={modalTitleId}
                    className="text-base font-semibold text-slate-900"
                  >
                    {modalTitle}
                  </h2>
                  <p className="mt-1 text-xs leading-5 text-slate-500">
                    {text.parentForm.carrierSelector.description}
                  </p>
                </div>
                <button
                  type="button"
                  className="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-full border border-slate-200 text-slate-500 transition hover:bg-slate-50 hover:text-slate-800 focus:outline-none focus:ring-2 focus:ring-slate-400"
                  aria-label={text.parentForm.carrierSelector.close}
                  onClick={() => setOpen(false)}
                >
                  <X aria-hidden="true" className="h-4 w-4" weight="bold" />
                </button>
              </div>
            </div>

            <div className="max-h-[62vh] space-y-3 overflow-y-auto px-4 py-4">
              {CARRIER_LOCI.map((definition) => {
                const options = optionsForParent(definition, parent);
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
                const selectedValue = value[definition.locus] ?? "";
                const selectedDescription = selectedValue
                  ? carrierChoiceDescription(definition.locus, selectedValue, language)
                  : definition.locus;
                const groupName = `carrier-${parent}-${definition.locus}`;
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
                            activePointerId.current = event.pointerId;
                            event.currentTarget.setPointerCapture(event.pointerId);
                            updateCarrierFromPointer(
                              event,
                              definition.locus,
                              groupName,
                            );
                          }}
                          onPointerMove={(event) => {
                            if (activePointerId.current !== event.pointerId) return;
                            event.preventDefault();
                            updateCarrierFromPointer(
                              event,
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
                                  onChange={() => updateCarrier(definition.locus, choice.value)}
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
                disabled={selectedCount === 0}
                onClick={() => onChange({})}
              >
                {text.parentForm.carrierSelector.clear}
              </button>
              <button
                type="button"
                className="rounded-md bg-slate-800 px-4 py-2 text-sm font-semibold text-white transition hover:bg-slate-700 focus:outline-none focus:ring-2 focus:ring-slate-400"
                onClick={() => setOpen(false)}
              >
                {text.parentForm.carrierSelector.close}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
