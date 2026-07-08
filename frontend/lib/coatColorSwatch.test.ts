import { describe, expect, it } from "vitest";

import { coatSwatchBackground } from "./coatColorSwatch";

// coatColorSwatch の色定数 (本体と同値)。三毛スウォッチの検証に使う。
const WHITE = "#fafafa";
const RED = "#d67a35";
const CREAM = "#eed9b6";
const BLUE = "#8b96a3";
const SILVER_UNDERCOAT_RGB = "243,245,247"; // シルバー下地 (smoke) の rgba

describe("coatSwatchBackground: キャリコ (三毛) の色見本", () => {
  it("Calico はトーティ (黒×赤) に白斑を足した3色になる", () => {
    const calico = coatSwatchBackground("Calico");
    expect(calico).toContain(WHITE); // 白斑 (三毛の白)
    expect(calico).toContain(RED); // フェオメラニン (赤)
  });

  it("Dilute Calico は希釈トーティ (青×クリーム) に白斑を足した3色になる", () => {
    const dilute = coatSwatchBackground("Dilute Calico");
    expect(dilute).toContain(WHITE);
    expect(dilute).toContain(BLUE); // 希釈ユーメラニン (ブルー)
    expect(dilute).toContain(CREAM); // 希釈フェオメラニン (クリーム)
    expect(dilute).not.toContain(RED); // 濃色の赤は出ない
  });

  it("Calico と Dilute Calico は別の色見本になる (従来は同色だった回帰防止)", () => {
    expect(coatSwatchBackground("Calico")).not.toBe(coatSwatchBackground("Dilute Calico"));
  });

  it("Calico は Tortoiseshell に白斑を足したもの (白の有無で区別)", () => {
    expect(coatSwatchBackground("Tortoiseshell")).not.toContain(WHITE);
    expect(coatSwatchBackground("Calico")).toContain(WHITE);
  });

  it("Dilute Calico は Blue Cream に白斑を足したもの (白の有無で区別)", () => {
    expect(coatSwatchBackground("Blue Cream")).not.toContain(WHITE);
    expect(coatSwatchBackground("Dilute Calico")).toContain(WHITE);
  });

  // 修飾語 (Smoke/Silver 等) を落とさない: 名前を丸ごと Tortoiseshell 等へ置換しないこと。
  // cat_color_master.csv には Smoke Calico / Smoke Dilute Calico 等が実在する。
  it("Smoke Calico は smoke (シルバー下地) を保持しつつ白斑を足す", () => {
    const smokeCalico = coatSwatchBackground("Smoke Calico");
    expect(smokeCalico).toContain(WHITE); // 三毛の白
    expect(smokeCalico).toContain(SILVER_UNDERCOAT_RGB); // smoke 下地が保持される
    expect(smokeCalico).not.toBe(coatSwatchBackground("Calico")); // 素の Calico と別
  });

  it("Smoke Dilute Calico は smoke・希釈(青×クリーム)・白斑をすべて反映する", () => {
    const s = coatSwatchBackground("Smoke Dilute Calico");
    expect(s).toContain(WHITE);
    expect(s).toContain(BLUE); // 希釈ユーメラニン
    expect(s).toContain(CREAM); // 希釈フェオメラニン
    expect(s).toContain(SILVER_UNDERCOAT_RGB); // smoke 下地
  });
});
