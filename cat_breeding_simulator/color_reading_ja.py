"""色名 (英語 canonical) からカタカナ読みを合成生成するレイヤ。

master CSV に日本語名カラムが存在しないため、色名を構成する単語トークンを
カタカナへ写像し連結することで読みを生成する。色名は限られた語彙 (62 トークン)
の合成で出来ているため、トークン辞書だけで全色をカバーできる。

意図的に外部 CSV ではなくインライン辞書とする: 直近で「データ CSV が Docker
イメージに同梱されず本番でのみ正規化が無効化」する事故 (Dockerfile 修正済) が
あったため、本モジュールは追加アセット無しで確実に同梱されるようにする。

責務は読みの生成のみ。遺伝計算・名前解決には関与しない。
未知トークンは英語のまま残す (英語キーワードでの突合は別途効くため安全側)。
"""

from __future__ import annotations

import re

# 単語トークン -> カタカナ読み。cat_color_master.csv の PrimaryName を構成する
# 全 62 トークンを網羅する。表記は一般的な毛色カタカナ呼称に寄せる。
_TOKEN_KATAKANA: dict[str, str] = {
    # ベース色
    "Black": "ブラック",
    "Blue": "ブルー",
    "Brown": "ブラウン",
    "Red": "レッド",
    "Cream": "クリーム",
    "Chocolate": "チョコレート",
    "Cinnamon": "シナモン",
    "Chestnut": "チェスナット",
    "Lilac": "ライラック",
    "Lavender": "ラベンダー",
    "Fawn": "フォーン",
    "Champagne": "シャンパン",
    "Platinum": "プラチナ",
    "Sable": "セーブル",
    "Sepia": "セピア",
    "Ebony": "エボニー",
    "Seal": "シール",
    "Mink": "ミンク",
    "Snow": "スノー",
    "Sorrel": "ソレル",
    "Tawny": "トーニー",
    "Bronze": "ブロンズ",
    "Gray": "グレー",
    "Flame": "フレーム",
    "Cameo": "カメオ",
    "Golden": "ゴールデン",
    "Ruddy": "ルディ",
    # パターン・修飾
    "Silver": "シルバー",
    "Smoke": "スモーク",
    "Shaded": "シェーデッド",
    "Shell": "シェル",
    "Chinchilla": "チンチラ",
    "Tabby": "タビー",
    "Mackerel": "マッカレル",
    "Spotted": "スポッテッド",
    "Ticked": "ティックド",
    "Classic": "クラシック",
    "Marbled": "マーブル",
    "Marble": "マーブル",
    "Patched": "パッチド",
    "Tortie": "トーティ",
    "Torbie": "トービー",
    "Tortoiseshell": "トーティシェル",
    "Calico": "キャリコ",
    "Lynx": "リンクス",
    "Point": "ポイント",
    "Mitted": "ミテッド",
    "Solid": "ソリッド",
    "White": "ホワイト",
    "Van": "バン",
    "Bi": "バイ",
    "Color": "カラー",
    "Mike": "ミケ",
    "Tri": "トライ",
    "Dilute": "ダイリュート",
    "Natural": "ナチュラル",
    "Agouti": "アグーチ",
    "Leopard": "レオパード",
    "Peke": "ピーク",
    "Face": "フェイス",
    # 略字 (T-White の T = Tabby)
    "T": "タビー",
}

# 括弧注記 (A.O.C) 等は読みから除外する。
_PAREN = re.compile(r"\([^)]*\)")
# 空白・ハイフン・スラッシュでトークン分割する。
_SPLIT = re.compile(r"[\s\-/]+")


def _tokens(name: str) -> list[str]:
    cleaned = _PAREN.sub("", name)
    return [token for token in _SPLIT.split(cleaned) if token]


def reading_ja(name: str) -> str:
    """英語の色名からカタカナ読みを合成して返す。

    例: "Brown Tabby" -> "ブラウンタビー"
        "Blue Patched Spotted Tabby" -> "ブルーパッチドスポッテッドタビー"
    未知トークンは原語のまま連結する (英語突合でカバーされるため害は無い)。
    """

    return "".join(_TOKEN_KATAKANA.get(token, token) for token in _tokens(name))
