import { describe, expect, it } from "vitest";
import {
  carriersText,
  colorRows,
  formatPct,
  groupedColorNameRows,
  sexLabel,
  targetSexLabel,
} from "./format";

describe("formatPct", () => {
  it("整数は小数点なし、端数は小数第1位まで表示する", () => {
    expect(formatPct(12)).toBe("12%");
    expect(formatPct(0)).toBe("0%");
    expect(formatPct(12.5)).toBe("12.5%");
    expect(formatPct(33.33)).toBe("33.3%");
  });
});

describe("sexLabel", () => {
  it("登録猫の性別を入力欄と同じラベルへ変換する", () => {
    expect(sexLabel("male")).toBe("♂ オス");
    expect(sexLabel("female")).toBe("♀ メス");
  });
});

describe("targetSexLabel", () => {
  it("目標性別を表示し、未指定は『指定なし』にする", () => {
    expect(targetSexLabel("male")).toBe("♂ オス");
    expect(targetSexLabel("female")).toBe("♀ メス");
    expect(targetSexLabel(null)).toBe("指定なし");
    expect(targetSexLabel(undefined)).toBe("指定なし");
  });
});

describe("colorRows", () => {
  it("空配列のときは案内文言を返す", () => {
    expect(colorRows([])).toBe("現在の計算範囲では表示できるカラーがありません。");
  });

  it("性別記号・色・確率を連結する", () => {
    expect(
      colorRows([
        { sex: "Female", color: "Blue", probability_pct: 12.5 },
        { sex: "Male", color: "Black", probability_pct: 25 },
      ]),
    ).toBe("♂ Black 25% / ♀ Blue 12.5%");
  });

  it("先頭8件までに制限する", () => {
    const rows = Array.from({ length: 10 }, (_, index) => ({
      sex: "Female" as const,
      color: `C${index}`,
      probability_pct: 1,
    }));
    expect(colorRows(rows).split(" / ")).toHaveLength(8);
  });

  it("メス結果が先に並んでいても、プレビューにはオス結果を含める", () => {
    const rows = [
      ...Array.from({ length: 8 }, (_, index) => ({
        sex: "Female",
        color: `Female${index}`,
        probability_pct: 1,
      })),
      ...Array.from({ length: 4 }, (_, index) => ({
        sex: "Male",
        color: `Male${index}`,
        probability_pct: 1,
      })),
    ];

    const displayed = colorRows(rows).split(" / ");

    expect(displayed).toHaveLength(8);
    expect(displayed.some((row) => row.startsWith("♂ Male"))).toBe(true);
    expect(displayed.some((row) => row.startsWith("♀ Female"))).toBe(true);
  });
});

describe("groupedColorNameRows", () => {
  it("その他カラーをオス、メスの順に色名だけでまとめる", () => {
    const groups = groupedColorNameRows([
      { sex: "Female", color: "Calico", probability_pct: 5.9 },
      { sex: "Female", color: "Cameo", probability_pct: 5.9 },
      { sex: "Female", color: "Red", probability_pct: 5.9 },
      { sex: "Female", color: "Tortoiseshell", probability_pct: 5.9 },
      { sex: "Male", color: "Black", probability_pct: 5.9 },
      { sex: "Male", color: "Cameo", probability_pct: 5.9 },
    ]);

    expect(groups).toEqual([
      {
        sex: "Male",
        symbol: "♂",
        colors: ["Black", "Cameo"],
        hiddenCount: 0,
      },
      {
        sex: "Female",
        symbol: "♀",
        colors: ["Calico", "Cameo", "Red"],
        hiddenCount: 1,
      },
    ]);
  });
});

describe("carriersText", () => {
  it("未登録(undefined)のときは空文字を返す", () => {
    expect(carriersText(undefined)).toBe("");
  });

  it("座位:遺伝子型をカンマ区切りで連結する", () => {
    expect(carriersText({ B: "B/b", D: "D/d" })).toBe("B:B/b, D:D/d");
  });
});
