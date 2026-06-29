"use client";

import { useEffect, useMemo, useState, type FormEvent } from "react";
import {
  fetchBreedColors,
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
import {
  canonicalColorValue,
  filterColorsByAllowedNames,
  resolveExactColorOption,
} from "@/lib/colorMatch";
import type {
  ColorOption,
  RegisteredCat,
  ReverseLookupResponse,
} from "@/lib/schema";
import { carriersText } from "./format";

// 目標カラーの子猫性別。"any" は未指定。
export type TargetSex = "any" | RegisteredCat["sex"];

// 1 頭につき複数色を登録するための追加カラー入力欄 (id で行を識別する)。
export type AdditionalColorInput = {
  id: string;
  value: string;
};

// 登録猫の一意 ID を生成する。crypto.randomUUID があれば優先する。
function createRegisteredCatId(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }
  return `${Date.now()}-${Math.round(Math.random() * 100000)}`;
}

// 追加カラー入力欄の行 ID。
function createAdditionalColorInputId(): string {
  return `color-${createRegisteredCatId()}`;
}

function repository(): RegisteredCatRepository {
  return createLocalRegisteredCatRepository();
}

// 手入力名が無いときの自動命名 (「Blueの父」)。同名衝突時は連番を付ける。
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

// 主カラー + 追加カラーを、トリム・空除去・重複排除した配列にする。
function splitColorEntries(
  primaryColor: string,
  additionalColors: AdditionalColorInput[],
): string[] {
  const entries = [primaryColor, ...additionalColors.map((entry) => entry.value)]
    .map((entry) => entry.trim())
    .filter((entry) => entry.length > 0);
  return [...new Set(entries)];
}

// 入力色を canonical 表記へ正規化し、重複を排除する。
function canonicalColorEntries(entries: string[], colors: ColorOption[]): string[] {
  return [...new Set(entries.map((entry) => canonicalColorValue(colors, entry)))];
}

// 「目標カラーから探す」画面の状態・副作用・操作を集約したコンテナフック。
// UI コンポーネントを表示に専念させ、ロジックを単体テスト可能にするために分離する。
export function useTargetColorSearch() {
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
  const [registrationBreedAllowedColors, setRegistrationBreedAllowedColors] = useState<string[]>([]);
  const [editBreedAllowedColors, setEditBreedAllowedColors] = useState<string[]>([]);
  const [targetBreedAllowedColors, setTargetBreedAllowedColors] = useState<string[]>([]);
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

  useEffect(() => {
    const trimmedBreed = breed.trim();
    if (!trimmedBreed) {
      setRegistrationBreedAllowedColors([]);
      return;
    }
    let alive = true;
    fetchBreedColors(trimmedBreed).then((list) => {
      if (alive) setRegistrationBreedAllowedColors(list);
    });
    return () => {
      alive = false;
    };
  }, [breed]);

  useEffect(() => {
    const trimmedBreed = editBreed.trim();
    if (!trimmedBreed) {
      setEditBreedAllowedColors([]);
      return;
    }
    let alive = true;
    fetchBreedColors(trimmedBreed).then((list) => {
      if (alive) setEditBreedAllowedColors(list);
    });
    return () => {
      alive = false;
    };
  }, [editBreed]);

  const targetBreed = useMemo(() => {
    const uniqueBreeds = [
      ...new Set(
        cats
          .map((cat) => cat.breed?.trim())
          .filter((catBreed): catBreed is string => Boolean(catBreed)),
      ),
    ];
    return uniqueBreeds.length === 1 ? uniqueBreeds[0] : "";
  }, [cats]);

  useEffect(() => {
    if (!targetBreed) {
      setTargetBreedAllowedColors([]);
      return;
    }
    let alive = true;
    fetchBreedColors(targetBreed).then((list) => {
      if (alive) setTargetBreedAllowedColors(list);
    });
    return () => {
      alive = false;
    };
  }, [targetBreed]);

  const registrationBreedColors = useMemo(
    () => filterColorsByAllowedNames(colors, registrationBreedAllowedColors),
    [colors, registrationBreedAllowedColors],
  );
  const editBreedColors = useMemo(
    () => filterColorsByAllowedNames(colors, editBreedAllowedColors),
    [colors, editBreedAllowedColors],
  );
  const targetColors = useMemo(
    () => filterColorsByAllowedNames(colors, targetBreedAllowedColors),
    [colors, targetBreedAllowedColors],
  );
  const maleRegistrationColors = useMemo(
    () =>
      registrationBreedColors.filter(
        (colorOption) => colorOption.sex_restriction !== "female_only",
      ),
    [registrationBreedColors],
  );
  const maleEditColors = useMemo(
    () =>
      editBreedColors.filter((colorOption) => colorOption.sex_restriction !== "female_only"),
    [editBreedColors],
  );
  const registrationColors = sex === "male" ? maleRegistrationColors : registrationBreedColors;
  const editColors = editSex === "male" ? maleEditColors : editBreedColors;
  const sires = useMemo(() => cats.filter((cat) => cat.sex === "male"), [cats]);
  const dams = useMemo(() => cats.filter((cat) => cat.sex === "female"), [cats]);
  const colorsToRegister = splitColorEntries(color, additionalColors);

  function saveCats(nextCats: RegisteredCat[]) {
    setCats(nextCats);
    catRepository.save(nextCats);
    setRegistrationError(null);
    setResult(null);
  }

  // 父候補にメス限定カラーが含まれていないか検証する。問題があれば日本語メッセージを返す。
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
    setAdditionalColors((entries) => entries.filter((entry) => entry.id !== id));
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

  return {
    // 登録フォーム
    name,
    setName,
    sex,
    setSex,
    color,
    setColor,
    additionalColors,
    addColorInput,
    updateAdditionalColor,
    removeAdditionalColor,
    breed,
    setBreed,
    carriers,
    setCarriers,
    colorsToRegister,
    registrationColors,
    handleAddCat,
    registrationError,
    // 一覧・編集
    cats,
    sires,
    dams,
    removeCat,
    editingId,
    editName,
    setEditName,
    editSex,
    setEditSex,
    editColor,
    setEditColor,
    editBreed,
    setEditBreed,
    editCarriers,
    setEditCarriers,
    editColors,
    startEdit,
    cancelEdit,
    handleSaveEdit,
    // マスタ
    colors,
    targetColors,
    breedItems,
    // 目標・検索
    targetColor,
    setTargetColor,
    targetSex,
    setTargetSex,
    loading,
    error,
    result,
    handleSearch,
  };
}
