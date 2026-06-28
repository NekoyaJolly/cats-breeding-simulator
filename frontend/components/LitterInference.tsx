"use client";

import { useEffect, useMemo, useState, type FormEvent } from "react";
import {
  fetchBreeds,
  fetchColors,
  inferFromLitter,
  type LitterInferenceOutcome,
} from "@/lib/api";
import { BREED_READING_JA } from "@/lib/breedReadingJa";
import type {
  ColorOption,
  InferenceFinding,
  LitterInferenceResponse,
} from "@/lib/schema";
import { ColorCombobox } from "./ColorCombobox";

type KittenInput = {
  id: string;
  name: string;
  sex: "male" | "female";
  color: string;
};

const inputClass =
  "w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm shadow-sm focus:border-slate-500 focus:outline-none focus:ring-1 focus:ring-slate-500";
const labelClass = "block text-sm font-medium text-slate-700";
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
}: {
  title: string;
  items: InferenceFinding[];
  emptyText: string;
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
                {item.parent} / {item.locus}: {item.genotype}
                <span className="ml-2 text-xs text-slate-400">
                  支持 {supportText(item.support_pct)}
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

function ResultPanel({ data }: { data: LitterInferenceResponse }) {
  return (
    <section className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-lg font-semibold text-slate-800">推定結果</h2>
        <span className="rounded bg-slate-100 px-2 py-1 text-sm font-medium text-slate-600">
          {data.response_category} / 候補 {data.candidate_pair_count} 件
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
        <FindingList title="確定" items={data.confirmed} emptyText="確定できる因子はありません。" />
        <FindingList
          title="条件付き確定"
          items={data.conditional}
          emptyText="条件付きで確定できる因子はありません。"
        />
        <FindingList title="推定" items={data.inferred} emptyText="推定できる因子はありません。" />
        <FindingList
          title="未確認"
          items={data.unconfirmed}
          emptyText="未確認として残る因子はありません。"
        />
      </div>

      {data.warnings.length > 0 && (
        <div className="mt-4 rounded-md border border-amber-200 bg-amber-50 p-3">
          <h3 className="text-sm font-semibold text-amber-800">警告</h3>
          <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-amber-800">
            {data.warnings.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </div>
      )}

      {data.recommended_tests.length > 0 && (
        <div className="mt-4 rounded-md bg-slate-50 p-3">
          <h3 className="text-sm font-semibold text-slate-700">推奨検査</h3>
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

export function LitterInference() {
  const [sireColor, setSireColor] = useState("");
  const [damColor, setDamColor] = useState("");
  const [breed, setBreed] = useState("");
  const [kittens, setKittens] = useState<KittenInput[]>([createKittenRow()]);
  const [colors, setColors] = useState<ColorOption[]>([]);
  const [breedItems, setBreedItems] = useState<ColorOption[]>([]);
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
            breed_context: breedOption.affects_genetics ? "遺伝に影響" : "",
            sex_restriction: "",
            keywords: [breedOption.value, reading].filter(Boolean),
          };
        }),
      );
    });
    return () => {
      alive = false;
    };
  }, []);

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
    <div className="space-y-6">
      <section className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
        <h2 className="text-lg font-semibold text-slate-800">リター実績から推定</h2>
        <form onSubmit={handleSubmit} className="mt-4 space-y-5">
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <ColorCombobox
              id="litter-sire-color"
              label="父猫カラー"
              value={sireColor}
              onValueChange={setSireColor}
              onCommit={setSireColor}
              colors={colors}
              recent={[]}
              placeholder="例: Blue"
              suggestionLayout="inline"
            />
            <ColorCombobox
              id="litter-dam-color"
              label="母猫カラー"
              value={damColor}
              onValueChange={setDamColor}
              onCommit={setDamColor}
              colors={colors}
              recent={[]}
              placeholder="例: Red Tabby"
              suggestionLayout="inline"
            />
          </div>

          <ColorCombobox
            id="litter-breed"
            label="猫種 (任意)"
            value={breed}
            onValueChange={setBreed}
            onCommit={setBreed}
            colors={breedItems}
            recent={[]}
            placeholder="例: British Shorthair"
          />

          <div className="space-y-3">
            <div className="flex items-center justify-between gap-3">
              <h3 className="text-sm font-semibold text-slate-700">子猫</h3>
              <button type="button" className={secondaryButtonClass} onClick={addKitten}>
                ＋ 子猫を追加
              </button>
            </div>
            {kittens.map((kitten, index) => (
              <div
                key={kitten.id}
                className="grid grid-cols-1 gap-3 rounded-md border border-slate-200 p-3 md:grid-cols-[1fr_130px_1.4fr_auto]"
              >
                <div className="space-y-1">
                  <label htmlFor={`kitten-name-${kitten.id}`} className={labelClass}>
                    子猫名 {index + 1}
                  </label>
                  <input
                    id={`kitten-name-${kitten.id}`}
                    className={inputClass}
                    value={kitten.name}
                    onChange={(event) => updateKitten(kitten.id, { name: event.target.value })}
                    placeholder="任意"
                  />
                </div>
                <div className="space-y-1">
                  <label htmlFor={`kitten-sex-${kitten.id}`} className={labelClass}>
                    性別
                  </label>
                  <select
                    id={`kitten-sex-${kitten.id}`}
                    className={inputClass}
                    value={kitten.sex}
                    onChange={(event) =>
                      updateKitten(kitten.id, {
                        sex: event.target.value === "male" ? "male" : "female",
                      })
                    }
                  >
                    <option value="female">♀ メス</option>
                    <option value="male">♂ オス</option>
                  </select>
                </div>
                <ColorCombobox
                  id={`kitten-color-${kitten.id}`}
                  label="子猫カラー"
                  value={kitten.color}
                  onValueChange={(value) => updateKitten(kitten.id, { color: value })}
                  onCommit={(value) => updateKitten(kitten.id, { color: value })}
                  colors={colors}
                  recent={[]}
                  placeholder="例: Blue Patched Tabby"
                  suggestionLayout="inline"
                />
                <button
                  type="button"
                  className={`${secondaryButtonClass} self-end whitespace-nowrap`}
                  onClick={() => removeKitten(kitten.id)}
                >
                  削除
                </button>
              </div>
            ))}
          </div>

          <button
            type="submit"
            disabled={!canSubmit}
            className="rounded-md bg-slate-800 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {loading ? "推定中…" : "推定する"}
          </button>
        </form>

        {error && (
          <div className="mt-4 rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">
            {error}
          </div>
        )}
      </section>

      {result && <ResultPanel data={result} />}
    </div>
  );
}
