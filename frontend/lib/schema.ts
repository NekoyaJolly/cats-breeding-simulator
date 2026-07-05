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

// 入力した親色が子に出現しないときの注釈 (api.py ParentColorNoteEntry に対応)。
export const parentColorNoteSchema = z.object({
  parent: z.string(), // "sire" / "dam"
  color: z.string(),
  blocked_factors: z.array(z.string()),
});
export type ParentColorNote = z.infer<typeof parentColorNoteSchema>;

// 「もしこの色が出たら」= 隠れキャリアを仮定した場合にのみ出る条件付きカラー群
// (api.py ConditionalColorGroup に対応)。確定色 (confirmed_results) とは分離して表示し、
// 「この色が出たら親の遺伝子型が確定する (逆推論)」という気付きを提供する。
export const conditionalColorGroupSchema = z.object({
  family_label: z.string(), // 例 "ブルー系"
  reverse_inference_label: z.string(), // 例 "この色が出たら両親が D/d 保因と確定します"
  conditional_probability_pct: z.number(), // 隠れキャリア仮定時の条件付き確率
  colors: z.array(z.string()), // 例 ["Blue"]
  assumed_carriers: z.record(z.record(z.string())), // 例 {"sire":{"D":"D/d"},"dam":{"D":"D/d"}}
  scenario: z.string(),
});
export type ConditionalColorGroup = z.infer<typeof conditionalColorGroupSchema>;

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
  // 隠れキャリアを仮定しない「確定色」のみ (normal モードで返る)。
  // 無い場合 (後方互換) はメイン表示で results にフォールバックする。
  confirmed_results: z.array(resultEntrySchema).nullable().optional(),
  // 「もしこの色が出たら」= 隠れキャリア仮定時のみ出る条件付きカラー群
  // (normal モードのみ、該当なしや他モードでは空配列)。
  conditional_color_groups: z.array(conditionalColorGroupSchema).optional().default([]),
  diagnostics: modeDiagnosticsSchema,
  // carrier_exploration_mode のときのみ非 null。
  carrier_exploration_results: z.array(carrierScenarioEntrySchema).nullable().optional(),
  // 入力した親色が子に出ないときの注釈 (normal モードのみ、無ければ空配列)。
  parent_color_notes: z.array(parentColorNoteSchema).optional().default([]),
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

// 入力サジェスト用の 1 猫種エントリ (api.py BreedOption に対応)。
export const breedOptionSchema = z.object({
  value: z.string(),
  affects_genetics: z.boolean(),
});
export type BreedOption = z.infer<typeof breedOptionSchema>;

// GET /api/v1/breeds のレスポンス (api.py BreedsResponse に対応)。
export const breedsResponseSchema = z.object({
  breeds: z.array(breedOptionSchema),
});
export type BreedsResponse = z.infer<typeof breedsResponseSchema>;

// GET /api/v1/breed-colors: その猫種で使える毛色 (認定カラー案内ポップアップ用)。
export const breedColorsResponseSchema = z.object({
  breed: z.string(),
  constrained: z.boolean(),
  colors: z.array(z.string()),
});
export type BreedColorsResponse = z.infer<typeof breedColorsResponseSchema>;

// 目標カラーから探す: 登録猫入力。
export const registeredCatSchema = z.object({
  id: z.string(),
  name: z.string(),
  sex: z.enum(["male", "female"]),
  color: z.string(),
  breed: z.string().optional(),
  carriers: z.record(z.string()).optional(),
});
export type RegisteredCat = z.infer<typeof registeredCatSchema>;

// 目標カラーから探す: 座位別根拠。
export const locusEvidenceSchema = z.object({
  locus: z.string(),
  target: z.string(),
  sire: z.string(),
  dam: z.string(),
  status: z.string(),
  note: z.string(),
});
export type LocusEvidence = z.infer<typeof locusEvidenceSchema>;

// 目標カラーから探す: 交配候補。
export const reverseLookupCandidateSchema = z.object({
  category: z.string(),
  sire: z.object({
    id: z.string(),
    name: z.string(),
    color: z.string(),
    breed: z.string().nullable(),
  }),
  dam: z.object({
    id: z.string(),
    name: z.string(),
    color: z.string(),
    breed: z.string().nullable(),
  }),
  target_color: z.string(),
  confirmed_probability_pct: z.number(),
  conditional_max_probability_pct: z.number(),
  establishment_conditions: z.array(z.string()),
  confirmation_needed: z.array(z.string()),
  recommended_tests: z.array(z.string()),
  locus_evidence: z.array(locusEvidenceSchema),
  target_possible_colors: z.array(resultEntrySchema).optional().default([]),
  other_possible_colors: z.array(resultEntrySchema),
});
export type ReverseLookupCandidate = z.infer<typeof reverseLookupCandidateSchema>;

// 目標カラーから探す: APIレスポンス。
export const reverseLookupResponseSchema = z.object({
  status: z.string(),
  target_color: z.string(),
  target_sex: z.enum(["male", "female"]).nullable().optional(),
  response_category: z.string(),
  target_conditions: z.array(z.string()),
  unchecked_conditions: z.array(z.string()),
  recommended_checks: z.array(z.string()),
  candidates: z.array(reverseLookupCandidateSchema),
});
export type ReverseLookupResponse = z.infer<typeof reverseLookupResponseSchema>;

// リター実績から推定: 座位別結果。
export const inferenceFindingSchema = z.object({
  category: z.string(),
  parent: z.string(),
  locus: z.string(),
  genotype: z.string(),
  note: z.string(),
  support_pct: z.number(),
});
export type InferenceFinding = z.infer<typeof inferenceFindingSchema>;

// リター実績から推定: APIレスポンス。
export const litterInferenceResponseSchema = z.object({
  status: z.string(),
  response_category: z.string(),
  candidate_pair_count: z.number(),
  confirmed: z.array(inferenceFindingSchema),
  conditional: z.array(inferenceFindingSchema),
  inferred: z.array(inferenceFindingSchema),
  unconfirmed: z.array(inferenceFindingSchema),
  contradictions: z.array(z.string()),
  warnings: z.array(z.string()),
  recommended_tests: z.array(z.string()),
});
export type LitterInferenceResponse = z.infer<typeof litterInferenceResponseSchema>;

// POST /api/v1/feedback: フィードバック受付結果 (sent=管理者へのメール送信成否)。
export const feedbackResponseSchema = z.object({
  sent: z.boolean(),
});
export type FeedbackResponse = z.infer<typeof feedbackResponseSchema>;
