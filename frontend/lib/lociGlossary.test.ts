import { describe, expect, it } from "vitest";

import { DEFAULT_LOCUS_TONE, LOCUS_GLOSSARY, getLocusTone } from "./lociGlossary";

describe("LOCUS_GLOSSARY", () => {
  it("主要な遺伝子座を網羅している", () => {
    for (const locus of ["A", "B", "C", "D", "I", "O", "S", "W", "Mc", "Ta", "Sp", "Wb"]) {
      expect(LOCUS_GLOSSARY[locus]).toBeDefined();
    }
  });

  it("各エントリの symbol はキーと一致し、全フィールドが非空", () => {
    // symbol とキーがずれると、診断情報 (opened_loci 等) との突合で誤表示になるため不変条件として検証。
    for (const [key, info] of Object.entries(LOCUS_GLOSSARY)) {
      expect(info.symbol).toBe(key);
      expect(info.name.length).toBeGreaterThan(0);
      expect(info.inheritance.length).toBeGreaterThan(0);
      expect(info.description.length).toBeGreaterThan(0);
    }
  });
});

describe("getLocusTone", () => {
  it("主要座位にはデフォルト以外のトーンを割り当てる", () => {
    expect(getLocusTone("A")).not.toBe(DEFAULT_LOCUS_TONE);
    expect(getLocusTone("A").iconClass).toContain("emerald");
    expect(getLocusTone("O")).not.toBe(DEFAULT_LOCUS_TONE);
    expect(getLocusTone("O").iconClass).toContain("orange");
  });

  it("未知座位はデフォルトトーンへフォールバックする", () => {
    expect(getLocusTone("Unknown")).toBe(DEFAULT_LOCUS_TONE);
  });
});
