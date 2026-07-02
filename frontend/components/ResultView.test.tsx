import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ResultView } from "./ResultView";
import type { CalculationResponse, ResultEntry } from "@/lib/schema";

// WHITE-4: AOC (Any Other Color) 行のフォーカス/クリックで説明が開き、通常時は説明を出さない。
// AOC は White 親のとき順方向に現れる集約カテゴリ (§2.3)。

function buildResponse(
  sireColor: string,
  damColor: string,
  results: ResultEntry[],
): CalculationResponse {
  return {
    status: "success",
    mode: "normal",
    parameters: {
      sire_color: sireColor,
      dam_color: damColor,
      breed: null,
      mode: "normal",
      sire_carriers: null,
      dam_carriers: null,
    },
    results,
    diagnostics: {
      opened_loci: ["W", "D", "I", "Mc", "Ta"],
      closed_loci: ["A", "B", "C", "Wb"],
      assumptions: [],
      matched_probability: 1,
      unmatched_probability: 0,
      unmatched_genotype_count: 0,
    },
    carrier_exploration_results: null,
    parent_color_notes: [],
  };
}

// 父 White × 母 Black の §2.1 出力 (AOC を含む)。
const WHITE_SIRE_RESULTS: ResultEntry[] = [
  { sex: "Male", color: "White", probability_pct: 25 },
  { sex: "Female", color: "White", probability_pct: 25 },
  { sex: "Male", color: "Black", probability_pct: 25 },
  { sex: "Female", color: "Black", probability_pct: 12.5 },
  { sex: "Female", color: "AOC", probability_pct: 12.5 },
];

describe("ResultView AOC", () => {
  it("AOC 行があるとき、説明はデフォルト非表示で、クリックで開く", async () => {
    render(
      <ResultView
        data={buildResponse("White", "Black", WHITE_SIRE_RESULTS)}
        language="ja"
      />,
    );

    const button = screen.getByRole("button", { name: "AOC の説明を開く" });
    // デフォルトは閉じている (通常時に説明を押し付けない)。
    expect(button).toHaveAttribute("aria-expanded", "false");

    await userEvent.click(button);
    expect(button).toHaveAttribute("aria-expanded", "true");
    // 本文と、White 親側の導線 (explicit_carrier への誘導) が読める。
    expect(screen.getByText(/Any Other Color/)).toBeInTheDocument();
    expect(
      screen.getByText(/父猫が White で下の色が未入力のためです/),
    ).toBeInTheDocument();
  });

  it("AOC 行が無いときは AOC 説明ボタンを描画しない", () => {
    const results: ResultEntry[] = [
      { sex: "Male", color: "Black", probability_pct: 46.875 },
      { sex: "Female", color: "Black", probability_pct: 46.875 },
      { sex: "Male", color: "Blue", probability_pct: 3.125 },
      { sex: "Female", color: "Blue", probability_pct: 3.125 },
    ];
    render(
      <ResultView data={buildResponse("Black", "Black", results)} language="ja" />,
    );

    expect(
      screen.queryByRole("button", { name: "AOC の説明を開く" }),
    ).toBeNull();
  });
});
