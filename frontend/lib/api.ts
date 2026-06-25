import {
  apiErrorSchema,
  calculationResponseSchema,
  type CalculationResponse,
} from "./schema";

// 計算 API への入力。breed と carriers は任意。
export type CalculateInput = {
  sire_color: string;
  dam_color: string;
  breed?: string;
  mode: string;
  sire_carriers?: Record<string, string>;
  dam_carriers?: Record<string, string>;
};

// 計算結果か、人間可読のエラーメッセージかを表す判別共用体。
// 例外を投げず呼び出し側で分岐できるようにする。
export type CalculateOutcome =
  | { ok: true; data: CalculationResponse }
  | { ok: false; message: string };

// pydantic 検証エラー (detail が配列) を 1 本の文字列にまとめる。
function describeError(detail: string | Array<{ msg: string }>): string {
  if (typeof detail === "string") return detail;
  const joined = detail.map((item) => item.msg).join(" / ");
  return joined.length > 0 ? joined : "入力値が不正です。";
}

// POST /api/v1/calculate を叩き、レスポンスを Zod で検証して返す。
export async function calculate(input: CalculateInput): Promise<CalculateOutcome> {
  let response: Response;
  try {
    response = await fetch("/api/v1/calculate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(input),
    });
  } catch {
    // バックエンド未起動などで到達できないケース。
    return {
      ok: false,
      message:
        "バックエンドに接続できませんでした。API サーバ (uvicorn) が起動しているか確認してください。",
    };
  }

  if (response.ok) {
    const parsed = calculationResponseSchema.safeParse(await response.json());
    if (!parsed.success) {
      return { ok: false, message: "API レスポンスの形式が想定と異なります。" };
    }
    return { ok: true, data: parsed.data };
  }

  // エラー応答: FastAPI の detail を人間可読に整形する。
  const errorBody = await response.json().catch(() => null);
  const parsedError = apiErrorSchema.safeParse(errorBody);
  if (parsedError.success) {
    return { ok: false, message: describeError(parsedError.data.detail) };
  }
  return { ok: false, message: `エラーが発生しました (HTTP ${response.status})。` };
}
