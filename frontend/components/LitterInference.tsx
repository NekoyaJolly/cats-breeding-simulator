"use client";

import { useEffect, useMemo, useState, type FormEvent } from "react";
import {
  fetchBreedColors,
  fetchBreeds,
  fetchColors,
  inferFromLitter,
  type LitterInferenceOutcome,
} from "@/lib/api";
import { BREED_READING_JA } from "@/lib/breedReadingJa";
import { filterColorsByAllowedNames } from "@/lib/colorMatch";
import { UI_TEXT, type Language } from "@/lib/i18n";
import type {
  ColorOption,
  InferenceFinding,
  LitterInferenceResponse,
} from "@/lib/schema";
import { ColorCombobox } from "./ColorCombobox";
import { FloatingSelect, FloatingTextInput } from "./FloatingField";
import { LocusChip } from "./LocusChip";

type KittenInput = {
  id: string;
  name: string;
  sex: "male" | "female";
  color: string;
};

const secondaryButtonClass =
  "rounded-md border border-slate-300 bg-white px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50";
function createKittenId(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }
  return `${Date.now()}-${Math.round(Math.random() * 100000)}`;
}

function createKittenRow(): KittenInput {
  return {
    id: createKittenId(),
    name: "",
    sex: "female",
    color: "",
  };
}

function supportText(value: number): string {
  return `${value.toFixed(value % 1 === 0 ? 0 : 1)}%`;
}

