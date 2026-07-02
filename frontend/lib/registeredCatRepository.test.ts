import { afterEach, describe, expect, it, vi } from "vitest";

import { createLocalRegisteredCatRepository } from "./registeredCatRepository";
import type { RegisteredCat } from "./schema";

// jsdom を導入せず、localStorage 互換の最小スタブを window として注入する。
type StorageStub = {
  getItem: (key: string) => string | null;
  setItem: (key: string, value: string) => void;
};

function makeStorage(initial: Record<string, string> = {}): StorageStub & { store: Record<string, string> } {
  const store: Record<string, string> = { ...initial };
  return {
    store,
    getItem: (key) => (key in store ? store[key] : null),
    setItem: (key, value) => {
      store[key] = value;
    },
  };
}

function stubWindow(storage: StorageStub): void {
  vi.stubGlobal("window", { localStorage: storage });
}

const CAT: RegisteredCat = { id: "1", name: "クロ", sex: "male", color: "Black" };

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("createLocalRegisteredCatRepository", () => {
  it("未保存なら load は空配列", async () => {
    stubWindow(makeStorage());
    await expect(createLocalRegisteredCatRepository().load()).resolves.toEqual([]);
  });

  it("save→load の往復で同じ猫リストを復元する", async () => {
    stubWindow(makeStorage());
    const repo = createLocalRegisteredCatRepository();
    await repo.save([CAT]);
    await expect(repo.load()).resolves.toEqual([CAT]);
  });

  it("旧登録猫キーの壊れたJSONは空配列にフォールバックする", async () => {
    stubWindow(makeStorage({ "cbs:registeredCats": "{壊れた" }));
    await expect(createLocalRegisteredCatRepository().load()).resolves.toEqual([]);
  });

  it("旧登録猫キーのスキーマ不一致データは空配列", async () => {
    stubWindow(makeStorage({ "cbs:registeredCats": JSON.stringify([{ wrong: true }]) }));
    await expect(createLocalRegisteredCatRepository().load()).resolves.toEqual([]);
  });

  it("旧登録猫キーの正しいデータはStorage v1として読み込める", async () => {
    stubWindow(makeStorage({ "cbs:registeredCats": JSON.stringify([CAT]) }));
    await expect(createLocalRegisteredCatRepository().load()).resolves.toEqual([CAT]);
  });

  it("save が例外を投げても呼び出し側へ伝播しない", async () => {
    stubWindow({
      getItem: () => null,
      setItem: () => {
        throw new Error("quota exceeded");
      },
    });
    await expect(createLocalRegisteredCatRepository().save([CAT])).resolves.toBeUndefined();
  });
});
