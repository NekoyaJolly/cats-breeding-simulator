import type {
  RegisteredCat,
  ResultEntry,
  ReverseLookupResponse,
} from "@/lib/schema";

// 目標カラー探索の表示ロジックで共有する純粋ヘルパー群。
// UI から切り離して単体テスト可能にするため、コンポーネントとは別ファイルに置く。

// 候補一覧でユーザーに見せる産出条件。判定保留/確認不可は候補なし案内側で扱う。
export const PUBLIC_CATEGORIES = [
  "確定で期待できる",
  "条件付きで期待できる",
] as const;

// 確率を「12%」「12.5%」のように整数なら小数点なしで表示する。
export function formatPct(value: number): string {
  return `${value.toFixed(value % 1 === 0 ? 0 : 1)}%`;
}

// 登録猫の性別を、入力欄と同じ性別ラベルに変換する。
export function sexLabel(sex: RegisteredCat["sex"]): string {
  return sex === "male" ? "♂ オス" : "♀ メス";
}

// 目標とする子猫の性別ラベル (未指定は「指定なし」)。
export function targetSexLabel(sex: ReverseLookupResponse["target_sex"]): string {
  if (sex === "male") return "♂ オス";
  if (sex === "female") return "♀ メス";
  return "指定なし";
}

// 目標カラー以外に生まれ得るカラー行を、先頭8件まで「♀ 色 12%」形式で連結する。
export function colorRows(
  rows: ResultEntry[],
  emptyText = "現在の計算範囲では表示できるカラーがありません。",
): string {
  if (rows.length === 0) return emptyText;
  return rows
    .slice(0, 8)
    .map(
      (row) =>
        `${row.sex === "Female" ? "♀" : "♂"} ${row.color} ${formatPct(row.probability_pct)}`,
    )
    .join(" / ");
}

// 確認済み因子 (キャリア) を「B:B/b, D:D/d」形式の文字列にする。未登録は空文字。
export function carriersText(carriers: RegisteredCat["carriers"]): string {
  if (!carriers) return "";
  return Object.entries(carriers)
    .map(([locus, genotype]) => `${locus}:${genotype}`)
    .join(", ");
}
