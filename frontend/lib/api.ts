import {
  apiErrorSchema,
  calculationResponseSchema,
  colorsResponseSchema,
  type CalculationResponse,
  type ColorOption,
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

// GET /api/v1/colors を叩き、入力サジェスト用の色一覧を返す。
// 失敗時 (未起動 / 非JSON / スキーマ不一致) は空配列を返し、
// 呼び出し側のコンボボックスは自由入力にフォールバックできる (例外を投げない)。
export async function fetchColors(): Promise<ColorOption[]> {
  let response: Response;
  try {
    response = await fetch("/api/v1/colors", {
      headers: { Accept: "application/json" },
    });
  } catch {
    return [];
  }
  if (!response.ok) return [];
  const body = await response.json().catch(() => null);
  const parsed = colorsResponseSchema.safeParse(body);
  return parsed.success ? parsed.data.colors : [];
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
    // 成功応答でも空ボディ / 非JSON / 途中切断で json() が例外になり得るため吸収し、
    // スキーマ不一致と同じ「形式が想定と異なります」へ落とす。
    const body = await response.json().catch(() => null);
    const parsed = calculationResponseSchema.safeParse(body);
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
