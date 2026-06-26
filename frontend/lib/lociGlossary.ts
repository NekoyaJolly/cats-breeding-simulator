// 遺伝子座の平易な解説 (UI のポップオーバー用)。ドメイン知識の固定リファレンスなので
// バックエンドには持たせず、型付きのフロント定数として保持する。
// キーは診断情報 (opened_loci / closed_loci) で使う座位記号と一致させること。

export type LocusInfo = {
  symbol: string; // 表示記号 (例: "A")
  name: string; // 日本語名 (例: "アグーチ")
  description: string; // 1〜2文の平易な解説
};

export const LOCUS_GLOSSARY: Record<string, LocusInfo> = {
  A: {
    symbol: "A",
    name: "アグーチ（タビー柄）",
    description:
      "縞模様（タビー）を出す遺伝子。A があればタビー、a/a で無地（ソリッド）やトーティになる。",
  },
  B: {
    symbol: "B",
    name: "黒色系（ブラック）",
    description: "黒の系統を決める。B=黒、b=チョコレート、bl=シナモン。",
  },
  C: {
    symbol: "C",
    name: "発色（フルカラー/ポイント）",
    description:
      "色の出方。C=フルカラー、cs=ポイント（シャム）、cb=セピア（バーミーズ）。",
  },
  D: {
    symbol: "D",
    name: "希釈（濃淡）",
    description: "色の濃さ。D=濃色（黒/赤）、d/d で淡色（ブルー/クリーム）になる。",
  },
  I: {
    symbol: "I",
    name: "シルバー（インヒビター）",
    description:
      "毛の根元の色を抜く修飾遺伝子。あるとスモーク／シルバー系になる（色自体は作らない）。",
  },
  O: {
    symbol: "O",
    name: "オレンジ（赤・X連鎖）",
    description:
      "赤を出す遺伝子（X染色体上）。♂は O/Y で全身赤、♀は O/O で赤・O/o でトーティ。",
  },
  S: {
    symbol: "S",
    name: "白斑（ホワイト）",
    description: "白いブチを出す。S/s でバイカラー、S/S でバン（白多め）。",
  },
  W: {
    symbol: "W",
    name: "優性白（ドミナントホワイト）",
    description: "全身を白にする上位の遺伝子。他の色柄を覆い隠す。",
  },
  Mc: {
    symbol: "Mc",
    name: "マッカレル（縞の型）",
    description: "タビーの型。Mc=マッカレル（魚骨状の縞）、mc/mc でクラシック（渦巻き）。",
  },
  Ta: {
    symbol: "Ta",
    name: "ティックドタビー",
    description:
      "アビシニアン等の地色のみのタビー。縞が出にくく、毛1本1本に縞が乗る。",
  },
  Sp: {
    symbol: "Sp",
    name: "スポテッド（斑点）",
    description: "縞が途切れて斑点状になるタビーの型。",
  },
  Wb: {
    symbol: "Wb",
    name: "ワイドバンド",
    description:
      "毛の根元の明るい帯を広げる。シルバー(I)と組むとチンチラ／シェーデッド、シルバー無しではゴールデンになる要因。",
  },
};
