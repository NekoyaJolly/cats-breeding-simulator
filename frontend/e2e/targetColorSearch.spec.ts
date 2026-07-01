import { test, expect } from "@playwright/test";

// 「目標カラーから探す」のゴールデンパス E2E。
// バックエンド API はすべて page.route でモックし、UI の一連の操作だけを検証する
// (登録 → 一覧反映 → 目標カラー検索 → 結果ランキング表示)。

// 逆引き API の固定レスポンス (候補1件)。
const reverseLookupResponse = {
  status: "ok",
  target_color: "Blue",
  target_sex: null,
  response_category: "ok",
  target_conditions: [],
  unchecked_conditions: [],
  recommended_checks: [],
  candidates: [
    {
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
    },
  ],
};

test.beforeEach(async ({ page }) => {
  // マスタ取得は空でよい (自由入力で進められる)。逆引きは固定レスポンスを返す。
  await page.route("**/api/v1/colors", (route) => route.fulfill({ json: { colors: [] } }));
  await page.route("**/api/v1/breeds", (route) => route.fulfill({ json: { breeds: [] } }));
  await page.route("**/api/v1/reverse-lookup", (route) =>
    route.fulfill({ json: reverseLookupResponse }),
  );
});

test("登録2頭 → 目標カラー検索で結果ランキングが表示される", async ({ page }) => {
  await page.addInitScript(() => {
    window.localStorage.setItem("ccp:language", "ja");
  });
  await page.goto("/");

  // Target Coat タブへ切り替える。
  await page.getByRole("button", { name: "Target Coat" }).click();

  // 1頭目 (メス: 既定) を登録する。
  await page.locator("#registered-cat-color").fill("Blue");
  await page.getByRole("button", { name: "猫を登録する" }).click();

  // 2頭目 (オス) を登録する。
  await page.locator("#registered-cat-sex").selectOption("male");
  await page.locator("#registered-cat-color").fill("Black");
  await page.getByRole("button", { name: "猫を登録する" }).click();

  // 目標カラーを入力して検索する。
  await page.locator("#target-color").fill("Blue");
  await page.getByRole("button", { name: "組み合わせを探す" }).click();

  // 結果ランキングと候補カードが表示される。
  await expect(page.getByRole("heading", { name: "結果ランキング" })).toBeVisible();
  await expect(page.getByText("青系の父 × 黒系の母")).toBeVisible();
});
