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
  it("未保存なら load は空配列", () => {
    stubWindow(makeStorage());
    expect(createLocalRegisteredCatRepository().load()).toEqual([]);
  });

  it("save→load の往復で同じ猫リストを復元する", () => {
    stubWindow(makeStorage());
    const repo = createLocalRegisteredCatRepository();
    repo.save([CAT]);
    expect(repo.load()).toEqual([CAT]);
  });

  it("壊れたJSONは空配列にフォールバックする", () => {
    stubWindow(makeStorage({ "cbs:registeredCats": "{壊れた" }));
    expect(createLocalRegisteredCatRepository().load()).toEqual([]);
  });

  it("スキーマ不一致のデータは空配列", () => {
    stubWindow(makeStorage({ "cbs:registeredCats": JSON.stringify([{ wrong: true }]) }));
    expect(createLocalRegisteredCatRepository().load()).toEqual([]);
  });

  it("save が例外を投げても呼び出し側へ伝播しない", () => {
    stubWindow({
      getItem: () => null,
      setItem: () => {
        throw new Error("quota exceeded");
      },
    });
    expect(() => createLocalRegisteredCatRepository().save([CAT])).not.toThrow();
  });
});
