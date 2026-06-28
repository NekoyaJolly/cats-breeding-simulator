import { describe, expect, it } from "vitest";

import { parseCarriers } from "./carriers";

describe("parseCarriers", () => {
  it("空文字・空白のみは undefined", () => {
    expect(parseCarriers("")).toBeUndefined();
    expect(parseCarriers("   ")).toBeUndefined();
  });

  it("単一の座位:遺伝子型を辞書化する", () => {
    expect(parseCarriers("C:C/cs")).toEqual({ C: "C/cs" });
  });

  it("カンマ区切りの複数ペアを辞書化し、前後空白を除去する", () => {
    expect(parseCarriers(" C:C/cs , B:B/b ")).toEqual({ C: "C/cs", B: "B/b" });
  });

  it("座位または遺伝子型が欠けた要素は無視する", () => {
    expect(parseCarriers("C:C/cs, :B/b, D:")).toEqual({ C: "C/cs" });
  });

  it("有効なペアが1つも無ければ undefined", () => {
    expect(parseCarriers(",, : ,")).toBeUndefined();
  });

  it("同一座位の重複は後勝ちで上書きする", () => {
    expect(parseCarriers("C:C/cs, C:C/cb")).toEqual({ C: "C/cb" });
  });
});
