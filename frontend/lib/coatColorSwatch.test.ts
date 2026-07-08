import { describe, expect, it } from "vitest";

import { coatSwatchBackground } from "./coatColorSwatch";

// coatColorSwatch の色定数 (本体と同値)。三毛スウォッチの検証に使う。
const WHITE = "#fafafa";
const RED = "#d67a35";
const CREAM = "#eed9b6";
const BLUE = "#8b96a3";

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
});
