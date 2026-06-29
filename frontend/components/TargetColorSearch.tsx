"use client";

import { useEffect, useMemo, useState, type FormEvent } from "react";
import {
  fetchBreeds,
  fetchColors,
  searchTargetColor,
  type ReverseLookupOutcome,
} from "@/lib/api";
import { BREED_READING_JA } from "@/lib/breedReadingJa";
import { parseCarriers } from "@/lib/carriers";
import {
  createLocalRegisteredCatRepository,
  type RegisteredCatRepository,
} from "@/lib/registeredCatRepository";
import { canonicalColorValue, resolveExactColorOption } from "@/lib/colorMatch";
import type {
  ColorOption,
  RegisteredCat,
  ReverseLookupResponse,
} from "@/lib/schema";
import { ColorCombobox } from "./ColorCombobox";
import { ResultsView } from "./targetColorSearch/ResultsView";
import { carriersText, sexLabel } from "./targetColorSearch/format";

type TargetSex = "any" | RegisteredCat["sex"];
type AdditionalColorInput = {
  id: string;
  value: string;
};

const inputClass =
  "w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm shadow-sm focus:border-slate-500 focus:outline-none focus:ring-1 focus:ring-slate-500";
const labelClass = "block text-sm font-medium text-slate-700";
const secondaryButtonClass =
  "rounded-md border border-slate-300 bg-white px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50";

function createRegisteredCatId(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }
  return `${Date.now()}-${Math.round(Math.random() * 100000)}`;
}

function createAdditionalColorInputId(): string {
  return `color-${createRegisteredCatId()}`;
}

function repository(): RegisteredCatRepository {
  return createLocalRegisteredCatRepository();
}

function autoRegisteredName(
  color: string,
  sex: RegisteredCat["sex"],
  usedNames: Set<string>,
): string {
  const base = `${color}の${sex === "male" ? "父" : "母"}`;
  if (!usedNames.has(base)) {
    usedNames.add(base);
    return base;
  }
  let suffix = 2;
  while (usedNames.has(`${base}${suffix}`)) suffix += 1;
  const name = `${base}${suffix}`;
  usedNames.add(name);
  return name;
}

function splitColorEntries(
  primaryColor: string,
  additionalColors: AdditionalColorInput[],
): string[] {
  const entries = [primaryColor, ...additionalColors.map((entry) => entry.value)]
    .map((entry) => entry.trim())
    .filter((entry) => entry.length > 0);
  return [...new Set(entries)];
}

function canonicalColorEntries(entries: string[], colors: ColorOption[]): string[] {
  return [...new Set(entries.map((entry) => canonicalColorValue(colors, entry)))];
}

