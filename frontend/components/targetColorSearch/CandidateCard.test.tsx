import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import type { ReverseLookupCandidate } from "@/lib/schema";
import { CandidateCard } from "./CandidateCard";

// テスト用の交配候補。必要な部分だけ上書きできるようにする。
function makeCandidate(
  overrides: Partial<ReverseLookupCandidate> = {},
): ReverseLookupCandidate {
  return {
    category: "確定で期待できる",
    sire: { id: "s1", name: "父A", color: "Blue", breed: null },
    dam: { id: "d1", name: "母B", color: "Black", breed: null },
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

describe("CandidateCard", () => {
  it("確定確率>0のとき、サマリーの代表確率は確定確率を表示する", () => {
    const { container } = render(
      <CandidateCard
        candidate={makeCandidate({
          confirmed_probability_pct: 25,
          conditional_max_probability_pct: 50,
        })}
        index={0}
        language="ja"
        categoryLabel="確定で期待できる"
      />,
    );
    // サマリー(常時可視)の代表確率は確定確率(25%)。条件付き最大(50%)はサマリーに出さない。
    const summary = container.querySelector("summary");
    expect(summary?.textContent).toContain("25%");
    expect(summary?.textContent).not.toContain("50%");
  });

  it("確定確率が0のとき、サマリーの代表確率は条件付き最大確率を表示する", () => {
    const { container } = render(
      <CandidateCard
        candidate={makeCandidate({
          confirmed_probability_pct: 0,
          conditional_max_probability_pct: 50,
        })}
        index={0}
        language="ja"
        categoryLabel="確定で期待できる"
      />,
    );
    const summary = container.querySelector("summary");
    expect(summary?.textContent).toContain("50%");
  });

  it("確認・検査・他カラーが空のとき、デフォルト文言を表示する", () => {
    render(
      <CandidateCard
        candidate={makeCandidate()}
        index={0}
        language="ja"
        categoryLabel="確定で期待できる"
      />,
    );
    expect(screen.getByText("追加確認なしで評価できます。")).toBeInTheDocument();
    expect(screen.getByText("現時点で追加検査の提案はありません。")).toBeInTheDocument();
    expect(
      screen.getByText("現在の計算範囲では表示できる色柄がありません。"),
    ).toBeInTheDocument();
  });

  it("組み合わせ番号は index+1 で表示する", () => {
    render(
      <CandidateCard
        candidate={makeCandidate()}
        index={2}
        language="ja"
        categoryLabel="確定で期待できる"
      />,
    );
    expect(screen.getByText("組み合わせ 3")).toBeInTheDocument();
  });
});
