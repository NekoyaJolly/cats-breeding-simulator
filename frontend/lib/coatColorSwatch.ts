// 毛色名から色見本 (swatch) の CSS background を組み立てる。色系統の近似ではなく「その毛色
// そのもの」を、下地→先端 (ティッピング) やトーティの2色を重ねて (レイヤー) 視覚化するのが狙い。
//   - シルバー/スモーク/カメオ = 白い下地 → 先端に色
//   - ゴールデン = アプリコットの下地 → 暗い先端
//   - トーティ/トーティシェル/キャリコ/パッチド/ブルークリーム等 = 2色の斜めグラデ
//     (ティッピングありなら白帯、ゴールデンならアプリコット帯を挟む)
//   - ポイント = 淡い体色
// なお shell/shaded/chinchilla は「度合い」語でシルバー/ゴールデン双方に付くため、下地色の判定
// (isSilver/isGolden) には使わず、ティッピングの有無 (degreeTipped) の判定にのみ使う。
// あくまで近似の見本なので、色名テキストと併記して使う。

// ユーメラニン系ベース (黒/チョコ/シナモン と各希釈、および品種呼称)。
const EUMELANIN_HEX: Record<string, string> = {
  black: "#3d3a37",
  ebony: "#3d3a37",
  blue: "#8b96a3",
  chocolate: "#5e3d2b",
  chestnut: "#5e3d2b",
  brown: "#6b5140",
  lilac: "#b6a9af",
  lavender: "#b6a9af",
  cinnamon: "#a3623a",
  fawn: "#cdb69d",
  sable: "#4a3728",
  seal: "#493a31",
  champagne: "#caa878",
  platinum: "#c4c0c1",
};

// フェオメラニン (赤/クリーム) と白、下地色。
const RED_HEX = "#d67a35";
const CREAM_HEX = "#eed9b6";
const WHITE_HEX = "#fafafa";
const SILVER_UNDERCOAT = "#f3f5f7";
const GOLDEN_UNDERCOAT = "#ecca85";

// タビーの統一テクスチャ (マッカレル/クラシック/ティックド/スポッテッドは区別せず「縞がある」ことだけ
// 表す)。縞の向きは「横 (0deg)」にする: 斜め縞は格子を斜めに横切りジャギーが出る。縦縞は LCD の
// サブピクセル (RGB縦列) と干渉して正面で色フリンジ/シマーが出る (斜めから見ると収まる)。横縞は
// サブピクセル縦列と直交し RGB を均等に覆うので、正面でもチラつかない。バッジは高さが低いので、
// 横縞は細く密に (2px実線＋2px空き=周期4px) して本数を確保し「縞」に見せる。
function tabbyStripes(stripeColor: string): string {
  return `repeating-linear-gradient(0deg, ${stripeColor} 0 2px, rgba(0,0,0,0) 2px 4px)`;
}

function hasWord(words: string[], word: string): boolean {
  return words.includes(word);
}

// ティッピングの度合い → 「色が乗る先端」の割合 (%)。実際の比率に寄せる: Chinchilla/Shell≈1/8、
// Shaded≈1/4、Smoke≈1/2。返すのは下地 (淡色) が占める上端からの % (= 100 - 先端割合)。
function undercoatShare(lower: string): number {
  if (/\b(chinchilla|shell)\b/.test(lower)) return 84; // 先端 ~16% (≈1/8)
  if (/\bshaded\b/.test(lower)) return 72; // 先端 ~28% (≈1/4)
  if (/\bsmoke\b/.test(lower)) return 50; // 先端 ~50% (≈1/2)
  return 58; // 度合い指定なし (シルバータビー等) は中庸
}

// 名前からユーメラニンのベース色を1つ選ぶ (最初に一致した色語)。無ければ黒。
function eumelaninBase(words: string[]): string {
  for (const key of [
    "blue",
    "chocolate",
    "chestnut",
    "lilac",
    "lavender",
    "cinnamon",
    "fawn",
    "sable",
    "seal",
    "champagne",
    "platinum",
    "ebony",
    "brown",
    "black",
  ]) {
    if (hasWord(words, key)) return EUMELANIN_HEX[key];
  }
  return EUMELANIN_HEX.black;
}

// 希釈 (blue/lilac/fawn/cream 系) かどうか。トーティの相方 (赤 or クリーム) を決める。
function isDiluteName(words: string[]): boolean {
  return (
    hasWord(words, "blue") ||
    hasWord(words, "lilac") ||
    hasWord(words, "lavender") ||
    hasWord(words, "fawn") ||
    hasWord(words, "cream")
  );
}

