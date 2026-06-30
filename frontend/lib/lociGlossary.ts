// 遺伝子座の平易な解説 (UI のポップオーバー用)。ドメイン知識の固定リファレンスなので
// バックエンドには持たせず、型付きのフロント定数として保持する。
// キーは遺伝子情報 (opened_loci / closed_loci) で使う座位記号と一致させること。

export type LocusInfo = {
  symbol: string; // 表示記号 (例: "A")
  name: string; // 日本語名 (例: "アグーチ")
  inheritance: string; // 遺伝形式 (常染色体・優性 / 劣性 / X連鎖 など)
  description: string; // 1〜2文の平易な解説
};

/**
 * UI 上で同じ遺伝子座を同じ色として認識するための Tailwind クラス群。
 */
export type LocusTone = {
  iconClass: string; // 座位アイコンの塗り・文字色
  chipClass: string; // 結果側の座位チップ
  selectedClass: string; // 入力側で選択された遺伝子型チップ
  textClass: string; // 補足説明テキスト
  tableCellClass: string; // 表内で座位を含むセルの薄い背景
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

export const DEFAULT_LOCUS_TONE: LocusTone = {
  iconClass: "bg-slate-100 text-slate-700 ring-1 ring-slate-200",
  chipClass:
    "border-slate-300 bg-slate-50 text-slate-700 hover:bg-slate-100",
  selectedClass: "bg-white text-slate-700 shadow-sm ring-1 ring-slate-200",
  textClass: "text-slate-600",
  tableCellClass: "bg-slate-50 text-slate-700",
};

const LOCUS_TONES: Record<string, LocusTone> = {
  A: {
    iconClass: "bg-emerald-50 text-emerald-800 ring-1 ring-emerald-200",
    chipClass:
      "border-emerald-300 bg-emerald-50 text-emerald-800 hover:bg-emerald-100",
    selectedClass: "bg-white text-emerald-700 shadow-sm ring-1 ring-emerald-200",
    textClass: "text-emerald-700",
    tableCellClass: "bg-emerald-50 text-emerald-800",
  },
  Mc: {
    iconClass: "bg-teal-50 text-teal-800 ring-1 ring-teal-200",
    chipClass: "border-teal-300 bg-teal-50 text-teal-800 hover:bg-teal-100",
    selectedClass: "bg-white text-teal-700 shadow-sm ring-1 ring-teal-200",
    textClass: "text-teal-700",
    tableCellClass: "bg-teal-50 text-teal-800",
  },
  Ta: {
    iconClass: "bg-cyan-50 text-cyan-800 ring-1 ring-cyan-200",
    chipClass: "border-cyan-300 bg-cyan-50 text-cyan-800 hover:bg-cyan-100",
    selectedClass: "bg-white text-cyan-700 shadow-sm ring-1 ring-cyan-200",
    textClass: "text-cyan-700",
    tableCellClass: "bg-cyan-50 text-cyan-800",
  },
  Sp: {
    iconClass: "bg-sky-50 text-sky-800 ring-1 ring-sky-200",
    chipClass: "border-sky-300 bg-sky-50 text-sky-800 hover:bg-sky-100",
    selectedClass: "bg-white text-sky-700 shadow-sm ring-1 ring-sky-200",
    textClass: "text-sky-700",
    tableCellClass: "bg-sky-50 text-sky-800",
  },
  B: {
    iconClass: "bg-violet-50 text-violet-800 ring-1 ring-violet-200",
    chipClass:
      "border-violet-300 bg-violet-50 text-violet-800 hover:bg-violet-100",
    selectedClass: "bg-white text-violet-700 shadow-sm ring-1 ring-violet-200",
    textClass: "text-violet-700",
    tableCellClass: "bg-violet-50 text-violet-800",
  },
  D: {
    iconClass: "bg-indigo-50 text-indigo-800 ring-1 ring-indigo-200",
    chipClass:
      "border-indigo-300 bg-indigo-50 text-indigo-800 hover:bg-indigo-100",
    selectedClass: "bg-white text-indigo-700 shadow-sm ring-1 ring-indigo-200",
    textClass: "text-indigo-700",
    tableCellClass: "bg-indigo-50 text-indigo-800",
  },
  C: {
    iconClass: "bg-blue-50 text-blue-800 ring-1 ring-blue-200",
    chipClass: "border-blue-300 bg-blue-50 text-blue-800 hover:bg-blue-100",
    selectedClass: "bg-white text-blue-700 shadow-sm ring-1 ring-blue-200",
    textClass: "text-blue-700",
    tableCellClass: "bg-blue-50 text-blue-800",
  },
  I: {
    iconClass: "bg-amber-50 text-amber-800 ring-1 ring-amber-200",
    chipClass:
      "border-amber-300 bg-amber-50 text-amber-800 hover:bg-amber-100",
    selectedClass: "bg-white text-amber-700 shadow-sm ring-1 ring-amber-200",
    textClass: "text-amber-700",
    tableCellClass: "bg-amber-50 text-amber-800",
  },
  Wb: {
    iconClass: "bg-yellow-50 text-yellow-800 ring-1 ring-yellow-200",
    chipClass:
      "border-yellow-300 bg-yellow-50 text-yellow-800 hover:bg-yellow-100",
    selectedClass: "bg-white text-yellow-700 shadow-sm ring-1 ring-yellow-200",
    textClass: "text-yellow-700",
    tableCellClass: "bg-yellow-50 text-yellow-800",
  },
  O: {
    iconClass: "bg-orange-50 text-orange-800 ring-1 ring-orange-200",
    chipClass:
      "border-orange-300 bg-orange-50 text-orange-800 hover:bg-orange-100",
    selectedClass: "bg-white text-orange-700 shadow-sm ring-1 ring-orange-200",
    textClass: "text-orange-700",
    tableCellClass: "bg-orange-50 text-orange-800",
  },
  S: {
    iconClass: "bg-cyan-50 text-cyan-800 ring-1 ring-cyan-200",
    chipClass: "border-cyan-300 bg-cyan-50 text-cyan-800 hover:bg-cyan-100",
    selectedClass: "bg-white text-cyan-700 shadow-sm ring-1 ring-cyan-200",
    textClass: "text-cyan-700",
    tableCellClass: "bg-cyan-50 text-cyan-800",
  },
  W: {
    iconClass: "bg-slate-50 text-slate-800 ring-1 ring-slate-200",
    chipClass:
      "border-slate-300 bg-slate-50 text-slate-800 hover:bg-slate-100",
    selectedClass: "bg-white text-slate-700 shadow-sm ring-1 ring-slate-200",
    textClass: "text-slate-700",
    tableCellClass: "bg-slate-50 text-slate-800",
  },
};

export function getLocusTone(locus: string): LocusTone {
  return LOCUS_TONES[locus] ?? DEFAULT_LOCUS_TONE;
}
