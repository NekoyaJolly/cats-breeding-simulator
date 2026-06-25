import { z } from "zod";

// バックエンド (cat_breeding_simulator/api.py) のレスポンス契約を
// フロント側で再宣言し、外部入力をランタイム検証する (AGENTS 最優先5原則 §2)。
// any / unknown を持ち込まず、ここで具体型へ narrow する。

// 1 表現型エントリ (api.py ResultEntry に対応)
export const resultEntrySchema = z.object({
  sex: z.string(),
  color: z.string(),
  probability_pct: z.number(),
});
export type ResultEntry = z.infer<typeof resultEntrySchema>;

// モード情報・診断値 (api.py ModeDiagnostics に対応)
export const modeDiagnosticsSchema = z.object({
  opened_loci: z.array(z.string()),
  closed_loci: z.array(z.string()),
  assumptions: z.array(z.string()),
  matched_probability: z.number(),
  unmatched_probability: z.number(),
  unmatched_genotype_count: z.number(),
});
export type ModeDiagnostics = z.infer<typeof modeDiagnosticsSchema>;

// carrier_exploration の条件付きシナリオ (api.py CarrierScenarioEntry に対応)。
// 通常結果とは完全分離して表示する (シミュレーター正本 §2)。
export const carrierScenarioEntrySchema = z.object({
  scenario: z.string(),
  label: z.string(),
  assumed_carriers: z.record(z.record(z.string())),
  probability_basis: z.string(),
  prior_probability_applied: z.boolean(),
  results: z.array(resultEntrySchema),
  new_colors: z.array(z.string()),
});
export type CarrierScenarioEntry = z.infer<typeof carrierScenarioEntrySchema>;

// 計算 API レスポンス全体 (api.py CalculationResponse に対応)
export const calculationResponseSchema = z.object({
  status: z.string(),
  mode: z.string(),
  parameters: z.object({
    sire_color: z.string(),
    dam_color: z.string(),
    breed: z.string().nullable().optional(),
    mode: z.string(),
    sire_carriers: z.record(z.string()).nullable().optional(),
    dam_carriers: z.record(z.string()).nullable().optional(),
  }),
  results: z.array(resultEntrySchema),
  diagnostics: modeDiagnosticsSchema,
  // carrier_exploration_mode のときのみ非 null。
  carrier_exploration_results: z.array(carrierScenarioEntrySchema).nullable().optional(),
});
export type CalculationResponse = z.infer<typeof calculationResponseSchema>;

// FastAPI のエラー応答 (HTTPException.detail)。
// 自前の BreedingCalculationError は文字列、pydantic 検証エラーは配列で返る。
export const apiErrorSchema = z.object({
  detail: z.union([z.string(), z.array(z.object({ msg: z.string() }))]),
});

// 入力サジェスト用の 1 色エントリ (api.py ColorOption に対応)。
export const colorOptionSchema = z.object({
  value: z.string(),
  reading_ja: z.string(),
  status: z.string(),
  breed_context: z.string(),
  sex_restriction: z.string(),
  keywords: z.array(z.string()),
});
export type ColorOption = z.infer<typeof colorOptionSchema>;

// GET /api/v1/colors のレスポンス (api.py ColorsResponse に対応)。
export const colorsResponseSchema = z.object({
  colors: z.array(colorOptionSchema),
});
export type ColorsResponse = z.infer<typeof colorsResponseSchema>;