// 単色 (ソリッド) のベース色。赤/クリーム/白のソリッドも拾う。
function solidBase(words: string[]): string {
  if (hasWord(words, "white")) return WHITE_HEX;
  if (hasWord(words, "cream")) return CREAM_HEX;
  if (hasWord(words, "red")) return RED_HEX;
  return eumelaninBase(words);
}

/** 毛色名 → 色見本の CSS background 文字列。 */
export function coatSwatchBackground(name: string): string {
  const lower = name.toLowerCase();
  const words = lower.split(/[\s()\-]+/).filter(Boolean);

  const isTortie =
    /\b(tortoiseshell|tortie|torbie|calico)\b/.test(lower) ||
    /\bpatched\b/.test(lower) ||
    /\b(blue|lilac|fawn)\s+cream\b/.test(lower);
  // 下地色の判定は silver/smoke/cameo (白下地) と golden (アプリコット下地) のみで行う。
  const isGolden = /\bgolden\b/.test(lower);
  const isSilver = /\b(silver|smoke|cameo)\b/.test(lower);
  const degreeTipped = /\b(shell|shaded|chinchilla)\b/.test(lower);
  const isPoint = /\b(point|lynx)\b/.test(lower);
  // Lynx = タビーなので、Lynx を含むポイントもタビー縞を出す。
  const isTabby = /\b(tabby|mackerel|classic|ticked|spotted|lynx)\b/.test(lower);
  // 先端 (色が乗る側) が占める割合。実際のティッピングに寄せる (Chinchilla≈1/8 / Shaded≈1/4 /
  // Smoke≈1/2)。先端は「上」に置く (毛の先端=外側)。境目はハードでなくフェードにする。
  const tip = 100 - undercoatShare(lower);
  const fadeEnd = Math.min(tip + 22, 100); // フェードの終わり (ここから下は下地一色)

  // 縞は一律に黒 (地色より暗い縞 = 実際のタビーに近く、人間の可読性も高い)。白縞は色ごとに太さ感が
  // ばらつくため使わない。暗い毛色では自然とコントラストが下がる (実物の黒猫のタビーも同様)。
  const withTabby = (bg: string): string =>
    isTabby ? `${tabbyStripes("rgba(0,0,0,0.4)")}, ${bg}` : bg;
  // ポイント (cs) は体色が温度依存で淡い。全体に白のオーバーレイを重ねて ~0.5 トーン淡くする。
  const withPoint = (bg: string): string =>
    isPoint
      ? `linear-gradient(rgba(255,255,255,0.42), rgba(255,255,255,0.42)), ${bg}`
      : bg;
  // 仕上げ: 毛色ベースにタビー縞 → ポイントの淡色化を重ねる。
  const finish = (bg: string): string => withTabby(withPoint(bg));

  // トーティ/キャリコ = ユーメラニン + フェオ (濃=赤 / 淡=クリーム) の2色を横 50/50 で統一。
  // ティッピングがある場合は、横 50/50 は保ったまま「下地の淡色 (シルバー=白 / ゴールデン=
  // アプリコット)」を下側から縦フェードで重ねる (先端=上は元色、根元=下は下地が透ける)。
  if (isTortie) {
    const eumel = eumelaninBase(words);
    const pheo = isDiluteName(words) ? CREAM_HEX : RED_HEX;
    const tortie = `linear-gradient(135deg, ${eumel} 0 50%, ${pheo} 50% 100%)`;
    if (isGolden || isSilver || degreeTipped) {
      const under = isGolden ? "rgba(236,202,133,0.80)" : "rgba(243,245,247,0.85)";
      const undercoatFade = `linear-gradient(180deg, rgba(0,0,0,0) 0 ${tip}%, ${under} 100%)`;
      return finish(`${undercoatFade}, ${tortie}`);
    }
    return finish(tortie);
  }

  // ゴールデン = 先端に暗い色 (上) → アプリコットの下地 (下)。フェードで繋ぐ。度合いで比率が変わる。
  if (isGolden) {
    return finish(
      `linear-gradient(180deg, ${eumelaninBase(words)} 0 ${tip}%, ${GOLDEN_UNDERCOAT} ${fadeEnd}% 100%)`,
    );
  }

  // シルバー/スモーク/カメオ = 先端に色 (上) → 白い下地 (下)。フェードで繋ぐ。カメオは赤/クリームの先端。
  if (isSilver) {
    const tipColor = hasWord(words, "cameo")
      ? isDiluteName(words)
        ? CREAM_HEX
        : RED_HEX
      : solidBase(words);
    return finish(
      `linear-gradient(180deg, ${tipColor} 0 ${tip}%, ${SILVER_UNDERCOAT} ${fadeEnd}% 100%)`,
    );
  }

  // ソリッド (ポイントは finish の withPoint で一律に淡くなる)。
  return finish(solidBase(words));
}
