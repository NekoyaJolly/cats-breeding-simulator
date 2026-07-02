import { z } from "zod";
import { registeredCatSchema, type RegisteredCat } from "./schema";

export const LOCAL_STORE_SCHEMA_VERSION = 1;
export const CALCULATION_HISTORY_LIMIT = 20;

export const syncStatusSchema = z.enum(["local", "synced", "pending", "conflict"]);
/** 将来のSupabase同期で使うローカルレコードの同期状態。 */
export type SyncStatus = z.infer<typeof syncStatusSchema>;

export const carrierFactSourceSchema = z.enum(["inferred", "verified"]);
/** キャリア情報が計算推定か、検査済み確定かを表す区分。 */
export type CarrierFactSource = z.infer<typeof carrierFactSourceSchema>;

export const breedingPlanStatusSchema = z.enum([
  "candidate",
  "testing",
  "planned",
  "mated",
  "pregnancy_check",
  "due",
  "born",
  "completed",
  "archived",
]);
/** 候補ペアから出産後までを追跡する交配計画ステータス。 */
export type BreedingPlanStatus = z.infer<typeof breedingPlanStatusSchema>;

const syncFieldsSchema = z.object({
  // 将来Supabase同期へ移すため、v1から所有者と同期状態の置き場だけ予約する。
  ownerId: z.string().optional(),
  syncStatus: syncStatusSchema,
  updatedAt: z.string(),
  deletedAt: z.string().optional(),
});

export const storedRegisteredCatSchema = registeredCatSchema.merge(syncFieldsSchema);
/** Storage v1内で保持する登録猫。UI用登録猫に同期予約フィールドを足したもの。 */
export type StoredRegisteredCat = z.infer<typeof storedRegisteredCatSchema>;

export const candidatePairSchema = syncFieldsSchema.extend({
  id: z.string(),
  targetColor: z.string(),
  targetSex: z.enum(["male", "female"]).optional(),
  sireCatId: z.string().optional(),
  damCatId: z.string().optional(),
  sireColor: z.string(),
  damColor: z.string(),
  confirmedProbabilityPct: z.number().optional(),
  conditionalMaxProbabilityPct: z.number().optional(),
  uncheckedFactors: z.array(z.string()),
  recommendedTests: z.array(z.string()),
  memo: z.string().optional(),
});
/** Target Coatの逆引き結果から保存する候補ペア。 */
export type CandidatePair = z.infer<typeof candidatePairSchema>;

export const breedingPlanSchema = syncFieldsSchema.extend({
  id: z.string(),
  candidatePairId: z.string().optional(),
  status: breedingPlanStatusSchema,
  plannedDate: z.string().optional(),
  matingStartDate: z.string().optional(),
  matingEndDate: z.string().optional(),
  matingCheckCount: z.number().int().nonnegative().optional(),
  pregnancyCheckDate: z.string().optional(),
  dueDate: z.string().optional(),
  memo: z.string().optional(),
});
/** 候補ペアを交配予定・出産予定まで進めるための計画レコード。 */
export type BreedingPlan = z.infer<typeof breedingPlanSchema>;

export const litterKittenSchema = z.object({
  id: z.string(),
  name: z.string().optional(),
  sex: z.enum(["male", "female"]).optional(),
  color: z.string(),
});
/** リター実績に含める子猫1頭分の毛色記録。 */
export type LitterKitten = z.infer<typeof litterKittenSchema>;

export const litterRecordSchema = syncFieldsSchema.extend({
  id: z.string(),
  breedingPlanId: z.string().optional(),
  candidatePairId: z.string().optional(),
  bornDate: z.string().optional(),
  kittens: z.array(litterKittenSchema),
  memo: z.string().optional(),
});
/** 出産後にKitten Coatsへ渡すためのリター実績レコード。 */
export type LitterRecord = z.infer<typeof litterRecordSchema>;

export const carrierFactSchema = syncFieldsSchema.extend({
  id: z.string(),
  catId: z.string().optional(),
  candidatePairId: z.string().optional(),
  litterRecordId: z.string().optional(),
  parent: z.enum(["sire", "dam"]).optional(),
  locus: z.string(),
  genotype: z.string(),
  source: carrierFactSourceSchema,
  evidence: z.array(z.string()),
  memo: z.string().optional(),
});
/** 推定キャリアと検査済み確定因子を同じ形式で扱うキャリア事実。 */
export type CarrierFact = z.infer<typeof carrierFactSchema>;

export const calculationHistoryEntrySchema = syncFieldsSchema.extend({
  id: z.string(),
  kind: z.enum(["parent-coat", "target-coat", "kitten-coats"]),
  title: z.string(),
  inputSummary: z.array(z.string()),
  resultSummary: z.array(z.string()),
  createdAt: z.string(),
});
/** Parent/Target/Kitten各計算の要約履歴。履歴上限はStorage側で20件に丸める。 */
export type CalculationHistoryEntry = z.infer<typeof calculationHistoryEntrySchema>;

