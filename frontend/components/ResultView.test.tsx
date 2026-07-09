import { beforeEach, describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ResultView } from "./ResultView";
import type { CalculationResponse, ResultEntry } from "@/lib/schema";

// 各結果セクションはアコーディオンで、既定は全非展開・状態は localStorage 永続化。
// テスト間で展開状態が漏れないよう毎回クリアし、「非展開が既定」の前提を固定する。
beforeEach(() => {
  localStorage.clear();
});

// セクション見出しトグルを取得する。ドラッグハンドルの aria-label も同じセクション名を含むため、
// aria-expanded を持つ (= 開閉トグルである) ボタンに限定して曖昧さを避ける。
function sectionToggle(title: RegExp | string): HTMLElement {
  const toggle = screen
    .getAllByRole("button", { name: title })
    .find((button) => button.hasAttribute("aria-expanded"));
  if (!toggle) throw new Error(`section toggle not found: ${title}`);
  return toggle;
}

// セクション見出しトグルをクリックして中身を展開する。
async function openSection(title: RegExp | string): Promise<void> {
  await userEvent.click(sectionToggle(title));
}

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
    // メイン表示は confirmed_results ?? results にフォールバックする。
    // AOC テストは results 側の内訳を検証するので confirmed_results は null にする。
    confirmed_results: null,
    conditional_color_groups: [],
    diagnostics: {
      opened_loci: ["W", "D", "I", "Mc", "Ta"],
      closed_loci: ["A", "B", "C", "Wb"],
      assumptions: [],
      matched_probability: 1,
      unmatched_probability: 0,
      unmatched_genotype_count: 0,
    },
    parent_color_notes: [],
  };
}

// 父 White × 母 Black の §2.1 出力 (オス=母の色、メス=AOC)。
const WHITE_SIRE_RESULTS: ResultEntry[] = [
  { sex: "Male", color: "White", probability_pct: 25 },
  { sex: "Female", color: "White", probability_pct: 25 },
  { sex: "Male", color: "Black", probability_pct: 25 },
  { sex: "Female", color: "AOC", probability_pct: 25 },
];

