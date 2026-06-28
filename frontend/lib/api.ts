import {
  apiErrorSchema,
  breedColorsResponseSchema,
  breedsResponseSchema,
  calculationResponseSchema,
  colorsResponseSchema,
  feedbackResponseSchema,
  litterInferenceResponseSchema,
  reverseLookupResponseSchema,
  type BreedOption,
  type CalculationResponse,
  type ColorOption,
  type LitterInferenceResponse,
  type RegisteredCat,
  type ReverseLookupResponse,
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

export type ReverseLookupInput = {
  target_color: string;
  target_sex?: "male" | "female";
  cats: RegisteredCat[];
  limit?: number;
};

export type ReverseLookupOutcome =
  | { ok: true; data: ReverseLookupResponse }
  | { ok: false; message: string };

export type LitterInferenceInput = {
  sire: {
    color: string;
    breed?: string;
  };
  dam: {
    color: string;
    breed?: string;
  };
  kittens: Array<{
    id: string;
    sex: "male" | "female";
    color: string;
    name?: string;
  }>;
};

export type LitterInferenceOutcome =
  | { ok: true; data: LitterInferenceResponse }
  | { ok: false; message: string };

// バックエンドの冗長なエラー文を簡潔な日本語へ整形する。
// 例: "Unsupported color 'X'. Supported colors: <全色>" の長い一覧を省く。
function cleanErrorMessage(detail: string): string {
  const unsupportedColor = detail.match(/Unsupported color '(.+?)'\./);
  if (unsupportedColor) {
    return `「${unsupportedColor[1]}」は対応していない毛色です。候補から選んでください。`;
  }
  const invalidForSex = detail.match(/Color '(.+?)' is not valid for a (male|female)\./);
  if (invalidForSex) {
    const parent =
      invalidForSex[2] === "male" ? "オス親（♀限定の毛色）" : "メス親";
    return `「${invalidForSex[1]}」は${parent}には指定できない毛色です。`;
  }
  return detail; // それ以外 (既に簡潔な日本語メッセージ等) はそのまま返す。
}

// FastAPI のエラー detail を日本語メッセージへ整形する。
// 文字列は自前の BreedingCalculationError (日本語)。配列は pydantic の検証エラーで
// msg が英語のため、そのまま出さず日本語の総括メッセージにする。
function describeError(detail: string | Array<{ msg: string }>): string {
  if (typeof detail === "string") return cleanErrorMessage(detail);
  return "入力内容に誤りがあります。毛色が正しく入力されているか確認してください。";
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

// GET /api/v1/breeds を叩き、入力サジェスト/バリデーション用の猫種一覧を返す。
// 失敗時は空配列 (猫種は任意入力なので自由入力で継続できる)。
export async function fetchBreeds(): Promise<BreedOption[]> {
  let response: Response;
  try {
    response = await fetch("/api/v1/breeds", {
      headers: { Accept: "application/json" },
    });
  } catch {
    return [];
  }
  if (!response.ok) return [];
  const body = await response.json().catch(() => null);
  const parsed = breedsResponseSchema.safeParse(body);
  return parsed.success ? parsed.data.breeds : [];
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

// POST /api/v1/reverse-lookup を叩き、登録猫から目標カラーの交配候補を検索する。
export async function searchTargetColor(
  input: ReverseLookupInput,
): Promise<ReverseLookupOutcome> {
  let response: Response;
  try {
    response = await fetch("/api/v1/reverse-lookup", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(input),
    });
  } catch {
    return {
      ok: false,
      message:
        "バックエンドに接続できませんでした。API サーバ (uvicorn) が起動しているか確認してください。",
    };
  }

  if (response.ok) {
    const body = await response.json().catch(() => null);
    const parsed = reverseLookupResponseSchema.safeParse(body);
    if (!parsed.success) {
      return { ok: false, message: "逆引きAPIレスポンスの形式が想定と異なります。" };
    }
    return { ok: true, data: parsed.data };
  }

  const errorBody = await response.json().catch(() => null);
  const parsedError = apiErrorSchema.safeParse(errorBody);
  if (parsedError.success) {
    return { ok: false, message: describeError(parsedError.data.detail) };
  }
  return { ok: false, message: `エラーが発生しました (HTTP ${response.status})。` };
}

// POST /api/v1/litter-inference を叩き、リター実績から親の因子候補を推定する。
export async function inferFromLitter(
  input: LitterInferenceInput,
): Promise<LitterInferenceOutcome> {
  let response: Response;
  try {
    response = await fetch("/api/v1/litter-inference", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(input),
    });
  } catch {
    return {
      ok: false,
      message:
        "バックエンドに接続できませんでした。API サーバ (uvicorn) が起動しているか確認してください。",
    };
  }

  if (response.ok) {
    const body = await response.json().catch(() => null);
    const parsed = litterInferenceResponseSchema.safeParse(body);
    if (!parsed.success) {
      return { ok: false, message: "リター推定APIレスポンスの形式が想定と異なります。" };
    }
    return { ok: true, data: parsed.data };
  }

  const errorBody = await response.json().catch(() => null);
  const parsedError = apiErrorSchema.safeParse(errorBody);
  if (parsedError.success) {
    return { ok: false, message: describeError(parsedError.data.detail) };
  }
  return { ok: false, message: `エラーが発生しました (HTTP ${response.status})。` };
}

// GET /api/v1/breed-colors: 指定猫種で使える毛色一覧 (認定カラー案内ポップアップ用)。
// 失敗時 / 制約なし猫種は空配列を返す (呼び出し側はポップアップを出さない)。
export async function fetchBreedColors(breed: string): Promise<string[]> {
  let response: Response;
  try {
    response = await fetch(
      `/api/v1/breed-colors?breed=${encodeURIComponent(breed)}`,
      { headers: { Accept: "application/json" } },
    );
  } catch {
    return [];
  }
  if (!response.ok) return [];
  const body = await response.json().catch(() => null);
  const parsed = breedColorsResponseSchema.safeParse(body);
  if (!parsed.success || !parsed.data.constrained) return [];
  return parsed.data.colors;
}

// POST /api/v1/feedback: フィードバックを送る。sent=管理者へのメール送信に成功したか
// (サーバーのメール設定により false の場合がある)。送信自体に失敗したら例外を投げる。
export async function submitFeedback(message: string): Promise<{ sent: boolean }> {
  const response = await fetch("/api/v1/feedback", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message }),
  });
  if (!response.ok) {
    throw new Error("フィードバックの送信に失敗しました");
  }
  const body = await response.json().catch(() => null);
  const parsed = feedbackResponseSchema.safeParse(body);
  // 形式不一致は黙って成功扱いにせず例外にする (バックエンドの破損/想定外変更を UI で検知)。
  if (!parsed.success) {
    throw new Error("フィードバックの応答形式が想定と異なります");
  }
  return { sent: parsed.data.sent };
}
