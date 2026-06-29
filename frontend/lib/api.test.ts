import { afterEach, describe, expect, it, vi } from "vitest";

import {
  calculate,
  describeError,
  fetchBreedColors,
  fetchBreeds,
  fetchColors,
  inferFromLitter,
  searchTargetColor,
  submitFeedback,
} from "./api";

// fetch をモックして応答を差し替えるヘルパ。コードは response.ok / status / json() のみ参照する。
type MockResponse = { ok: boolean; status: number; json: () => Promise<unknown> };

function jsonResponse(body: unknown, ok = true, status = 200): MockResponse {
  return { ok, status, json: async () => body };
}

function brokenJsonResponse(ok = true, status = 200): MockResponse {
  return { ok, status, json: async () => {
    throw new Error("invalid json");
  } };
}

function mockFetch(response: MockResponse): void {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(response));
}

function mockFetchReject(): void {
  vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("network down")));
}

// 各スキーマを満たす最小の有効ボディ。
const VALID_CALCULATION = {
  status: "success",
  mode: "normal",
  parameters: { sire_color: "Black", dam_color: "Black", mode: "normal" },
  results: [{ sex: "Male", color: "Black", probability_pct: 100 }],
  diagnostics: {
    opened_loci: [],
    closed_loci: [],
    assumptions: [],
    matched_probability: 1,
    unmatched_probability: 0,
    unmatched_genotype_count: 0,
  },
};

const VALID_REVERSE = {
  status: "success",
  target_color: "Blue",
  response_category: "確定で期待できる",
  target_conditions: [],
  unchecked_conditions: [],
  recommended_checks: [],
  candidates: [],
};

const VALID_LITTER = {
  status: "success",
  response_category: "推定可能",
  candidate_pair_count: 1,
  confirmed: [],
  conditional: [],
  inferred: [],
  unconfirmed: [],
  contradictions: [],
  warnings: [],
  recommended_tests: [],
};

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("describeError", () => {
  describe("文字列 detail (自前 BreedingCalculationError)", () => {
    it("Unsupported color の長い一覧を簡潔な日本語へ整形する", () => {
      const detail = "Unsupported color 'Foo'. Supported colors: Black, Blue, ...";
      expect(describeError(detail)).toBe(
        "「Foo」は対応していない毛色です。候補から選んでください。",
      );
    });

    it("性別不適合カラーをオス親向けに整形する", () => {
      const detail = "Color 'Blue Cream' is not valid for a male.";
      expect(describeError(detail)).toBe(
        "「Blue Cream」はオス親（♀限定の毛色）には指定できない毛色です。",
      );
    });

    it("性別不適合カラーをメス親向けに整形する", () => {
      const detail = "Color 'Foo' is not valid for a female.";
      expect(describeError(detail)).toBe("「Foo」はメス親には指定できない毛色です。");
    });

    it("既に日本語のメッセージはそのまま返す", () => {
      const detail = "「Foo」は通常の計算では入力できない色区分です。";
      expect(describeError(detail)).toBe(detail);
    });
  });

  describe("配列 detail (pydantic 検証エラー)", () => {
    it("日本語の検証メッセージ (入力上限超過) を表示し Value error 接頭辞を除去する", () => {
      const detail = [{ msg: "Value error, 登録猫は最大50頭までです。頭数を減らしてください。" }];
      expect(describeError(detail)).toBe("登録猫は最大50頭までです。頭数を減らしてください。");
    });

    it("リター子猫上限の日本語メッセージを表示する", () => {
      const detail = [{ msg: "Value error, 観察できる子猫は最大12頭までです。" }];
      expect(describeError(detail)).toBe("観察できる子猫は最大12頭までです。");
    });

    it("英語のみの検証エラーは総括文言にフォールバックする", () => {
      const detail = [{ msg: "String should have at least 1 character" }];
      expect(describeError(detail)).toBe(
        "入力内容に誤りがあります。毛色が正しく入力されているか確認してください。",
      );
    });

    it("英語と日本語が混在する場合は最初の日本語メッセージを採用する", () => {
      const detail = [
        { msg: "Field required" },
        { msg: "Value error, 登録猫は最大50頭までです。頭数を減らしてください。" },
      ];
      expect(describeError(detail)).toBe("登録猫は最大50頭までです。頭数を減らしてください。");
    });
  });
});

describe("fetchColors", () => {
  it("成功時は colors を返す", async () => {
    mockFetch(
      jsonResponse({
        colors: [
          {
            value: "Black",
            reading_ja: "ブラック",
            status: "ok",
            breed_context: "",
            sex_restriction: "",
            keywords: ["Black"],
          },
        ],
      }),
    );
    const colors = await fetchColors();
    expect(colors).toHaveLength(1);
    expect(colors[0].value).toBe("Black");
  });

  it("ネットワークエラー時は空配列にフォールバックする", async () => {
    mockFetchReject();
    expect(await fetchColors()).toEqual([]);
  });

  it("HTTPエラー応答時は空配列", async () => {
    mockFetch(jsonResponse(null, false, 500));
    expect(await fetchColors()).toEqual([]);
  });

  it("スキーマ不一致のボディは空配列", async () => {
    mockFetch(jsonResponse({ unexpected: true }));
    expect(await fetchColors()).toEqual([]);
  });

  it("非JSON応答は空配列", async () => {
    mockFetch(brokenJsonResponse());
    expect(await fetchColors()).toEqual([]);
  });
});

