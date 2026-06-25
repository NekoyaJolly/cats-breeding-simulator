import type { ColorOption } from "./schema";

// 入力サジェストの突合処理 (純粋関数)。React に依存しないためロジックを単体検証できる。
// 英名・略称・カナ読みを横断して絞り込む。日本語はひらがな→カタカナへ畳み込む。

// 突合キーを正規化する: ひらがな→カタカナ / 小文字化 / 空白・記号除去。
// これにより "ぶらうん"・"Brown"・"brown tabby"・"ブラウンタビー" が同じ土俵で比較される。
export function normalizeKey(input: string): string {
  let folded = "";
  for (const ch of input) {
    const code = ch.codePointAt(0) ?? 0;
    // ひらがな (U+3041–U+3096) を同じ並びのカタカナ (U+30A1–U+30F6) へ +0x60 でシフト。
    if (code >= 0x3041 && code <= 0x3096) {
      folded += String.fromCodePoint(code + 0x60);
    } else {
      folded += ch;
    }
  }
  return folded.toLowerCase().replace(/[\s　\-_/().,・。．]/g, "");
}

// 1 色が正規化済み query にどの程度マッチするか。小さいほど上位。マッチしなければ null。
// 0 = value/読みの前方一致、1 = いずれかのキーの前方一致、2 = 部分一致。
function scoreColor(color: ColorOption, query: string): number | null {
  const valueKey = normalizeKey(color.value);
  const readingKey = normalizeKey(color.reading_ja);
  if (valueKey.startsWith(query) || readingKey.startsWith(query)) return 0;

  let best: number | null = null;
  for (const keyword of color.keywords) {
    const idx = normalizeKey(keyword).indexOf(query);
    if (idx === 0) {
      best = best === null ? 1 : Math.min(best, 1);
    } else if (idx > 0) {
      best = best === null ? 2 : Math.min(best, 2);
    }
  }
  return best;
}

// query で colors を絞り込み、関連度→名前長→辞書順で並べて上位 limit 件を返す。
// query が空なら先頭 limit 件をそのまま返す (呼び出し側が履歴を優先表示する想定)。
export function filterColors(
  colors: ColorOption[],
  query: string,
  limit = 20,
): ColorOption[] {
  const q = normalizeKey(query);
  if (q.length === 0) return colors.slice(0, limit);

  const ranked: Array<{ color: ColorOption; score: number }> = [];
  for (const color of colors) {
    const score = scoreColor(color, q);
    if (score !== null) ranked.push({ color, score });
  }
  ranked.sort(
    (a, b) =>
      a.score - b.score ||
      a.color.value.length - b.color.value.length ||
      a.color.value.localeCompare(b.color.value),
  );
  return ranked.slice(0, limit).map((entry) => entry.color);
}
