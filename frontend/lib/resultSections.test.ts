import { afterEach, describe, expect, it, vi } from "vitest";

import {
  DEFAULT_SECTION_ORDER,
  loadSectionOpen,
  loadSectionOrder,
  saveSectionOpen,
  saveSectionOrder,
  type SectionId,
} from "./resultSections";

// lib テストは node 環境 (DOM非依存) のため、localStorage 互換の最小スタブを global に注入する
// (registeredCatRepository.test.ts などと同じ方針)。
const ORDER_KEY = "cbs:resultSectionOrder";
const OPEN_KEY = "cbs:resultSectionOpen";

function stubStorage(initial: Record<string, string> = {}): void {
  const store: Record<string, string> = { ...initial };
  vi.stubGlobal("localStorage", {
    getItem: (key: string) => (key in store ? store[key] : null),
    setItem: (key: string, value: string) => {
      store[key] = value;
    },
    removeItem: (key: string) => {
      delete store[key];
    },
    clear: () => {
      for (const key of Object.keys(store)) delete store[key];
    },
  });
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("resultSections 並び順", () => {
  it("未保存なら既定順を返す", () => {
    stubStorage();
    expect(loadSectionOrder()).toEqual([...DEFAULT_SECTION_ORDER]);
  });

  it("save→load で並び順が往復する", () => {
    stubStorage();
    const custom: SectionId[] = [
      "distribution",
      "conditional",
      "confirmed",
      "normalNote",
      "genetics",
    ];
    saveSectionOrder(custom);
    expect(loadSectionOrder()).toEqual(custom);
  });

  it("未知IDは除外し、欠落IDは既定順で末尾補完する", () => {
    stubStorage({ [ORDER_KEY]: JSON.stringify(["genetics", "bogus", "confirmed"]) });
    expect(loadSectionOrder()).toEqual([
      "genetics",
      "confirmed",
      "distribution",
      "conditional",
      "normalNote",
    ]);
  });

  it("重複IDは最初の1つだけ残す", () => {
    stubStorage({
      [ORDER_KEY]: JSON.stringify(["confirmed", "confirmed", "distribution"]),
    });
    const order = loadSectionOrder();
    expect(order.filter((id) => id === "confirmed")).toHaveLength(1);
    expect(order).toEqual([
      "confirmed",
      "distribution",
      "conditional",
      "normalNote",
      "genetics",
    ]);
  });

  it("壊れたJSON・配列でない値は既定順にフォールバックする", () => {
    stubStorage({ [ORDER_KEY]: "{not json" });
    expect(loadSectionOrder()).toEqual([...DEFAULT_SECTION_ORDER]);
    stubStorage({ [ORDER_KEY]: JSON.stringify("distribution") });
    expect(loadSectionOrder()).toEqual([...DEFAULT_SECTION_ORDER]);
  });
});

describe("resultSections 展開状態", () => {
  it("未保存なら空 (全非展開)", () => {
    stubStorage();
    expect(loadSectionOpen()).toEqual({});
  });

  it("save→load で展開状態が往復する", () => {
    stubStorage();
    saveSectionOpen({ distribution: true, confirmed: false });
    expect(loadSectionOpen()).toEqual({ distribution: true, confirmed: false });
  });

  it("未知キーは除外する", () => {
    stubStorage({ [OPEN_KEY]: JSON.stringify({ distribution: true, bogus: true }) });
    expect(loadSectionOpen()).toEqual({ distribution: true });
  });

  it("boolean以外の値を含むと Zod で弾いて空になる", () => {
    stubStorage({ [OPEN_KEY]: JSON.stringify({ distribution: "yes" }) });
    expect(loadSectionOpen()).toEqual({});
  });
});