describe("fetchBreeds", () => {
  it("成功時は breeds を返す", async () => {
    mockFetch(jsonResponse({ breeds: [{ value: "Munchkin", affects_genetics: false }] }));
    const breeds = await fetchBreeds();
    expect(breeds.map((b) => b.value)).toEqual(["Munchkin"]);
  });

  it("ネットワークエラー時は空配列", async () => {
    mockFetchReject();
    expect(await fetchBreeds()).toEqual([]);
  });
});

describe("fetchBreedColors", () => {
  it("制約ありの猫種は colors を返す", async () => {
    mockFetch(jsonResponse({ breed: "Siamese", constrained: true, colors: ["Seal Point"] }));
    expect(await fetchBreedColors("Siamese")).toEqual(["Seal Point"]);
  });

  it("制約なしの猫種は空配列 (ポップアップを出さない)", async () => {
    mockFetch(jsonResponse({ breed: "Munchkin", constrained: false, colors: [] }));
    expect(await fetchBreedColors("Munchkin")).toEqual([]);
  });

  it("ネットワークエラー時は空配列", async () => {
    mockFetchReject();
    expect(await fetchBreedColors("Siamese")).toEqual([]);
  });
});

describe("calculate", () => {
  const input = { sire_color: "Black", dam_color: "Black", mode: "normal" };

  it("成功時は ok:true で検証済みデータを返す", async () => {
    mockFetch(jsonResponse(VALID_CALCULATION));
    const result = await calculate(input);
    expect(result.ok).toBe(true);
    if (result.ok) expect(result.data.results[0].color).toBe("Black");
  });

  it("接続不可は ok:false で接続エラー文言", async () => {
    mockFetchReject();
    const result = await calculate(input);
    expect(result).toEqual({
      ok: false,
      message:
        "バックエンドに接続できませんでした。API サーバ (uvicorn) が起動しているか確認してください。",
    });
  });

  it("エラー応答 (文字列 detail) は整形メッセージを返す", async () => {
    mockFetch(jsonResponse({ detail: "「Foo」は対応していない毛色です。" }, false, 422));
    const result = await calculate(input);
    expect(result).toEqual({ ok: false, message: "「Foo」は対応していない毛色です。" });
  });

  it("200 でもスキーマ不一致なら形式エラー文言", async () => {
    mockFetch(jsonResponse({ bogus: true }));
    const result = await calculate(input);
    expect(result).toEqual({ ok: false, message: "API レスポンスの形式が想定と異なります。" });
  });

  it("detail が解釈不能なエラー応答は HTTP コード付き文言", async () => {
    mockFetch(jsonResponse({ nope: 1 }, false, 503));
    const result = await calculate(input);
    expect(result).toEqual({ ok: false, message: "エラーが発生しました (HTTP 503)。" });
  });
});

describe("searchTargetColor", () => {
  const input = { target_color: "Blue", cats: [] };

  it("成功時は ok:true でデータを返す", async () => {
    mockFetch(jsonResponse(VALID_REVERSE));
    const result = await searchTargetColor(input);
    expect(result.ok).toBe(true);
    if (result.ok) expect(result.data.target_color).toBe("Blue");
  });

  it("配列 detail の上限超過は日本語文言を返す", async () => {
    mockFetch(
      jsonResponse(
        { detail: [{ msg: "Value error, 登録猫は最大50頭までです。頭数を減らしてください。" }] },
        false,
        422,
      ),
    );
    const result = await searchTargetColor(input);
    expect(result).toEqual({
      ok: false,
      message: "登録猫は最大50頭までです。頭数を減らしてください。",
    });
  });
});

describe("inferFromLitter", () => {
  const input = {
    sire: { color: "Black" },
    dam: { color: "Black" },
    kittens: [{ id: "k1", sex: "female" as const, color: "Black" }],
  };

  it("成功時は ok:true でデータを返す", async () => {
    mockFetch(jsonResponse(VALID_LITTER));
    const result = await inferFromLitter(input);
    expect(result.ok).toBe(true);
    if (result.ok) expect(result.data.candidate_pair_count).toBe(1);
  });

  it("接続不可は ok:false で接続エラー文言", async () => {
    mockFetchReject();
    const result = await inferFromLitter(input);
    expect(result.ok).toBe(false);
    if (!result.ok) expect(result.message).toContain("バックエンドに接続できませんでした");
  });

  it("エラー応答 (配列 detail) は日本語文言を返す", async () => {
    mockFetch(
      jsonResponse(
        { detail: [{ msg: "Value error, 観察できる子猫は最大12頭までです。" }] },
        false,
        422,
      ),
    );
    const result = await inferFromLitter(input);
    expect(result).toEqual({ ok: false, message: "観察できる子猫は最大12頭までです。" });
  });

  it("200 でもスキーマ不一致なら形式エラー文言", async () => {
    mockFetch(jsonResponse({ bogus: true }));
    const result = await inferFromLitter(input);
    expect(result).toEqual({
      ok: false,
      message: "リター推定APIレスポンスの形式が想定と異なります。",
    });
  });
});

describe("submitFeedback", () => {
  it("成功時は sent を返す", async () => {
    mockFetch(jsonResponse({ sent: true }));
    expect(await submitFeedback("ありがとう")).toEqual({ sent: true });
  });

  it("HTTPエラー時は例外を投げる", async () => {
    mockFetch(jsonResponse(null, false, 500));
    await expect(submitFeedback("x")).rejects.toThrow("フィードバックの送信に失敗しました");
  });

  it("応答形式が不一致なら例外を投げる", async () => {
    mockFetch(jsonResponse({ unexpected: true }));
    await expect(submitFeedback("x")).rejects.toThrow("応答形式が想定と異なります");
  });
});
