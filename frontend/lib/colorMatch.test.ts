import { describe, expect, it } from "vitest";

import {
  canonicalColorValue,
  filterColors,
  normalizeKey,
  resolveExactColorOption,
} from "./colorMatch";
import type { ColorOption } from "./schema";

function option(
  value: string,
  reading_ja: string,
  keywords: string[] = [],
): ColorOption {
  return {
    value,
    reading_ja,
    keywords,
    status: "ok",
    breed_context: "",
    sex_restriction: "",
  };
}

const COLORS: ColorOption[] = [
  option("Brown Tabby", "ブラウンタビー", ["Brown", "ぶらうん", "BT"]),
  option("Black", "ブラック", ["Black", "くろ"]),
  option("Blue", "ブルー", ["Blue", "あお"]),
  option("Blue Cream", "ブルークリーム", ["Blue Cream"]),
];

describe("normalizeKey", () => {
  it("ひらがなをカタカナへ畳み込む", () => {
    expect(normalizeKey("ぶらうん")).toBe(normalizeKey("ブラウン"));
  });

  it("大文字小文字・空白・記号を吸収する", () => {
    expect(normalizeKey("Brown Tabby")).toBe("browntabby");
    expect(normalizeKey("blue-cream")).toBe(normalizeKey("Blue Cream"));
    // 半角括弧・中黒・スラッシュは除去される
    expect(normalizeKey("(あお)・/")).toBe("アオ");
  });
});

describe("resolveExactColorOption", () => {
  it("正式名の完全一致 (記号・大小無視) を解決する", () => {
    expect(resolveExactColorOption(COLORS, "brown tabby")?.value).toBe("Brown Tabby");
  });

  it("カナ読み・別名の完全一致を解決する", () => {
    expect(resolveExactColorOption(COLORS, "ぶらうん")?.value).toBe("Brown Tabby");
    expect(resolveExactColorOption(COLORS, "くろ")?.value).toBe("Black");
  });

  it("空入力・不一致は null", () => {
    expect(resolveExactColorOption(COLORS, "  ")).toBeNull();
    expect(resolveExactColorOption(COLORS, "存在しない色")).toBeNull();
  });
});

describe("canonicalColorValue", () => {
  it("既知の別名は canonical 値へ揃える", () => {
    expect(canonicalColorValue(COLORS, "ぶらうん")).toBe("Brown Tabby");
  });

  it("未対応の自由入力はトリムして保持する", () => {
    expect(canonicalColorValue(COLORS, "  謎の色  ")).toBe("謎の色");
  });
});

describe("filterColors", () => {
  it("空 query は先頭から limit 件を返す", () => {
    expect(filterColors(COLORS, "", 2).map((c) => c.value)).toEqual([
      "Brown Tabby",
      "Black",
    ]);
  });

  it("前方一致を部分一致より上位にする", () => {
    const result = filterColors(COLORS, "blue").map((c) => c.value);
    // "Blue" (前方一致・短い) が "Blue Cream" より先
    expect(result[0]).toBe("Blue");
    expect(result).toContain("Blue Cream");
  });

  it("カナ query でも一致する", () => {
    expect(filterColors(COLORS, "あお").map((c) => c.value)).toContain("Blue");
  });

  it("キーワードの前方一致でヒットする (略称)", () => {
    // "BT" は Brown Tabby のキーワード。value/読みには前方一致しないがキーワードで拾う。
    expect(filterColors(COLORS, "bt").map((c) => c.value)).toContain("Brown Tabby");
  });

  it("キーワードの部分一致 (前方でない) でもヒットする", () => {
    // "rown" は keyword "Brown" の途中一致 → 部分一致スコアで採用。
    expect(filterColors(COLORS, "rown").map((c) => c.value)).toContain("Brown Tabby");
  });
});
