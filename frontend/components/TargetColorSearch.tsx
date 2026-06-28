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
import type {
  ColorOption,
  RegisteredCat,
  ResultEntry,
  ReverseLookupCandidate,
  ReverseLookupResponse,
} from "@/lib/schema";
import { ColorCombobox } from "./ColorCombobox";

type TargetSex = "any" | RegisteredCat["sex"];

const CATEGORIES = [
  "確定で期待できる",
  "条件付きで期待できる",
  "現在の情報では判定が難しい",
  "現在の登録情報では確認できない",
] as const;

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

function repository(): RegisteredCatRepository {
  return createLocalRegisteredCatRepository();
}

function formatPct(value: number): string {
  return `${value.toFixed(value % 1 === 0 ? 0 : 1)}%`;
}

function sexLabel(sex: RegisteredCat["sex"]): string {
  return sex === "male" ? "♂ 父猫候補" : "♀ 母猫候補";
}

function targetSexLabel(sex: ReverseLookupResponse["target_sex"]): string {
  if (sex === "male") return "♂ オス";
  if (sex === "female") return "♀ メス";
  return "指定なし";
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

function colorRows(rows: ResultEntry[]): string {
  if (rows.length === 0) return "現在の計算範囲では表示できるカラーがありません。";
  return rows
    .slice(0, 8)
    .map((row) => `${row.sex === "Female" ? "♀" : "♂"} ${row.color} ${formatPct(row.probability_pct)}`)
    .join(" / ");
}

function carriersText(carriers: RegisteredCat["carriers"]): string {
  if (!carriers) return "";
  return Object.entries(carriers)
    .map(([locus, genotype]) => `${locus}:${genotype}`)
    .join(", ");
}

function splitColorEntries(primaryColor: string, bulkColors: string): string[] {
  const entries = [primaryColor, ...bulkColors.split(/[\n,、]+/)]
    .map((entry) => entry.trim())
    .filter((entry) => entry.length > 0);
  return [...new Set(entries)];
}

function CandidateCard({
  candidate,
  index,
}: {
  candidate: ReverseLookupCandidate;
  index: number;
}) {
  const summaryProbability =
    candidate.confirmed_probability_pct > 0
      ? candidate.confirmed_probability_pct
      : candidate.conditional_max_probability_pct;

  return (
    <details className="rounded-md border border-slate-200 bg-white">
      <summary className="flex cursor-pointer flex-wrap items-center justify-between gap-3 px-4 py-3">
        <div>
          <p className="text-xs font-medium text-slate-400">組み合わせ {index + 1}</p>
          <h4 className="text-base font-semibold text-slate-800">
            {candidate.sire.name} × {candidate.dam.name}
          </h4>
          <p className="mt-1 text-xs text-slate-500">
            {candidate.sire.color} ♂ / {candidate.dam.color} ♀
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className="rounded bg-slate-100 px-2 py-1 text-xs font-medium text-slate-600">
            {candidate.category}
          </span>
          <span className="text-lg font-semibold tabular-nums text-slate-800">
            {formatPct(summaryProbability)}
          </span>
        </div>
      </summary>

      <div className="border-t border-slate-100 p-4">
        <div className="grid grid-cols-2 gap-3">
          <div className="rounded-md bg-emerald-50 p-3">
            <p className="text-xs text-emerald-700">確定確率</p>
            <p className="text-xl font-semibold tabular-nums text-emerald-900">
              {formatPct(candidate.confirmed_probability_pct)}
            </p>
          </div>
          <div className="rounded-md bg-amber-50 p-3">
            <p className="text-xs text-amber-700">条件付き最大確率</p>
            <p className="text-xl font-semibold tabular-nums text-amber-900">
              {formatPct(candidate.conditional_max_probability_pct)}
            </p>
          </div>
        </div>

        <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-2">
          <InfoList title="成立条件" items={candidate.establishment_conditions} />
          <InfoList
            title="確認が必要な条件"
            items={
              candidate.confirmation_needed.length > 0
                ? candidate.confirmation_needed
                : ["追加確認なしで評価できます。"]
            }
          />
          <InfoList
            title="推奨検査"
            items={
              candidate.recommended_tests.length > 0
                ? candidate.recommended_tests
                : ["現時点で追加検査の提案はありません。"]
            }
          />
          <div className="rounded-md bg-slate-50 p-3 text-sm">
            <p className="font-medium text-slate-700">
              目標カラー以外に生まれる可能性のあるカラー
            </p>
            <p className="mt-1 text-xs leading-5 text-slate-600">
              {colorRows(candidate.other_possible_colors)}
            </p>
          </div>
        </div>

        <div className="mt-4 overflow-hidden rounded-md border border-slate-200">
          <table className="min-w-full text-left text-xs">
            <thead className="bg-slate-50 text-slate-500">
              <tr>
                <th className="px-3 py-2 font-medium">座位</th>
                <th className="px-3 py-2 font-medium">目標条件</th>
                <th className="px-3 py-2 font-medium">父猫側</th>
                <th className="px-3 py-2 font-medium">母猫側</th>
                <th className="px-3 py-2 font-medium">根拠</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {candidate.locus_evidence.map((evidence) => (
                <tr key={evidence.locus}>
                  <td className="px-3 py-2 font-medium text-slate-700">
                    {evidence.locus}
                  </td>
                  <td className="px-3 py-2 text-slate-600">{evidence.target}</td>
                  <td className="px-3 py-2 text-slate-600">{evidence.sire}</td>
                  <td className="px-3 py-2 text-slate-600">{evidence.dam}</td>
                  <td className="px-3 py-2 text-slate-500">{evidence.note}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </details>
  );
}

function InfoList({ title, items }: { title: string; items: string[] }) {
  return (
    <div className="rounded-md bg-slate-50 p-3 text-sm">
      <p className="font-medium text-slate-700">{title}</p>
      <ul className="mt-1 space-y-1 text-xs leading-5 text-slate-600">
        {items.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>
    </div>
  );
}

function NoCandidateAnalysis({ data }: { data: ReverseLookupResponse }) {
  return (
    <div className="rounded-md border border-amber-200 bg-amber-50 p-4 text-sm text-amber-950">
      <p className="font-semibold">
        現在の登録情報では、目標カラーの成立条件を満たす交配候補を確認できません。
      </p>
      <div className="mt-3 grid grid-cols-1 gap-3 md:grid-cols-3">
        <InfoList title="目標カラーに必要な主な条件" items={data.target_conditions} />
        <InfoList title="現在確認できない条件" items={data.unchecked_conditions} />
        <InfoList title="確認するとよい項目" items={data.recommended_checks} />
      </div>
      <p className="mt-3 text-xs leading-5 text-amber-800">
        ゴールデン / ワイドバンド / CORIN系は品種・系統で扱いが複雑なため、
        現在の対応範囲では登録情報と既存ルールに基づく確認結果として表示します。
      </p>
    </div>
  );
}

function ResultsView({ data }: { data: ReverseLookupResponse }) {
  const grouped = CATEGORIES.map((category) => ({
    category,
    candidates: data.candidates.filter((candidate) => candidate.category === category),
  }));

  return (
    <section className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 className="text-lg font-semibold text-slate-800">結果ランキング</h3>
        <span className="rounded bg-slate-100 px-2 py-1 text-xs text-slate-600">
          目標: {targetSexLabel(data.target_sex)} / {data.target_color}
        </span>
      </div>
      {data.candidates.length === 0 && <NoCandidateAnalysis data={data} />}
      {grouped.map((group) => (
        <section key={group.category} className="space-y-3">
          <div className="flex items-center justify-between border-b border-slate-200 pb-1">
            <h4 className="text-sm font-semibold text-slate-700">{group.category}</h4>
            <span className="text-xs text-slate-400">{group.candidates.length} 件</span>
          </div>
          {group.candidates.length > 0 ? (
            group.candidates.map((candidate, index) => (
              <CandidateCard
                key={`${candidate.sire.id}-${candidate.dam.id}-${group.category}`}
                candidate={candidate}
                index={index}
              />
            ))
          ) : (
            <p className="text-sm text-slate-500">
              このカテゴリで確認できる交配候補はまだありません。
            </p>
          )}
        </section>
      ))}
    </section>
  );
}

export function TargetColorSearch() {
  const [cats, setCats] = useState<RegisteredCat[]>([]);
  const [name, setName] = useState("");
  const [sex, setSex] = useState<RegisteredCat["sex"]>("female");
  const [color, setColor] = useState("");
  const [bulkColors, setBulkColors] = useState("");
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

  const femaleOnly = useMemo(
    () =>
      new Set(
        colors
          .filter((colorOption) => colorOption.sex_restriction === "female_only")
          .map((colorOption) => colorOption.value),
      ),
    [colors],
  );
  const maleColors = useMemo(
    () => colors.filter((colorOption) => !femaleOnly.has(colorOption.value)),
    [colors, femaleOnly],
  );
  const registrationColors = sex === "male" ? maleColors : colors;
  const editColors = editSex === "male" ? maleColors : colors;
  const sires = useMemo(() => cats.filter((cat) => cat.sex === "male"), [cats]);
  const dams = useMemo(() => cats.filter((cat) => cat.sex === "female"), [cats]);
  const colorsToRegister = splitColorEntries(color, bulkColors);

  function saveCats(nextCats: RegisteredCat[]) {
    setCats(nextCats);
    catRepository.save(nextCats);
    setResult(null);
  }

  function handleAddCat(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (colorsToRegister.length === 0) return;

    const trimmedBreed = breed.trim();
    const parsedCarriers = parseCarriers(carriers);
    const usedNames = new Set(cats.map((cat) => cat.name));
    const trimmedName = name.trim();
    const nextCats = colorsToRegister.map((entryColor) => {
      const shouldUseManualName = colorsToRegister.length === 1 && trimmedName.length > 0;
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
    setBulkColors("");
    setBreed("");
    setCarriers("");
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

    const updatedCat: RegisteredCat = {
      id: editingId,
      name: trimmedName,
      sex: editSex,
      color: trimmedColor,
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
          <ColorCombobox
            id="registered-cat-color"
            label="毛色"
            value={color}
            onValueChange={setColor}
            onCommit={setColor}
            colors={registrationColors}
            recent={[]}
            placeholder="例: Blue / Chocolate"
          />
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
          <div className="space-y-1 md:col-span-2">
            <label htmlFor="registered-cat-bulk-colors" className={labelClass}>
              まとめて登録するカラー (任意)
            </label>
            <textarea
              id="registered-cat-bulk-colors"
              className={`${inputClass} min-h-24`}
              value={bulkColors}
              onChange={(event) => setBulkColors(event.target.value)}
              placeholder={`例: Blue
Chocolate
Lilac`}
            />
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
