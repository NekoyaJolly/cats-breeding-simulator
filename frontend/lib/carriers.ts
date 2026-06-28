// "C:C/cs, B:B/b" 形式のテキストを座位→遺伝子型の辞書へ変換する。
// 入力が空、または有効なペアが無い場合は undefined を返す。
export function parseCarriers(text: string): Record<string, string> | undefined {
  const trimmed = text.trim();
  if (!trimmed) return undefined;
  const entries: Record<string, string> = {};
  for (const part of trimmed.split(",")) {
    const [locus, genotype] = part.split(":").map((token) => token.trim());
    if (locus && genotype) entries[locus] = genotype;
  }
  return Object.keys(entries).length > 0 ? entries : undefined;
}