describe("ResultView AOC", () => {
  it("AOC 行があるとき、説明はデフォルト非表示で、クリックで開く", async () => {
    render(
      <ResultView
        data={buildResponse("White", "Black", WHITE_SIRE_RESULTS)}
        language="ja"
      />,
    );

    // AOC 行は全分布アコーディオン内。まずセクションを展開する。
    await openSection(/全分布/);
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

// P2「もしこの色が出たら」: 隠れキャリア仮定時のみ出る条件付きカラー群の表示。
// normal モードかつ conditional_color_groups があるときだけ畳みで表示し、
// 開くと family_label / reverse_inference_label / % / colors が読める。
describe("ResultView conditional colors", () => {
  const BASE_RESULTS: ResultEntry[] = [
    { sex: "Male", color: "Black", probability_pct: 50 },
    { sex: "Female", color: "Black", probability_pct: 50 },
  ];

  function withConditional(response: CalculationResponse): CalculationResponse {
    return {
      ...response,
      confirmed_results: BASE_RESULTS,
      conditional_color_groups: [
        {
          family_label: "ブルー系",
          reverse_inference_label:
            "この色が出たら両親が D/d 保因と確定します",
          conditional_probability_pct: 25,
          colors: ["Blue"],
          color_sexes: { Blue: ["Female", "Male"] },
          assumed_carriers: { sire: { D: "D/d" }, dam: { D: "D/d" } },
          scenario: "dilute",
        },
      ],
    };
  }

  it("normal モードで条件付きカラーがあるとき、アコーディオンを開くと中身が一覧でき、畳める", async () => {
    render(
      <ResultView
        data={withConditional(buildResponse("Black", "Black", BASE_RESULTS))}
        language="ja"
      />,
    );

    const toggle = sectionToggle(/両親キャリア推定/);
    // 既定は非展開 (統一アコーディオン。展開状態は localStorage 永続)。
    expect(toggle).toHaveAttribute("aria-expanded", "false");
    expect(
      screen.queryByText(/この色が出たら両親が D\/d 保因と確定します/),
    ).toBeNull();

    // 開くと中身が読める。
    await userEvent.click(toggle);
    expect(toggle).toHaveAttribute("aria-expanded", "true");
    // グルーピングは色系統でなく遺伝子座 (原因キャリア) 単位。原因は逆推論の説明文に出る。
    expect(
      screen.getByText(/この色が出たら両親が D\/d 保因と確定します/),
    ).toBeInTheDocument();
    // 出る色は色見本バッジで並ぶ。
    expect(screen.getByText("Blue")).toBeInTheDocument();
    expect(screen.getByText(/最大/)).toBeInTheDocument();

    // 任意で畳める。
    await userEvent.click(toggle);
    expect(toggle).toHaveAttribute("aria-expanded", "false");
    expect(
      screen.queryByText(/この色が出たら両親が D\/d 保因と確定します/),
    ).toBeNull();
  });

  it("両親キャリア推定バッジに親ラベルと遺伝子型が表示される", async () => {
    // assumed_carriers = {sire:{D:"D/d"}, dam:{D:"D/d"}} → 同一遺伝子型なので「両親 D/d」に集約。
    render(
      <ResultView
        data={withConditional(buildResponse("Black", "Black", BASE_RESULTS))}
        language="ja"
      />,
    );
    // バッジは両親キャリア推定アコーディオン内。展開してから検証する。
    await openSection(/両親キャリア推定/);
    // 説明文にも同じ文字列が含まれるため、バッジ要素そのものを testid で特定して検証する。
    const badges = screen.getAllByTestId("carrier-badge");
    expect(badges).toHaveLength(1);
    expect(badges[0]).toHaveTextContent("両親");
    expect(badges[0]).toHaveTextContent("D/d");
  });

  it("conditional_color_groups が空ならセクションを描画しない", () => {
    render(
      <ResultView
        data={buildResponse("Black", "Black", BASE_RESULTS)}
        language="ja"
      />,
    );
    expect(
      screen.queryByRole("button", { name: /両親キャリア推定/ }),
    ).toBeNull();
  });

  it("normal 以外のモードでは条件付きカラーがあっても描画しない", () => {
    const base = withConditional(buildResponse("Black", "Black", BASE_RESULTS));
    const explicit: CalculationResponse = {
      ...base,
      mode: "explicit_carrier",
    };
    render(<ResultView data={explicit} language="ja" />);
    expect(
      screen.queryByRole("button", { name: /両親キャリア推定/ }),
    ).toBeNull();
  });
});

// 全分布: 1%未満の色は既定で畳まれ、ボタンで展開すると一覧に現れる。
describe("ResultView full distribution", () => {
  it("1%未満の色は集約され、ボタンをクリックすると展開される", async () => {
    const results: ResultEntry[] = [
      { sex: "Male", color: "Black", probability_pct: 49 },
      { sex: "Female", color: "Black", probability_pct: 49 },
      { sex: "Male", color: "Blue", probability_pct: 1 },
      { sex: "Female", color: "Blue", probability_pct: 1 },
      // <1% の微小色 (集約対象)。
      { sex: "Male", color: "Chocolate", probability_pct: 0.4 },
      { sex: "Female", color: "Chocolate", probability_pct: 0.4 },
    ];
    render(
      <ResultView data={buildResponse("Black", "Black", results)} language="ja" />,
    );

    // 全分布はアコーディオン内。展開してから内訳を検証する。
    await openSection(/全分布/);
    // 「1%未満 · N色」の集約ボタンが (性別ごとに) 出る。
    const toggles = screen.getAllByRole("button", { name: /1%未満/ });
    expect(toggles.length).toBeGreaterThan(0);
    // 既定では <1% の色 (Chocolate) は一覧に出ない。
    expect(screen.queryByText("Chocolate")).toBeNull();

    // クリックで展開すると現れる。
    await userEvent.click(toggles[0]);
    expect(screen.getAllByText("Chocolate").length).toBeGreaterThan(0);
  });

  it("全セクションは既定で非展開、展開状態は localStorage に永続化され次回に引き継がれる", async () => {
    const confirmed: ResultEntry[] = [
      { sex: "Male", color: "Black", probability_pct: 50 },
      { sex: "Female", color: "Black", probability_pct: 50 },
    ];
    const withConfirmed: CalculationResponse = {
      ...buildResponse("Black", "Black", confirmed),
      confirmed_results: confirmed,
    };
    // 統一アコーディオン: 確定色の有無に関わらず、既定はすべて非展開。
    const { unmount } = render(<ResultView data={withConfirmed} language="ja" />);
    expect(sectionToggle(/確定カラー/)).toHaveAttribute("aria-expanded", "false");
    expect(sectionToggle(/全分布/)).toHaveAttribute("aria-expanded", "false");

    // ユーザーが全分布を展開すると localStorage に保存される。
    await openSection(/全分布/);
    expect(sectionToggle(/全分布/)).toHaveAttribute("aria-expanded", "true");
    unmount();

    // 次回の計算結果 (再マウント) では、保存された展開状態で復元される。
    render(<ResultView data={withConfirmed} language="ja" />);
    expect(sectionToggle(/全分布/)).toHaveAttribute("aria-expanded", "true");
    expect(sectionToggle(/確定カラー/)).toHaveAttribute("aria-expanded", "false");
  });

  it("確定色は -White を合算せず、ベース色と -White を別チップで表示する", async () => {
    const confirmed: ResultEntry[] = [
      { sex: "Female", color: "Brown Tabby", probability_pct: 25 },
      { sex: "Female", color: "Brown Tabby-White", probability_pct: 25 },
      { sex: "Male", color: "Brown Tabby", probability_pct: 25 },
      { sex: "Male", color: "Brown Tabby-White", probability_pct: 25 },
    ];
    const data: CalculationResponse = {
      ...buildResponse("Brown Tabby", "Brown Tabby-White", confirmed),
      confirmed_results: confirmed,
    };
    render(<ResultView data={data} language="ja" />);
    // 確定カラーはアコーディオン内。展開してからチップを検証する。
    await openSection(/確定カラー/);
    // ベース色と -White が (合算されず) 別々のチップとして両方出る。
    expect(screen.getAllByText("Brown Tabby").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Brown Tabby-White").length).toBeGreaterThan(0);
  });

  it("白斑レベル (-White) は合算されず副次行で表示される", async () => {
    const results: ResultEntry[] = [
      { sex: "Male", color: "Silver Tabby", probability_pct: 25 },
      { sex: "Male", color: "Silver Tabby-White", probability_pct: 25 },
      { sex: "Female", color: "Silver Tabby", probability_pct: 25 },
      { sex: "Female", color: "Silver Tabby-White", probability_pct: 25 },
    ];
    render(
      <ResultView
        data={buildResponse("Silver Tabby", "Silver Tabby-White", results)}
        language="ja"
      />,
    );
    // 全分布はアコーディオン内。展開してから副次行を検証する。
    await openSection(/全分布/);
    // ベース色 (Silver Tabby) に集約されつつ、-White の内訳が副次行 (└ -White) で残る。
    expect(screen.getAllByText(/└ -White/).length).toBeGreaterThan(0);
  });
});
