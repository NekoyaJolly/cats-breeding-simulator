import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import type {
  ReverseLookupCandidate,
  ReverseLookupResponse,
} from "@/lib/schema";
import { ResultsView } from "./ResultsView";

// テスト用の交配候補を作る。必要な部分だけ上書きできるようにする。
function makeCandidate(
  overrides: Partial<ReverseLookupCandidate> = {},
): ReverseLookupCandidate {
  return {
    category: "確定で期待できる",
    sire: { id: "s1", name: "青系の父", color: "Blue", breed: null },
    dam: { id: "d1", name: "黒系の母", color: "Black", breed: null },
    target_color: "Blue",
    confirmed_probability_pct: 25,
    conditional_max_probability_pct: 50,
    establishment_conditions: ["父が d/d を持つ"],
    confirmation_needed: [],
    recommended_tests: [],
    locus_evidence: [
      { locus: "D", target: "d/d", sire: "d/d", dam: "D/d", status: "ok", note: "希釈" },
    ],
    other_possible_colors: [],
    ...overrides,
  };
}

function makeResponse(
  overrides: Partial<ReverseLookupResponse> = {},
): ReverseLookupResponse {
  return {
    status: "ok",
    target_color: "Blue",
    target_sex: null,
    response_category: "ok",
    target_conditions: [],
    unchecked_conditions: [],
    recommended_checks: [],
    candidates: [],
    ...overrides,
  };
}

describe("ResultsView", () => {
  it("候補があるとき、父×母の見出しと目標カラーを表示する", () => {
    render(<ResultsView data={makeResponse({ candidates: [makeCandidate()] })} />);

    expect(screen.getByText("青系の父 × 黒系の母")).toBeInTheDocument();
    // 目標サマリー (性別未指定 + 目標カラー) を表示する。
    expect(screen.getByText("目標: 指定なし / Blue")).toBeInTheDocument();
  });

  it("候補が0件のとき、確認できない旨の案内 (NoCandidateAnalysis) を出す", () => {
    render(<ResultsView data={makeResponse({ candidates: [] })} />);

    expect(
      screen.getByText(
        "現在の登録情報では、目標カラーの成立条件を満たす交配候補を確認できません。",
      ),
    ).toBeInTheDocument();
  });
});