function FindingList({
  title,
  items,
  emptyText,
  supportLabel,
}: {
  title: string;
  items: InferenceFinding[];
  emptyText: string;
  supportLabel: string;
}) {
  return (
    <div className="rounded-md bg-slate-50 p-3">
      <h3 className="text-sm font-semibold text-slate-700">{title}</h3>
      {items.length === 0 ? (
        <p className="mt-2 text-sm text-slate-500">{emptyText}</p>
      ) : (
        <ul className="mt-2 space-y-2">
          {items.map((item, index) => (
            <li key={`${item.category}-${item.parent}-${item.locus}-${index}`} className="text-sm">
              <p className="font-medium text-slate-800">
                {item.parent} / <LocusChip locus={item.locus} />: {item.genotype}
                <span className="ml-2 text-xs text-slate-400">
                  {supportLabel} {supportText(item.support_pct)}
                </span>
              </p>
              <p className="mt-1 text-xs leading-5 text-slate-600">{item.note}</p>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function ResultPanel({
  data,
  language,
}: {
  data: LitterInferenceResponse;
  language: Language;
}) {
  const text = UI_TEXT[language];
  return (
    <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm sm:p-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-lg font-semibold text-slate-800">
          {text.kittenForm.resultTitle}
        </h2>
        <span className="rounded bg-slate-100 px-2 py-1 text-sm font-medium text-slate-600">
          {language === "ja"
            ? `${data.response_category} / ${text.kittenForm.candidateCount} ${data.candidate_pair_count} 件`
            : `${data.response_category} / ${data.candidate_pair_count} ${text.kittenForm.candidateCount}`}
        </span>
      </div>

      {data.contradictions.length > 0 && (
        <div className="mt-4 rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">
          <ul className="list-disc space-y-1 pl-5">
            {data.contradictions.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </div>
      )}

      <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-2">
        <FindingList
          title={text.kittenForm.confirmed}
          items={data.confirmed}
          emptyText={text.kittenForm.confirmedEmpty}
          supportLabel={text.kittenForm.support}
        />
        <FindingList
          title={text.kittenForm.conditional}
          items={data.conditional}
          emptyText={text.kittenForm.conditionalEmpty}
          supportLabel={text.kittenForm.support}
        />
        <FindingList
          title={text.kittenForm.inferred}
          items={data.inferred}
          emptyText={text.kittenForm.inferredEmpty}
          supportLabel={text.kittenForm.support}
        />
        <FindingList
          title={text.kittenForm.unconfirmed}
          items={data.unconfirmed}
          emptyText={text.kittenForm.unconfirmedEmpty}
          supportLabel={text.kittenForm.support}
        />
      </div>

      {data.warnings.length > 0 && (
        <div className="mt-4 rounded-md border border-amber-200 bg-amber-50 p-3">
          <h3 className="text-sm font-semibold text-amber-800">
            {text.kittenForm.warnings}
          </h3>
          <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-amber-800">
            {data.warnings.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </div>
      )}

      {data.recommended_tests.length > 0 && (
        <div className="mt-4 rounded-md bg-slate-50 p-3">
          <h3 className="text-sm font-semibold text-slate-700">
            {text.kittenForm.recommendedTests}
          </h3>
          <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-slate-600">
            {data.recommended_tests.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}

export function LitterInference({ language }: { language: Language }) {
  const text = UI_TEXT[language];
  const [sireColor, setSireColor] = useState("");
  const [damColor, setDamColor] = useState("");
  const [breed, setBreed] = useState("");
  const [kittens, setKittens] = useState<KittenInput[]>([createKittenRow()]);
  const [colors, setColors] = useState<ColorOption[]>([]);
  const [breedItems, setBreedItems] = useState<ColorOption[]>([]);
  const [breedAllowedColors, setBreedAllowedColors] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<LitterInferenceResponse | null>(null);

  useEffect(() => {
    let alive = true;
    fetchColors().then((list) => {
      if (alive) setColors(list);
    });
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

  // 猫種が指定されている場合は、親・子猫カラー候補をその猫種の方針へ寄せる。
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

  const breedFilteredColors = useMemo(
    () => filterColorsByAllowedNames(colors, breedAllowedColors),
    [colors, breedAllowedColors],
  );

  const canSubmit = useMemo(
    () =>
      sireColor.trim().length > 0 &&
      damColor.trim().length > 0 &&
      kittens.some((kitten) => kitten.color.trim().length > 0) &&
      !loading,
    [sireColor, damColor, kittens, loading],
  );

  function updateKitten(id: string, patch: Partial<Omit<KittenInput, "id">>) {
    setKittens((rows) =>
      rows.map((row) => (row.id === id ? { ...row, ...patch } : row)),
    );
  }

  function addKitten() {
    setKittens((rows) => [...rows, createKittenRow()]);
  }

  function removeKitten(id: string) {
    setKittens((rows) => {
      const nextRows = rows.filter((row) => row.id !== id);
      return nextRows.length > 0 ? nextRows : [createKittenRow()];
    });
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!canSubmit) return;
    setLoading(true);
    setError(null);
    const trimmedBreed = breed.trim();
    const outcome: LitterInferenceOutcome = await inferFromLitter({
      sire: {
        color: sireColor.trim(),
        ...(trimmedBreed ? { breed: trimmedBreed } : {}),
      },
      dam: {
        color: damColor.trim(),
        ...(trimmedBreed ? { breed: trimmedBreed } : {}),
      },
      kittens: kittens
        .filter((kitten) => kitten.color.trim().length > 0)
        .map((kitten) => ({
          id: kitten.id,
          sex: kitten.sex,
          color: kitten.color.trim(),
          ...(kitten.name.trim() ? { name: kitten.name.trim() } : {}),
        })),
    });
    if (outcome.ok) {
      setResult(outcome.data);
    } else {
      setResult(null);
      setError(outcome.message);
    }
    setLoading(false);
  }

  return (
    <div className="space-y-4 sm:space-y-6">
      <section className="relative rounded-lg border border-slate-200 bg-white px-4 pb-4 pt-5 shadow-sm sm:px-6 sm:pb-6 sm:pt-6">
        <h2 className="absolute -top-2.5 left-4 bg-white px-1 text-sm font-semibold leading-5 text-slate-700 sm:left-6">
          {text.kittenForm.sectionTitle}
        </h2>
        <form onSubmit={handleSubmit} className="space-y-4 sm:space-y-5">
          <div className="grid grid-cols-1 gap-3 md:grid-cols-2 md:gap-4">
            <ColorCombobox
              id="litter-sire-color"
              label={text.kittenForm.sireCoat}
              value={sireColor}
              onValueChange={setSireColor}
              onCommit={setSireColor}
              colors={breedFilteredColors}
              recent={[]}
              placeholder={text.kittenForm.sirePlaceholder}
              suggestionLayout="inline"
              recentLabel={text.common.recent}
              femaleOnlyLabel={text.common.femaleOnly}
            />
            <ColorCombobox
              id="litter-dam-color"
              label={text.kittenForm.damCoat}
              value={damColor}
              onValueChange={setDamColor}
              onCommit={setDamColor}
              colors={breedFilteredColors}
              recent={[]}
              placeholder={text.kittenForm.damPlaceholder}
              suggestionLayout="inline"
              recentLabel={text.common.recent}
              femaleOnlyLabel={text.common.femaleOnly}
            />
          </div>

          <ColorCombobox
            id="litter-breed"
            label={text.common.breed}
            value={breed}
            onValueChange={setBreed}
            onCommit={setBreed}
            colors={breedItems}
            recent={[]}
            placeholder={text.kittenForm.breedPlaceholder}
            recentLabel={text.common.recent}
            femaleOnlyLabel={text.common.femaleOnly}
          />

          <section className="relative rounded-md border border-slate-200 px-2.5 pb-2.5 pt-5 sm:px-3 sm:pb-3 sm:pt-5">
            <h3 className="absolute -top-2.5 left-3 bg-white px-1 text-sm font-semibold leading-5 text-slate-700">
              {text.kittenForm.kittenSection}
            </h3>
            <div className="space-y-3">
              {kittens.map((kitten, index) => (
                <div
                  key={kitten.id}
                  className="grid grid-cols-1 gap-3 md:grid-cols-[1fr_130px_1.4fr]"
                >
                  <div className="grid grid-cols-[minmax(0,1fr)_7.5rem] gap-2 md:contents">
                    <FloatingTextInput
                      id={`kitten-name-${kitten.id}`}
                      label={`${text.kittenForm.kittenName} ${index + 1}`}
                      value={kitten.name}
                      onChange={(event) => updateKitten(kitten.id, { name: event.target.value })}
                      placeholder={text.kittenForm.kittenNamePlaceholder}
                    />
                    <FloatingSelect
                      id={`kitten-sex-${kitten.id}`}
                      label={text.common.sex}
                      value={kitten.sex}
                      onChange={(event) =>
                        updateKitten(kitten.id, {
                          sex: event.target.value === "male" ? "male" : "female",
                        })
                      }
                    >
                      <option value="female">{text.common.female}</option>
                      <option value="male">{text.common.male}</option>
                    </FloatingSelect>
                  </div>
                  <ColorCombobox
                    id={`kitten-color-${kitten.id}`}
                    label={text.kittenForm.kittenCoat}
                    value={kitten.color}
                    onValueChange={(value) => updateKitten(kitten.id, { color: value })}
                    onCommit={(value) => updateKitten(kitten.id, { color: value })}
                    colors={breedFilteredColors}
                    recent={[]}
                    placeholder={text.kittenForm.kittenCoatPlaceholder}
                    suggestionLayout="inline"
                    recentLabel={text.common.recent}
                    femaleOnlyLabel={text.common.femaleOnly}
                  />
                  <div className="grid grid-cols-2 gap-2 md:col-span-3">
                    <button
                      type="button"
                      className={`${secondaryButtonClass} h-11 whitespace-nowrap`}
                      onClick={addKitten}
                    >
                      {text.kittenForm.addKitten}
                    </button>
                    <button
                      type="button"
                      className={`${secondaryButtonClass} h-11 whitespace-nowrap`}
                      onClick={() => removeKitten(kitten.id)}
                    >
                      {text.common.delete}
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </section>

          <button
            type="submit"
            disabled={!canSubmit}
            className="rounded-md bg-slate-800 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {loading ? text.kittenForm.loading : text.kittenForm.button}
          </button>
        </form>

        {error && (
          <div className="mt-4 rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">
            {error}
          </div>
        )}
      </section>

      {result && <ResultPanel data={result} language={language} />}
    </div>
  );
}
