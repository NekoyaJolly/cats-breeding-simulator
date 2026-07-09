// 結果レポートのアコーディオン各セクションの「並び順」と「展開状態」を localStorage に永続化する。
// 既定は全セクション非展開。ユーザーが展開/並び替えした最後の状態を保存し、次回計算結果に反映する。
//
// localStorage の値は外部入力相当なので、他の永続化 (localStoreSchema) と同様に
// parseJsonValue + Zod safeParse で検証してから具体型へ narrow する。

import { z } from "zod";
import { parseJsonValue } from "./localStoreSchema";

export const sectionIdSchema = z.enum([
  "confirmed",
  "distribution",
  "conditional",
  "normalNote",
  "genetics",
]);
export type SectionId = z.infer<typeof sectionIdSchema>;

// 既定の並び順 (確定色 → 全分布 → 両親キャリア推定 → 通常モード注記 → 遺伝子情報)。
export const DEFAULT_SECTION_ORDER: readonly SectionId[] = [
  "confirmed",
  "distribution",
  "conditional",
  "normalNote",
  "genetics",
];

const ORDER_KEY = "cbs:resultSectionOrder";
const OPEN_KEY = "cbs:resultSectionOpen";

// 未知IDが混じっても全体を捨てず既知分だけ拾えるよう、要素は緩く string で受けて後段で narrow する
// (バージョン差でセクションが増減しても壊れないようにするため)。
const rawOrderSchema = z.array(z.string());
const rawOpenSchema = z.record(z.boolean());

function readJson<T>(key: string, schema: z.ZodType<T>): T | null {
  let raw: string | null;
  try {
    raw = localStorage.getItem(key);
  } catch {
    return null;
  }
  if (raw === null) return null;
  const json = parseJsonValue(raw);
  if (json === null) return null;
  const parsed = schema.safeParse(json);
  return parsed.success ? parsed.data : null;
}

/** 保存済みの並び順を返す。既知IDのみに正規化し、欠けているIDは既定順で末尾補完する。 */
export function loadSectionOrder(): SectionId[] {
  const stored = readJson(ORDER_KEY, rawOrderSchema) ?? [];
  const seen = new Set<SectionId>();
  const order: SectionId[] = [];
  for (const value of stored) {
    const id = sectionIdSchema.safeParse(value);
    if (id.success && !seen.has(id.data)) {
      seen.add(id.data);
      order.push(id.data);
    }
  }
  // 未知/欠落は既定順で補完 (新セクション追加時も壊れない)。
  for (const id of DEFAULT_SECTION_ORDER) {
    if (!seen.has(id)) order.push(id);
  }
  return order;
}

export function saveSectionOrder(order: SectionId[]): void {
  try {
    localStorage.setItem(ORDER_KEY, JSON.stringify(order));
  } catch {
    // 保存できない環境でも、現在の画面上の並び順は維持する。
  }
}

/** 保存済みの展開状態 (id → open) を返す。未保存は空 = 全非展開。 */
export function loadSectionOpen(): Partial<Record<SectionId, boolean>> {
  const stored = readJson(OPEN_KEY, rawOpenSchema) ?? {};
  const open: Partial<Record<SectionId, boolean>> = {};
  for (const [key, value] of Object.entries(stored)) {
    const id = sectionIdSchema.safeParse(key);
    if (id.success) open[id.data] = value;
  }
  return open;
}

export function saveSectionOpen(open: Partial<Record<SectionId, boolean>>): void {
  try {
    localStorage.setItem(OPEN_KEY, JSON.stringify(open));
  } catch {
    // 保存できない環境でも、現在の展開状態は維持する。
  }
}