export const userSettingsSchema = z.object({
  language: z.enum(["ja", "en"]).optional(),
  historyLimit: z.literal(CALCULATION_HISTORY_LIMIT),
});
/** Local Store v1に保存するユーザー設定。 */
export type UserSettings = z.infer<typeof userSettingsSchema>;

export const localStoreStateSchema = z.object({
  schemaVersion: z.literal(LOCAL_STORE_SCHEMA_VERSION),
  registeredCats: z.array(storedRegisteredCatSchema),
  candidatePairs: z.array(candidatePairSchema),
  breedingPlans: z.array(breedingPlanSchema),
  litterRecords: z.array(litterRecordSchema),
  carrierFacts: z.array(carrierFactSchema),
  calculationHistory: z.array(calculationHistoryEntrySchema),
  userSettings: userSettingsSchema,
});
/** import/exportとIndexedDBに保存するLocal Store v1全体の状態。 */
export type LocalStoreState = z.infer<typeof localStoreStateSchema>;

type JsonPrimitive = string | number | boolean | null;
/** 外部JSONをZod検証へ渡すためのJSON値型。 */
export type JsonValue = JsonPrimitive | JsonValue[] | { [key: string]: JsonValue };

export function createEmptyLocalStoreState(): LocalStoreState {
  return {
    schemaVersion: LOCAL_STORE_SCHEMA_VERSION,
    registeredCats: [],
    candidatePairs: [],
    breedingPlans: [],
    litterRecords: [],
    carrierFacts: [],
    calculationHistory: [],
    userSettings: { historyLimit: CALCULATION_HISTORY_LIMIT },
  };
}

export function parseJsonValue(raw: string): JsonValue | null {
  try {
    return JSON.parse(raw) as JsonValue;
  } catch {
    return null;
  }
}

export function normalizeLocalStoreState(value: JsonValue): LocalStoreState {
  const parsed = localStoreStateSchema.safeParse(value);
  if (!parsed.success) return createEmptyLocalStoreState();
  return {
    ...parsed.data,
    calculationHistory: parsed.data.calculationHistory.slice(0, CALCULATION_HISTORY_LIMIT),
  };
}

export function exportLocalStoreState(state: LocalStoreState): string {
  return JSON.stringify(normalizeLocalStoreState(state), null, 2);
}

export function importLocalStoreState(raw: string): LocalStoreState | null {
  const parsedJson = parseJsonValue(raw);
  if (parsedJson === null) return null;
  const parsedState = localStoreStateSchema.safeParse(parsedJson);
  if (!parsedState.success) return null;
  return normalizeLocalStoreState(parsedState.data);
}

function sameCarrierMap(
  left: RegisteredCat["carriers"],
  right: RegisteredCat["carriers"],
): boolean {
  return JSON.stringify(left ?? {}) === JSON.stringify(right ?? {});
}

function sameRegisteredCatData(cat: RegisteredCat, stored: StoredRegisteredCat): boolean {
  return (
    cat.name === stored.name &&
    cat.sex === stored.sex &&
    cat.color === stored.color &&
    cat.breed === stored.breed &&
    sameCarrierMap(cat.carriers, stored.carriers)
  );
}

export function activeRegisteredCats(state: LocalStoreState): RegisteredCat[] {
  return state.registeredCats
    .filter((cat) => !cat.deletedAt)
    .map(({ id, name, sex, color, breed, carriers }) => {
      const cat: RegisteredCat = { id, name, sex, color };
      if (breed) cat.breed = breed;
      if (carriers) cat.carriers = carriers;
      return cat;
    });
}

export function mergeRegisteredCatsForStorage(
  cats: RegisteredCat[],
  storedCats: StoredRegisteredCat[],
  now: string,
): StoredRegisteredCat[] {
  const storedById = new Map(storedCats.map((cat) => [cat.id, cat]));
  const activeIds = new Set(cats.map((cat) => cat.id));
  const nextCats = cats.map((cat) => {
    const previous = storedById.get(cat.id);
    if (previous && sameRegisteredCatData(cat, previous) && !previous.deletedAt) {
      return previous;
    }
    return {
      ...cat,
      ownerId: previous?.ownerId,
      syncStatus: previous?.syncStatus === "synced" ? "pending" : previous?.syncStatus ?? "local",
      updatedAt: now,
      deletedAt: undefined,
    };
  });

  const deletedCats = storedCats
    .filter((cat) => !activeIds.has(cat.id))
    .map((cat) => {
      if (cat.deletedAt) return cat;
      return {
        ...cat,
        syncStatus: cat.syncStatus === "synced" ? "pending" : cat.syncStatus,
        updatedAt: now,
        deletedAt: now,
      };
    });

  return [...nextCats, ...deletedCats];
}

export function legacyRegisteredCatsToState(cats: RegisteredCat[], now: string): LocalStoreState {
  const state = createEmptyLocalStoreState();
  return {
    ...state,
    registeredCats: cats.map((cat) => ({
      ...cat,
      syncStatus: "local",
      updatedAt: now,
    })),
  };
}
