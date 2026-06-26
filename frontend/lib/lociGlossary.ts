// 遺伝子座の平易な解説 (UI のポップオーバー用)。ドメイン知識の固定リファレンスなので
// バックエンドには持たせず、型付きのフロント定数として保持する。
// キーは遺伝子情報 (opened_loci / closed_loci) で使う座位記号と一致させること。

export type LocusInfo = {
  symbol: string; // 表示記号 (例: "A")
  name: string; // 日本語名 (例: "アグーチ")
  inheritance: string; // 遺伝形式 (常染色体・優性 / 劣性 / X連鎖 など)
  description: string; // 1〜2文の平易な解説
};

export const LOCUS_GLOSSARY: Record<string, LocusInfo> = {
  A: {
    symbol: "A",
    name: "アグーチ（タビー柄）",
    inheritance: "常染色体・優性（タビーが優性）",
    description:
      "縞模様（タビー）を出す遺伝子。A があればタビー、a/a で無地（ソリッド）やトーティになる。",
  },
  B: {
    symbol: "B",
    name: "黒色系（ブラック）",
    inheritance: "常染色体・優性順位（B > b > bl）",
    description: "黒の系統を決める。B=黒、b=チョコレート、bl=シナモン。",
  },
  C: {
    symbol: "C",
    name: "発色（フルカラー/ポイント）",
    inheritance: "常染色体・劣性系列（C > cs/cb、cs・cb は不完全優性）",
    description:
      "色の出方。C=フルカラー、cs=ポイント（シャム）、cb=セピア（バーミーズ）。",
  },
  D: {
    symbol: "D",
    name: "希釈（濃淡）",
    inheritance: "常染色体・劣性（d/d で希釈）",
    description: "色の濃さ。D=濃色（黒/赤）、d/d で淡色（ブルー/クリーム）になる。",
  },
  I: {
    symbol: "I",
    name: "シルバー（インヒビター）",
    inheritance: "常染色体・優性",
    description:
      "毛の根元の色を抜く修飾遺伝子。あるとスモーク／シルバー系になる（色自体は作らない）。",
  },
  O: {
    symbol: "O",
    name: "オレンジ（赤・X連鎖）",
    inheritance: "X染色体連鎖（伴性）・♀ヘテロは共優性的にトーティ",
    description:
      "赤を出す遺伝子（X染色体上）。♂は O/Y で全身赤、♀は O/O で赤・O/o でトーティ。",
  },
  S: {
    symbol: "S",
    name: "白斑（ホワイト）",
    inheritance: "常染色体・優性（不完全優性）",
    description: "白いブチを出す。S/s でバイカラー、S/S でバン（白多め）。",
  },
  W: {
    symbol: "W",
    name: "優性白（ドミナントホワイト）",
    inheritance: "常染色体・優性（上位／エピスタシス）",
    description: "全身を白にする上位の遺伝子。他の色柄を覆い隠す。",
  },
  Mc: {
    symbol: "Mc",
    name: "マッカレル（縞の型）",
    inheritance: "常染色体・優性（クラシック mc が劣性）",
    description: "タビーの型。Mc=マッカレル（魚骨状の縞）、mc/mc でクラシック（渦巻き）。",
  },
  Ta: {
    symbol: "Ta",
    name: "ティックドタビー",
    inheritance: "常染色体・優性（他のタビー型に優先）",
    description:
      "アビシニアン等の地色のみのタビー。縞が出にくく、毛1本1本に縞が乗る。",
  },
  Sp: {
    symbol: "Sp",
    name: "スポテッド（斑点）",
    inheritance: "常染色体・優性（縞を分断する修飾因子）",
    description: "縞が途切れて斑点状になるタビーの型。",
  },
  Wb: {
    symbol: "Wb",
    name: "ワイドバンド",
    inheritance: "常染色体・優性（本シムでの扱い）",
    description:
      "毛の根元の明るい帯を広げる。シルバー(I)と組むとチンチラ／シェーデッド、シルバー無しではゴールデンになる要因。",
  },
};