export function TargetColorSearch() {
  const [cats, setCats] = useState<RegisteredCat[]>([]);
  const [name, setName] = useState("");
  const [sex, setSex] = useState<RegisteredCat["sex"]>("female");
  const [color, setColor] = useState("");
  const [additionalColors, setAdditionalColors] = useState<AdditionalColorInput[]>([]);
  const [breed, setBreed] = useState("");
  const [carriers, setCarriers] = useState("");
  const [targetColor, setTargetColor] = useState("");
  const [targetSex, setTargetSex] = useState<TargetSex>("any");
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editName, setEditName] = useState("");
  const [editSex, setEditSex] = useState<RegisteredCat["sex"]>("female");
  const [editColor, setEditColor] = useState("");
  const [editBreed, setEditBreed] = useState("");
  const [editCarriers, setEditCarriers] = useState("");
  const [colors, setColors] = useState<ColorOption[]>([]);
  const [breedItems, setBreedItems] = useState<ColorOption[]>([]);
  const [loading, setLoading] = useState(false);
  const [registrationError, setRegistrationError] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<ReverseLookupResponse | null>(null);

  const catRepository = useMemo(() => repository(), []);

  useEffect(() => {
    setCats(catRepository.load());
  }, [catRepository]);

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

  const maleColors = useMemo(
    () => colors.filter((colorOption) => colorOption.sex_restriction !== "female_only"),
    [colors],
  );
  const registrationColors = sex === "male" ? maleColors : colors;
  const editColors = editSex === "male" ? maleColors : colors;
  const sires = useMemo(() => cats.filter((cat) => cat.sex === "male"), [cats]);
  const dams = useMemo(() => cats.filter((cat) => cat.sex === "female"), [cats]);
  const colorsToRegister = splitColorEntries(color, additionalColors);

  function saveCats(nextCats: RegisteredCat[]) {
    setCats(nextCats);
    catRepository.save(nextCats);
    setRegistrationError(null);
    setResult(null);
  }

  function maleRestrictedMessage(
    selectedSex: RegisteredCat["sex"],
    entries: string[],
  ): string | null {
    if (selectedSex !== "male") return null;
    const invalidColors: string[] = [];
    for (const entry of entries) {
      const resolvedColor = resolveExactColorOption(colors, entry);
      if (resolvedColor?.sex_restriction === "female_only") {
        invalidColors.push(resolvedColor.value);
      }
    }
    if (invalidColors.length === 0) return null;
    return `父候補には指定できないメス限定カラーがあります: ${[...new Set(invalidColors)].join(", ")}`;
  }

  function handleAddCat(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (colorsToRegister.length === 0) return;
    const canonicalColors = canonicalColorEntries(colorsToRegister, colors);
    const restrictedMessage = maleRestrictedMessage(sex, canonicalColors);
    if (restrictedMessage) {
      setRegistrationError(restrictedMessage);
      return;
    }

    const trimmedBreed = breed.trim();
    const parsedCarriers = parseCarriers(carriers);
    const usedNames = new Set(cats.map((cat) => cat.name));
    const trimmedName = name.trim();
    const nextCats = canonicalColors.map((entryColor) => {
      const shouldUseManualName = canonicalColors.length === 1 && trimmedName.length > 0;
      const nextCat: RegisteredCat = {
        id: createRegisteredCatId(),
        name: shouldUseManualName ? trimmedName : autoRegisteredName(entryColor, sex, usedNames),
        sex,
        color: entryColor,
      };
      if (trimmedBreed) nextCat.breed = trimmedBreed;
      if (parsedCarriers) nextCat.carriers = parsedCarriers;
      return nextCat;
    });
    saveCats([...nextCats, ...cats]);
    setName("");
    setColor("");
    setAdditionalColors([]);
    setBreed("");
    setCarriers("");
  }

  function addColorInput() {
    setAdditionalColors((entries) => [
      ...entries,
      { id: createAdditionalColorInputId(), value: "" },
    ]);
  }

  function updateAdditionalColor(id: string, value: string) {
    setAdditionalColors((entries) =>
      entries.map((entry) => (entry.id === id ? { ...entry, value } : entry)),
    );
  }

  function removeAdditionalColor(id: string) {
    setAdditionalColors((entries) =>
      entries.filter((entry) => entry.id !== id),
    );
  }

  function removeCat(id: string) {
    saveCats(cats.filter((cat) => cat.id !== id));
    if (editingId === id) setEditingId(null);
  }

  function startEdit(cat: RegisteredCat) {
    setEditingId(cat.id);
    setEditName(cat.name);
    setEditSex(cat.sex);
    setEditColor(cat.color);
    setEditBreed(cat.breed ?? "");
    setEditCarriers(carriersText(cat.carriers));
  }

  function cancelEdit() {
    setEditingId(null);
    setEditName("");
    setEditColor("");
    setEditBreed("");
    setEditCarriers("");
  }

  function handleSaveEdit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!editingId) return;
    const trimmedName = editName.trim();
    const trimmedColor = editColor.trim();
    if (!trimmedName || !trimmedColor) return;
    const canonicalColor = canonicalColorValue(colors, trimmedColor);
    const restrictedMessage = maleRestrictedMessage(editSex, [canonicalColor]);
    if (restrictedMessage) {
      setRegistrationError(restrictedMessage);
      return;
    }

    const updatedCat: RegisteredCat = {
      id: editingId,
      name: trimmedName,
      sex: editSex,
      color: canonicalColor,
    };
    const trimmedBreed = editBreed.trim();
    if (trimmedBreed) updatedCat.breed = trimmedBreed;
    const parsedCarriers = parseCarriers(editCarriers);
    if (parsedCarriers) updatedCat.carriers = parsedCarriers;

    saveCats(cats.map((cat) => (cat.id === editingId ? updatedCat : cat)));
    cancelEdit();
  }

  async function handleSearch() {
    if (!targetColor.trim() || cats.length < 2) return;
    setLoading(true);
    setError(null);
    const targetSexValue = targetSex === "any" ? undefined : targetSex;
    const outcome: ReverseLookupOutcome = await searchTargetColor({
      target_color: targetColor.trim(),
      target_sex: targetSexValue,
      cats,
      limit: 20,
    });
    if (outcome.ok) {
      setResult(outcome.data);
    } else {
      setResult(null);
      setError(outcome.message);
    }
    setLoading(false);
  }

  function renderCatList(groupCats: RegisteredCat[]) {
    if (groupCats.length === 0) {
      return <p className="px-4 py-3 text-sm text-slate-500">まだ登録されていません。</p>;
    }
    return (
      <ul className="divide-y divide-slate-100">
        {groupCats.map((cat) => (
          <li key={cat.id} className="px-4 py-3 text-sm">
            {editingId === cat.id ? (
              <form onSubmit={handleSaveEdit} className="grid grid-cols-1 gap-3 md:grid-cols-2">
                <div className="space-y-1">
                  <label htmlFor={`edit-name-${cat.id}`} className={labelClass}>
                    登録名
                  </label>
                  <input
                    id={`edit-name-${cat.id}`}
                    className={inputClass}
                    value={editName}
                    onChange={(event) => setEditName(event.target.value)}
                  />
                </div>
                <div className="space-y-1">
                  <label htmlFor={`edit-sex-${cat.id}`} className={labelClass}>
                    性別
                  </label>
                  <select
                    id={`edit-sex-${cat.id}`}
                    className={inputClass}
                    value={editSex}
                    onChange={(event) => setEditSex(event.target.value === "male" ? "male" : "female")}
                  >
                    <option value="female">♀ 母猫候補</option>
                    <option value="male">♂ 父猫候補</option>
                  </select>
                </div>
                <ColorCombobox
                  id={`edit-color-${cat.id}`}
                  label="毛色"
                  value={editColor}
                  onValueChange={setEditColor}
                  onCommit={setEditColor}
                  colors={editColors}
                  recent={[]}
                  suggestionLayout="inline"
                />
                <ColorCombobox
                  id={`edit-breed-${cat.id}`}
                  label="猫種 (任意)"
                  value={editBreed}
                  onValueChange={setEditBreed}
                  onCommit={setEditBreed}
                  colors={breedItems}
                  recent={[]}
                />
                <div className="space-y-1 md:col-span-2">
                  <label htmlFor={`edit-carriers-${cat.id}`} className={labelClass}>
                    確認済み因子 (任意)
                  </label>
                  <input
                    id={`edit-carriers-${cat.id}`}
                    className={inputClass}
                    value={editCarriers}
                    onChange={(event) => setEditCarriers(event.target.value)}
                    placeholder="例: B:B/b, D:D/d"
                  />
                </div>
                <div className="flex gap-2 md:col-span-2">
                  <button
                    type="submit"
                    className="rounded-md bg-slate-800 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-50"
                    disabled={!editName.trim() || !editColor.trim()}
                  >
                    更新する
                  </button>
                  <button type="button" className={secondaryButtonClass} onClick={cancelEdit}>
                    キャンセル
                  </button>
                </div>
              </form>
            ) : (
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <p className="font-medium text-slate-800">
                    {cat.name} <span className="text-slate-400">{sexLabel(cat.sex)}</span>
                  </p>
                  <p className="text-xs text-slate-500">
                    {cat.color}
                    {cat.breed ? ` / ${cat.breed}` : ""}
                    {cat.carriers ? ` / 確認済み因子: ${carriersText(cat.carriers)}` : ""}
                  </p>
                </div>
                <div className="flex gap-2">
                  <button type="button" className={secondaryButtonClass} onClick={() => startEdit(cat)}>
                    編集
                  </button>
                  <button type="button" className={secondaryButtonClass} onClick={() => removeCat(cat.id)}>
                    登録から外す
                  </button>
                </div>
              </div>
            )}
          </li>
        ))}
      </ul>
    );
  }

  return (
    <div className="space-y-6">
      <section className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
        <h2 className="text-lg font-semibold text-slate-800">両親猫のカラー登録</h2>
        <form onSubmit={handleAddCat} className="mt-4 grid grid-cols-1 gap-4 md:grid-cols-2">
          <div className="space-y-1">
            <label htmlFor="registered-cat-name" className={labelClass}>
              登録名
            </label>
            <input
              id="registered-cat-name"
              className={inputClass}
              value={name}
              onChange={(event) => setName(event.target.value)}
              placeholder="例: 青系の父"
            />
          </div>
          <div className="space-y-1">
            <label htmlFor="registered-cat-sex" className={labelClass}>
              性別
            </label>
            <select
              id="registered-cat-sex"
              className={inputClass}
              value={sex}
              onChange={(event) => setSex(event.target.value === "male" ? "male" : "female")}
            >
              <option value="female">♀ 母猫候補</option>
              <option value="male">♂ 父猫候補</option>
            </select>
          </div>
          <div className="space-y-3 md:col-span-2">
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
              <div className="grid grid-cols-[minmax(0,1fr)_auto] items-start gap-2">
                <ColorCombobox
                  id="registered-cat-color"
                  label="毛色"
                  value={color}
                  onValueChange={setColor}
                  onCommit={setColor}
                  colors={registrationColors}
                  recent={[]}
                  placeholder="例: Blue / Chocolate"
                  suggestionLayout="inline"
                />
                <button
                  type="button"
                  className={`${secondaryButtonClass} mt-6 whitespace-nowrap`}
                  onClick={addColorInput}
                >
                  ＋ カラー追加
                </button>
              </div>
              <ColorCombobox
                id="registered-cat-breed"
                label="猫種 (任意)"
                value={breed}
                onValueChange={setBreed}
                onCommit={setBreed}
                colors={breedItems}
                recent={[]}
                placeholder="例: British Shorthair"
              />
            </div>
            {additionalColors.map((entryColor, index) => (
              <div
                key={entryColor.id}
                className="grid grid-cols-[minmax(0,1fr)_auto] items-start gap-2"
              >
                <ColorCombobox
                  id={`registered-cat-additional-color-${entryColor.id}`}
                  label={`追加カラー ${index + 1}`}
                  value={entryColor.value}
                  onValueChange={(value) => updateAdditionalColor(entryColor.id, value)}
                  onCommit={(value) => updateAdditionalColor(entryColor.id, value)}
                  colors={registrationColors}
                  recent={[]}
                  placeholder="例: Lilac"
                  suggestionLayout="inline"
                />
                <button
                  type="button"
                  className={`${secondaryButtonClass} mt-6 whitespace-nowrap`}
                  onClick={() => removeAdditionalColor(entryColor.id)}
                >
                  削除
                </button>
              </div>
            ))}
          </div>
          <div className="space-y-1 md:col-span-2">
            <label htmlFor="registered-cat-carriers" className={labelClass}>
              確認済み因子 (任意)
            </label>
            <input
              id="registered-cat-carriers"
              className={inputClass}
              value={carriers}
              onChange={(event) => setCarriers(event.target.value)}
              placeholder="例: B:B/b, D:D/d"
            />
          </div>
          <div className="md:col-span-2">
            <button
              type="submit"
              className="rounded-md bg-slate-800 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-50"
              disabled={colorsToRegister.length === 0}
            >
              登録する
            </button>
          </div>
        </form>
        {registrationError && (
          <div className="mt-4 rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">
            {registrationError}
          </div>
        )}

        <div className="mt-5 space-y-2">
          <h3 className="text-sm font-semibold text-slate-700">自舎カラー構成</h3>
          {cats.length === 0 ? (
            <p className="text-sm text-slate-500">
              父候補・母候補のカラーを追加すると、目標カラーの交配候補を検索できます。
            </p>
          ) : (
            <div className="space-y-2">
              <details className="rounded-md border border-slate-200 bg-white">
                <summary className="flex cursor-pointer items-center justify-between px-4 py-3 text-sm font-semibold text-slate-700">
                  <span>父候補</span>
                  <span className="text-slate-400">{sires.length} 件</span>
                </summary>
                {renderCatList(sires)}
              </details>
              <details className="rounded-md border border-slate-200 bg-white">
                <summary className="flex cursor-pointer items-center justify-between px-4 py-3 text-sm font-semibold text-slate-700">
                  <span>母候補</span>
                  <span className="text-slate-400">{dams.length} 件</span>
                </summary>
                {renderCatList(dams)}
              </details>
            </div>
          )}
        </div>
      </section>

      <section className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
        <h2 className="text-lg font-semibold text-slate-800">目標カラーの選択</h2>
        <div className="mt-4 grid grid-cols-1 gap-4 md:grid-cols-[1fr_180px_auto] md:items-end">
          <ColorCombobox
            id="target-color"
            label="目標カラー"
            value={targetColor}
            onValueChange={setTargetColor}
            onCommit={setTargetColor}
            colors={colors}
            recent={[]}
            placeholder="例: Lilac / Cinnamon Golden Tabby"
          />
          <div className="space-y-1">
            <label htmlFor="target-sex" className={labelClass}>
              子猫の性別 (任意)
            </label>
            <select
              id="target-sex"
              className={inputClass}
              value={targetSex}
              onChange={(event) => {
                const value = event.target.value;
                setTargetSex(value === "male" || value === "female" ? value : "any");
              }}
            >
              <option value="any">指定なし</option>
              <option value="male">♂ オス</option>
              <option value="female">♀ メス</option>
            </select>
          </div>
          <button
            type="button"
            onClick={handleSearch}
            disabled={!targetColor.trim() || cats.length < 2 || loading}
            className="rounded-md bg-slate-800 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {loading ? "検索中…" : "交配候補を検索"}
          </button>
        </div>
        {error && (
          <div className="mt-4 rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">
            {error}
          </div>
        )}
      </section>

      {result && (
        <section className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
          <ResultsView data={result} />
        </section>
      )}
    </div>
  );
}
