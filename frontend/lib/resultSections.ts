// 結果レポートのアコーディオン各セクションの「並び順」と「展開状態」を localStorage に永続化する。
// 既定は全セクション非展開。ユーザーが展開/並び替えした最後の状態を保存し、次回計算結果に反映する。

export type SectionId =
  | "confirmed"
  | "distribution"
  | "conditional"
  | "normalNote"
  | "genetics";

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

const KNOWN: ReadonlySet<string> = new Set(DEFAULT_SECTION_ORDER);

function isSectionId(value: unknown): value is SectionId {
  return typeof value === "string" && KNOWN.has(value);
}

/** 保存済みの並び順を返す。既知IDのみに正規化し、欠けているIDは既定順で末尾補完する。 */
export function loadSectionOrder(): SectionId[] {
  let stored: unknown = null;
  try {
    const raw = localStorage.getItem(ORDER_KEY);
    stored = raw ? JSON.parse(raw) : null;
  } catch {
    stored = null;
  }
  const seen = new Set<SectionId>();
  const order: SectionId[] = [];
  if (Array.isArray(stored)) {
    for (const value of stored) {
      if (isSectionId(value) && !seen.has(value)) {
        seen.add(value);
        order.push(value);
      }
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
  let stored: unknown = null;
  try {
    const raw = localStorage.getItem(OPEN_KEY);
    stored = raw ? JSON.parse(raw) : null;
  } catch {
    stored = null;
  }
  const open: Partial<Record<SectionId, boolean>> = {};
  if (stored && typeof stored === "object") {
    for (const [key, value] of Object.entries(stored)) {
      if (isSectionId(key) && typeof value === "boolean") open[key] = value;
    }
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
