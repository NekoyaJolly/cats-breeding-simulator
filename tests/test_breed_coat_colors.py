"""品種別 毛色計算検証テスト (dense×dilute / 黒系×赤系マトリクス)。

目的:
  猫種を指定したとき、その猫種で「出るべき毛色」が「正しい確率」で出るかを、
  濃色×淡色・黒系×赤系のクロスで品種ごとに検証する。UI で見える毛色表示が
  遺伝的に破綻していないことの回帰ネットにする。

方針:
  - 猫種は cat_breed_genetic_map.csv で固定座位が定義された種を対象とする。
  - 遺伝的に同一な品種バリアント (例: American Curl SH/LH、Selkirk Rex 各種) は
    代表 1 つにまとめる (座位が同一なら結果も同一のため)。
  - 期待値は「遺伝的に手検証した正解」を明記する (現行出力のスナップショットではない)。
    期待が変わるのは仕様変更時のみで、そのときは理由を添えて更新する。

各エントリ: (sire_color, dam_color, {(sex, color): probability_pct, ...})
  probability_pct は小数第3位まで一致を要求する。合計は 100% (未分類ゼロ) を必須とする。
"""

from __future__ import annotations

import pytest

from cat_breeding_simulator.engine import CoatColorCalculator

# ---------------------------------------------------------------------------
# Abyssinian (固定: A/A C/C w/w s/s Ta/Ta。ティックドタビー単一パターン)
#   黒系: Ruddy(濃色 B/B D/D) / Blue(淡色 B/B d/d)
#   赤系(シナモン): Red=Sorrel(濃色 bl/bl D/D) / Fawn(淡色 bl/bl d/d)
#   ※ Abyssinian の「Red」は伴性オレンジではなくシナモン (Sorrel)。表示名は品種呼称。
#   ※ D 座位は品種未固定のため濃色親は D/- 展開され、濃色×濃色でも希釈が 6.25% 出る
#      (両親が希釈キャリアの場合)。これは遺伝的に正しい。
#   ※ B 座位は normal で非展開 (キャリア閉鎖)。B/B × bl/bl → B/bl は黒発現 = Ruddy 系。
# ---------------------------------------------------------------------------
_ABYSSINIAN_CROSSES = [
    # 黒系 × 黒系
    ("Ruddy", "Ruddy", {
        ("Male", "Ruddy"): 46.875, ("Female", "Ruddy"): 46.875,
        ("Male", "Blue"): 3.125, ("Female", "Blue"): 3.125,
    }),
    ("Ruddy", "Blue", {
        ("Male", "Ruddy"): 37.5, ("Female", "Ruddy"): 37.5,
        ("Male", "Blue"): 12.5, ("Female", "Blue"): 12.5,
    }),
    # 淡色 × 淡色: d/d × d/d は不可逆で濃色が出ない → Blue 100%
    ("Blue", "Blue", {
        ("Male", "Blue"): 50.0, ("Female", "Blue"): 50.0,
    }),
    # 黒系 × 赤系(シナモン): B/B × bl/bl → 全 B/bl は黒発現 = Ruddy (シナモンは出ない)
    ("Ruddy", "Cinnamon", {
        ("Male", "Ruddy"): 46.875, ("Female", "Ruddy"): 46.875,
        ("Male", "Blue"): 3.125, ("Female", "Blue"): 3.125,
    }),
    ("Ruddy", "Fawn", {
        ("Male", "Ruddy"): 37.5, ("Female", "Ruddy"): 37.5,
        ("Male", "Blue"): 12.5, ("Female", "Blue"): 12.5,
    }),
    # 赤系 × 赤系: bl/bl × bl/bl → シナモン系 (Red=Sorrel / Fawn)
    ("Cinnamon", "Cinnamon", {
        ("Male", "Red"): 46.875, ("Female", "Red"): 46.875,
        ("Male", "Fawn"): 3.125, ("Female", "Fawn"): 3.125,
    }),
    ("Cinnamon", "Fawn", {
        ("Male", "Red"): 37.5, ("Female", "Red"): 37.5,
        ("Male", "Fawn"): 12.5, ("Female", "Fawn"): 12.5,
    }),
    ("Fawn", "Fawn", {
        ("Male", "Fawn"): 50.0, ("Female", "Fawn"): 50.0,
    }),
    # 淡黒 × 赤系: B/B(d/d) × bl/bl → B/bl 黒発現。D は Cinnamon 側 D/- 展開で 25% 希釈
    ("Blue", "Cinnamon", {
        ("Male", "Ruddy"): 37.5, ("Female", "Ruddy"): 37.5,
        ("Male", "Blue"): 12.5, ("Female", "Blue"): 12.5,
    }),
    # 淡黒 × 淡赤: 双方 d/d → 全 Blue (B/bl 黒発現・希釈固定)
    ("Blue", "Fawn", {
        ("Male", "Blue"): 50.0, ("Female", "Blue"): 50.0,
    }),
]

# ---------------------------------------------------------------------------
# Burmese (固定: a/a cb/cb w/w s/s。セピアソリッド。アウトクロス品種なし)
#   確定パレット (Neko): Sable Brown(黒濃) / Champagne(チョコ濃) / Blue(黒淡) / Platinum(チョコ淡) + AOC。
#   ※ B/D は品種未固定。B は normal で非展開 (B/b は黒発現=Sable Brown)、D は D/- 展開。
#   ※ a/a ソリッドのためセピアはソリッド表示に落ち、未分類にならない。
#   ※ 入力 "Blue"→Blue Solid 遺伝子型、出力表示は Burmese 呼称 (Sable Brown/Blue)。
# ---------------------------------------------------------------------------
_BURMESE_CROSSES = [
    ("Sable Brown", "Sable Brown", {
        ("Male", "Sable Brown"): 46.875, ("Female", "Sable Brown"): 46.875,
        ("Male", "Blue"): 3.125, ("Female", "Blue"): 3.125,
    }),
    # 黒系 × 淡黒: D/- × d/d → 25% 希釈
    ("Sable Brown", "Blue", {
        ("Male", "Sable Brown"): 37.5, ("Female", "Sable Brown"): 37.5,
        ("Male", "Blue"): 12.5, ("Female", "Blue"): 12.5,
    }),
    ("Blue", "Blue", {
        ("Male", "Blue"): 50.0, ("Female", "Blue"): 50.0,
    }),
    # 黒系 × チョコ系: B/B × b/b → 全 B/b は黒発現 = Sable Brown (Champagne は出ない)
    ("Sable Brown", "Champagne", {
        ("Male", "Sable Brown"): 46.875, ("Female", "Sable Brown"): 46.875,
        ("Male", "Blue"): 3.125, ("Female", "Blue"): 3.125,
    }),
    ("Champagne", "Champagne", {
        ("Male", "Champagne"): 46.875, ("Female", "Champagne"): 46.875,
        ("Male", "Platinum"): 3.125, ("Female", "Platinum"): 3.125,
    }),
    ("Champagne", "Platinum", {
        ("Male", "Champagne"): 37.5, ("Female", "Champagne"): 37.5,
        ("Male", "Platinum"): 12.5, ("Female", "Platinum"): 12.5,
    }),
    ("Platinum", "Platinum", {
        ("Male", "Platinum"): 50.0, ("Female", "Platinum"): 50.0,
    }),
    ("Sable Brown", "Platinum", {
        ("Male", "Sable Brown"): 37.5, ("Female", "Sable Brown"): 37.5,
        ("Male", "Blue"): 12.5, ("Female", "Blue"): 12.5,
    }),
]

# ---------------------------------------------------------------------------
# European Burmese (固定: a/a cb/cb w/w s/s。Burmese と遺伝同一・別呼称)
#   確定パレット (Neko): Brown(黒濃) / Blue(黒淡) / Chocolate(チョコ濃) / Lilac(チョコ淡) /
#     Red / Cream / Brown・Blue・Chocolate・Lilac Tortie。
#   入出力とも EB 呼称。内部セピア遺伝子型は Burmese と共有 (Sable/Champagne/Platinum/Blue Solid)。
#   Red/Cream/Tortie は EB 固有の新規セピアオレンジ色 (内部 "… Sepia" 名) を割当。
#   ※ 純オレンジ (Red/Cream) は赤色素が B 座位をマスクするため base 差なし (expressed_key で
#     orange を base 非依存化)。トーティは黒/チョコ斑が可視のため Brown/Chocolate Tortie を区別。
# ---------------------------------------------------------------------------
_EUROPEAN_BURMESE_CROSSES = [
    ("Brown", "Brown", {
        ("Male", "Brown"): 46.875, ("Female", "Brown"): 46.875,
        ("Male", "Blue"): 3.125, ("Female", "Blue"): 3.125,
    }),
    ("Brown", "Blue", {
        ("Male", "Brown"): 37.5, ("Female", "Brown"): 37.5,
        ("Male", "Blue"): 12.5, ("Female", "Blue"): 12.5,
    }),
    ("Blue", "Blue", {
        ("Male", "Blue"): 50.0, ("Female", "Blue"): 50.0,
    }),
    # 黒系 × チョコ系: B/B × b/b → 全 B/b 黒発現 = Brown
    ("Brown", "Chocolate", {
        ("Male", "Brown"): 46.875, ("Female", "Brown"): 46.875,
        ("Male", "Blue"): 3.125, ("Female", "Blue"): 3.125,
    }),
    ("Chocolate", "Chocolate", {
        ("Male", "Chocolate"): 46.875, ("Female", "Chocolate"): 46.875,
        ("Male", "Lilac"): 3.125, ("Female", "Lilac"): 3.125,
    }),
    ("Chocolate", "Lilac", {
        ("Male", "Chocolate"): 37.5, ("Female", "Chocolate"): 37.5,
        ("Male", "Lilac"): 12.5, ("Female", "Lilac"): 12.5,
    }),
    ("Lilac", "Lilac", {
        ("Male", "Lilac"): 50.0, ("Female", "Lilac"): 50.0,
    }),
    # 赤系 (伴性オレンジ): Red / Cream。Red×Red → Red + 希釈 Cream。
    ("Red", "Red", {
        ("Female", "Red"): 46.875, ("Male", "Red"): 46.875,
        ("Female", "Cream"): 3.125, ("Male", "Cream"): 3.125,
    }),
    ("Cream", "Cream", {
        ("Female", "Cream"): 50.0, ("Male", "Cream"): 50.0,
    }),
    # 黒系♂ × 赤♀: 息子 Red・娘 Brown Tortie。希釈で Cream / Blue Tortie。
    ("Brown", "Red", {
        ("Female", "Brown Tortie"): 46.875, ("Male", "Red"): 46.875,
        ("Female", "Blue Tortie"): 3.125, ("Male", "Cream"): 3.125,
    }),
    # チョコ系♂ × 赤♀: 息子は B/b で黒ベース赤 = Red、娘 Brown Tortie (B/b は黒斑)。
    ("Chocolate", "Red", {
        ("Female", "Brown Tortie"): 46.875, ("Male", "Red"): 46.875,
        ("Female", "Blue Tortie"): 3.125, ("Male", "Cream"): 3.125,
    }),
    # 黒系♂ × 黒トーティ♀: 息子 Brown/Red・娘 Brown/Brown Tortie。希釈で Blue 系。
    ("Brown", "Brown Tortie", {
        ("Female", "Brown"): 23.438, ("Male", "Brown"): 23.438,
        ("Female", "Brown Tortie"): 23.438, ("Male", "Red"): 23.438,
        ("Female", "Blue"): 1.562, ("Male", "Blue"): 1.562,
        ("Female", "Blue Tortie"): 1.562, ("Male", "Cream"): 1.562,
    }),
    # チョコ系♂ × チョコトーティ♀: Chocolate/Chocolate Tortie/Red + 希釈 Lilac 系。
    ("Chocolate", "Chocolate Tortie", {
        ("Female", "Chocolate"): 23.438, ("Male", "Chocolate"): 23.438,
        ("Female", "Chocolate Tortie"): 23.438, ("Male", "Red"): 23.438,
        ("Female", "Lilac"): 1.562, ("Male", "Lilac"): 1.562,
        ("Female", "Lilac Tortie"): 1.562, ("Male", "Cream"): 1.562,
    }),
    # 淡チョコ系♂ × 淡チョコトーティ♀: 全希釈 → Lilac/Lilac Tortie/Cream。
    ("Lilac", "Lilac Tortie", {
        ("Female", "Lilac"): 25.0, ("Male", "Lilac"): 25.0,
        ("Female", "Lilac Tortie"): 25.0, ("Male", "Cream"): 25.0,
    }),
]

# ---------------------------------------------------------------------------
# Havana Brown (固定: b/b D/D a/a C/C w/w s/s。チョコレート単色)
#   チョコ単色。D/D 固定のためライラック希釈は出ず Chocolate 100%。Black/Lilac は認定外。
# ---------------------------------------------------------------------------
_HAVANA_BROWN_CROSSES = [
    ("Chocolate", "Chocolate", {
        ("Male", "Chocolate"): 50.0, ("Female", "Chocolate"): 50.0,
    }),
]

# ---------------------------------------------------------------------------
# Toyger (固定: B/B o/o D/D A/A C/C w/w s/s Mc/Mc ta/ta sp/sp i/i wb/wb。ブラウンマッカレルタビー単一)
#   Brown Mackerel Tabby のみ。Mc/Mc 固定でクラシック (無記名タビー=mc/mc) を除外、
#   ta/ta sp/sp でティックド/スポテッド除外、o/o で赤除外、i/i wb/wb で銀/ゴールデン除外、
#   D/D でブルー除外。Brown Mackerel Tabby × 同色 → 100%。
# ---------------------------------------------------------------------------
_TOYGER_CROSSES = [
    ("Brown Mackerel Tabby", "Brown Mackerel Tabby", {
        ("Male", "Brown Mackerel Tabby"): 50.0, ("Female", "Brown Mackerel Tabby"): 50.0,
    }),
]

# ---------------------------------------------------------------------------
# Pixiebob (固定: B/B o/o D/D A/A C/C w/w s/s ta/ta Sp/Sp i/i wb/wb。ブラウンスポテッドタビー単一)
#   Brown Spotted Tabby のみ。Sp/Sp でスポテッド固定、o/o で非赤、i/i wb/wb で非銀/非ゴールデン、
#   D/D でブルー不可、ta/ta で非ティックド。同色クロス → 100%。
# ---------------------------------------------------------------------------
_PIXIEBOB_CROSSES = [
    ("Brown Spotted Tabby", "Brown Spotted Tabby", {
        ("Male", "Brown Spotted Tabby"): 50.0, ("Female", "Brown Spotted Tabby"): 50.0,
    }),
]

# ---------------------------------------------------------------------------
# Bombay (固定: B/B o/o D/D a/a C/C w/w s/s i/i wb/wb。黒ソリッド単色)
#   黒ソリッドのみ。D/D 固定でブルー不可、o/o/i/i/wb/wb で赤/銀/ゴールデン除外。
#   Black × Black → Black 100%。
# ---------------------------------------------------------------------------
_BOMBAY_CROSSES = [
    ("Black", "Black", {
        ("Male", "Black"): 50.0, ("Female", "Black"): 50.0,
    }),
]

# ---------------------------------------------------------------------------
# 全座位固定の単色ブルー品種 (B/B d/d a/a C/C w/w s/s)。Blue のみ、Blue×Blue→Blue 100%。
# Chartreux / Korat / Russian Blue は遺伝が同一なのでクロス表を共有する。
# ---------------------------------------------------------------------------
_SOLID_BLUE_CROSSES = [
    ("Blue", "Blue", {
        ("Male", "Blue"): 50.0, ("Female", "Blue"): 50.0,
    }),
]

# ---------------------------------------------------------------------------
# 単色品種 (Neko 認定カラー登録):
#   Lykoi = Black only (B/B D/D a/a C/C w/w s/s。黒ソリッド)
#   Nebelung = Blue only (B/B d/d a/a C/C w/w s/s。青ソリッド。Russian Blue と同一遺伝)
#   Khao Manee = White only (W/W。優性白。有色は下不明のため AOC に集約)
#   ※ 単色品種は O/I/Wb 未固定のため認定色リストに Red/Silver 等が混じる (Bombay/Russian Blue と
#     同じ既存仕様)。主要クロスの計算は正しい。
# ---------------------------------------------------------------------------
_LYKOI_CROSSES = [
    ("Black", "Black", {("Male", "Black"): 50.0, ("Female", "Black"): 50.0}),
]
_NEBELUNG_CROSSES = [
    ("Blue", "Blue", {("Male", "Blue"): 50.0, ("Female", "Blue"): 50.0}),
]
_KHAO_MANEE_CROSSES = [
    # 優性白 W/w 仮定。白 75% (M/F 各 37.5%)、有色 25% は下不明で AOC に集約。
    ("White", "White", {
        ("Male", "White"): 37.5, ("Female", "White"): 37.5,
        ("Male", "AOC"): 12.5, ("Female", "AOC"): 12.5,
    }),
]

# ---------------------------------------------------------------------------
# Australian Mist (固定: A/A cb/cb w/w s/s。セピアアグーチタビー。パターンは Spotted/Marbled 両方認定)
#   黒系: Seal Sepia Tabby(濃) / Blue Sepia Tabby(淡)。チョコ系: Chocolate / Lilac Sepia Tabby。
#   セピアアグーチのため未分類にならない (Sepia Agouti/Singapura と同一遺伝子型・別呼称)。
# ---------------------------------------------------------------------------
_AUSTRALIAN_MIST_CROSSES = [
    ("Seal Sepia Tabby", "Seal Sepia Tabby", {
        ("Male", "Seal Sepia Tabby"): 46.875, ("Female", "Seal Sepia Tabby"): 46.875,
        ("Male", "Blue Sepia Tabby"): 3.125, ("Female", "Blue Sepia Tabby"): 3.125,
    }),
    ("Seal Sepia Tabby", "Blue Sepia Tabby", {
        ("Male", "Seal Sepia Tabby"): 37.5, ("Female", "Seal Sepia Tabby"): 37.5,
        ("Male", "Blue Sepia Tabby"): 12.5, ("Female", "Blue Sepia Tabby"): 12.5,
    }),
    ("Blue Sepia Tabby", "Blue Sepia Tabby", {
        ("Male", "Blue Sepia Tabby"): 50.0, ("Female", "Blue Sepia Tabby"): 50.0,
    }),
    # 黒系 × チョコ系: B/B × b/b → B/b 黒発現 = Seal (Chocolate は出ない)
    ("Seal Sepia Tabby", "Chocolate Sepia Tabby", {
        ("Male", "Seal Sepia Tabby"): 46.875, ("Female", "Seal Sepia Tabby"): 46.875,
        ("Male", "Blue Sepia Tabby"): 3.125, ("Female", "Blue Sepia Tabby"): 3.125,
    }),
    ("Chocolate Sepia Tabby", "Chocolate Sepia Tabby", {
        ("Male", "Chocolate Sepia Tabby"): 46.875, ("Female", "Chocolate Sepia Tabby"): 46.875,
        ("Male", "Lilac Sepia Tabby"): 3.125, ("Female", "Lilac Sepia Tabby"): 3.125,
    }),
    ("Chocolate Sepia Tabby", "Lilac Sepia Tabby", {
        ("Male", "Chocolate Sepia Tabby"): 37.5, ("Female", "Chocolate Sepia Tabby"): 37.5,
        ("Male", "Lilac Sepia Tabby"): 12.5, ("Female", "Lilac Sepia Tabby"): 12.5,
    }),
    ("Lilac Sepia Tabby", "Lilac Sepia Tabby", {
        ("Male", "Lilac Sepia Tabby"): 50.0, ("Female", "Lilac Sepia Tabby"): 50.0,
    }),
]

# ---------------------------------------------------------------------------
# Singapura (固定: D/D A/A cb/cb w/w s/s Ta/Ta。セピアアグーティ単色)
#   Sepia Agouti 単色。D/D 固定のため希釈は出ず Sepia Agouti 100%。
# ---------------------------------------------------------------------------
_SINGAPURA_CROSSES = [
    ("Sepia Agouti", "Sepia Agouti", {
        ("Male", "Sepia Agouti"): 50.0, ("Female", "Sepia Agouti"): 50.0,
    }),
]

# ---------------------------------------------------------------------------
# ポイント系品種 (固定: C=cs/cs。Siamese/Balinese/Colorpoint Shorthair は w/w s/s も固定)
#   黒系: Seal Point(濃色) / Blue Point(淡色)
#   チョコ系: Chocolate Point(濃色) / Lilac Point(淡色)
#   赤系(伴性オレンジ): Red Point / Cream Point(淡色)、♀×♂で Tortie Point が出る
#   ※ ポイントは体色が抑制されるが、遺伝子型(B/D/O)は通常どおり分離する。
#   ※ Red は伴性 O。Seal♂ × Red♀ → 息子 Red・娘 Seal Tortie (X 連鎖の帰結)。
# ---------------------------------------------------------------------------
_POINT_CROSSES = [
    # 黒系 × 黒系
    ("Seal Point", "Seal Point", {
        ("Male", "Seal Point"): 46.875, ("Female", "Seal Point"): 46.875,
        ("Male", "Blue Point"): 3.125, ("Female", "Blue Point"): 3.125,
    }),
    ("Seal Point", "Blue Point", {
        ("Male", "Seal Point"): 37.5, ("Female", "Seal Point"): 37.5,
        ("Male", "Blue Point"): 12.5, ("Female", "Blue Point"): 12.5,
    }),
    ("Blue Point", "Blue Point", {
        ("Male", "Blue Point"): 50.0, ("Female", "Blue Point"): 50.0,
    }),
    # 黒系 × チョコ系: B/B × b/b → B/b は黒発現 = Seal (Chocolate は出ない)
    ("Seal Point", "Chocolate Point", {
        ("Male", "Seal Point"): 46.875, ("Female", "Seal Point"): 46.875,
        ("Male", "Blue Point"): 3.125, ("Female", "Blue Point"): 3.125,
    }),
    ("Chocolate Point", "Chocolate Point", {
        ("Male", "Chocolate Point"): 46.875, ("Female", "Chocolate Point"): 46.875,
        ("Male", "Lilac Point"): 3.125, ("Female", "Lilac Point"): 3.125,
    }),
    ("Chocolate Point", "Lilac Point", {
        ("Male", "Chocolate Point"): 37.5, ("Female", "Chocolate Point"): 37.5,
        ("Male", "Lilac Point"): 12.5, ("Female", "Lilac Point"): 12.5,
    }),
    ("Lilac Point", "Lilac Point", {
        ("Male", "Lilac Point"): 50.0, ("Female", "Lilac Point"): 50.0,
    }),
    ("Seal Point", "Lilac Point", {
        ("Male", "Seal Point"): 37.5, ("Female", "Seal Point"): 37.5,
        ("Male", "Blue Point"): 12.5, ("Female", "Blue Point"): 12.5,
    }),
    # 黒系 × 赤系(伴性): Seal♂ × Red♀ → 息子 Red・娘 Seal Tortie。希釈 6.25% で Cream/Blue Cream
    ("Seal Point", "Red Point", {
        ("Male", "Red Point"): 46.875, ("Female", "Seal Tortie Point"): 46.875,
        ("Male", "Cream Point"): 3.125, ("Female", "Blue Cream Point"): 3.125,
    }),
    # 赤系 × 赤系: 全 Red (♂♀とも)、希釈で Cream
    ("Red Point", "Red Point", {
        ("Male", "Red Point"): 46.875, ("Female", "Red Point"): 46.875,
        ("Male", "Cream Point"): 3.125, ("Female", "Cream Point"): 3.125,
    }),
    # 淡黒 × 赤系: Blue♂(d/d) × Red♀(D/-)。息子 Red/Cream・娘 Seal Tortie/Blue Cream
    ("Blue Point", "Red Point", {
        ("Male", "Red Point"): 37.5, ("Female", "Seal Tortie Point"): 37.5,
        ("Male", "Cream Point"): 12.5, ("Female", "Blue Cream Point"): 12.5,
    }),
]

# ---------------------------------------------------------------------------
# スポテッドタビー品種 (固定: A/A Sp/Sp。Egyptian Mau / Ocicat)
#   黒系: Brown Spotted(濃色) / Blue Spotted(淡色)
#   チョコ系: Chocolate Spotted(濃色) / Lilac Spotted(淡色。入力別名 Lavender)
#   赤系(伴性): Red Spotted。黒系♂ × Red♀ → 息子 Red Spotted・娘 Brown Patched Spotted。
#   Silver(I/-): Silver Spotted。
#   ※ スポテッド品種は Sp/Sp 固定のため、トーティ(Patched)やシルバー希釈の子も必ず
#      "Spotted" が付く (simplify_patterns の is_spotted_breed 補完)。
# ---------------------------------------------------------------------------
_SPOTTED_CROSSES = [
    ("Brown Spotted Tabby", "Brown Spotted Tabby", {
        ("Female", "Brown Spotted Tabby"): 46.875, ("Male", "Brown Spotted Tabby"): 46.875,
        ("Female", "Blue Spotted Tabby"): 3.125, ("Male", "Blue Spotted Tabby"): 3.125,
    }),
    ("Brown Spotted Tabby", "Blue Spotted Tabby", {
        ("Female", "Brown Spotted Tabby"): 37.5, ("Male", "Brown Spotted Tabby"): 37.5,
        ("Female", "Blue Spotted Tabby"): 12.5, ("Male", "Blue Spotted Tabby"): 12.5,
    }),
    ("Blue Spotted Tabby", "Blue Spotted Tabby", {
        ("Female", "Blue Spotted Tabby"): 50.0, ("Male", "Blue Spotted Tabby"): 50.0,
    }),
    # 黒系 × チョコ系: B/B × b/b → B/b 黒発現 = Brown (Chocolate は出ない)
    ("Brown Spotted Tabby", "Chocolate Spotted Tabby", {
        ("Female", "Brown Spotted Tabby"): 46.875, ("Male", "Brown Spotted Tabby"): 46.875,
        ("Female", "Blue Spotted Tabby"): 3.125, ("Male", "Blue Spotted Tabby"): 3.125,
    }),
    ("Chocolate Spotted Tabby", "Chocolate Spotted Tabby", {
        ("Female", "Chocolate Spotted Tabby"): 46.875, ("Male", "Chocolate Spotted Tabby"): 46.875,
        ("Female", "Lilac Spotted Tabby"): 3.125, ("Male", "Lilac Spotted Tabby"): 3.125,
    }),
    ("Chocolate Spotted Tabby", "Lavender Spotted Tabby", {
        ("Female", "Chocolate Spotted Tabby"): 37.5, ("Male", "Chocolate Spotted Tabby"): 37.5,
        ("Female", "Lilac Spotted Tabby"): 12.5, ("Male", "Lilac Spotted Tabby"): 12.5,
    }),
    ("Lavender Spotted Tabby", "Lavender Spotted Tabby", {
        ("Female", "Lilac Spotted Tabby"): 50.0, ("Male", "Lilac Spotted Tabby"): 50.0,
    }),
    # 黒系♂ × 赤系♀(伴性): 息子 Red Spotted・娘 Brown Patched Spotted。希釈で Cream/Blue Patched
    ("Brown Spotted Tabby", "Red Spotted Tabby", {
        ("Female", "Brown Patched Spotted Tabby"): 46.875, ("Male", "Red Spotted Tabby"): 46.875,
        ("Female", "Blue Patched Spotted Tabby"): 3.125, ("Male", "Cream Spotted Tabby"): 3.125,
    }),
    ("Red Spotted Tabby", "Red Spotted Tabby", {
        ("Female", "Red Spotted Tabby"): 46.875, ("Male", "Red Spotted Tabby"): 46.875,
        ("Female", "Cream Spotted Tabby"): 3.125, ("Male", "Cream Spotted Tabby"): 3.125,
    }),
    # Silver(I/-): カテゴリA展開のため非シルバー(i/i)は 6.25%。全個体スポテッド保持。
    ("Silver Spotted Tabby", "Silver Spotted Tabby", {
        ("Female", "Silver Spotted Tabby"): 43.945, ("Male", "Silver Spotted Tabby"): 43.945,
        ("Female", "Blue Silver Spotted Tabby"): 2.93, ("Male", "Blue Silver Spotted Tabby"): 2.93,
        ("Female", "Brown Spotted Tabby"): 2.93, ("Male", "Brown Spotted Tabby"): 2.93,
        ("Female", "Blue Spotted Tabby"): 0.195, ("Male", "Blue Spotted Tabby"): 0.195,
    }),
    ("Silver Spotted Tabby", "Brown Spotted Tabby", {
        ("Female", "Silver Spotted Tabby"): 35.156, ("Male", "Silver Spotted Tabby"): 35.156,
        ("Female", "Brown Spotted Tabby"): 11.719, ("Male", "Brown Spotted Tabby"): 11.719,
        ("Female", "Blue Silver Spotted Tabby"): 2.344, ("Male", "Blue Silver Spotted Tabby"): 2.344,
        ("Female", "Blue Spotted Tabby"): 0.781, ("Male", "Blue Spotted Tabby"): 0.781,
    }),
]

# ---------------------------------------------------------------------------
# Tonkinese (ミンク class: C=cb/cs)。Mink×Mink は 1:2:1 で Sepia(Solid)/Mink/Point に分離する。
#   Natural(黒系) / Champagne(濃チョコ) / Blue(淡黒) / Platinum(淡チョコ)。cb/cs のヘテロがミンクの本質。
#   ※ Champagne 系の希釈ポイントは Tonkinese 固有呼称 "Platinum Point" で出す (find_matching_color
#      の breed_specific_rank で一般 "Lilac Point" とのタイを固有呼称優先で解消)。
# ---------------------------------------------------------------------------
_TONKINESE_CROSSES = [
    # Mink×Mink → Mink 50% / Point 25% / Solid(Sepia) 25% + 希釈 6.25%
    ("Natural Mink", "Natural Mink", {
        ("Female", "Natural Mink"): 23.438, ("Male", "Natural Mink"): 23.438,
        ("Female", "Natural Point"): 11.719, ("Male", "Natural Point"): 11.719,
        ("Female", "Natural Solid"): 11.719, ("Male", "Natural Solid"): 11.719,
        ("Female", "Blue Mink"): 1.562, ("Male", "Blue Mink"): 1.562,
        ("Female", "Blue Point"): 0.781, ("Male", "Blue Point"): 0.781,
        ("Female", "Blue Solid"): 0.781, ("Male", "Blue Solid"): 0.781,
    }),
    ("Natural Mink", "Blue Mink", {
        ("Female", "Natural Mink"): 18.75, ("Male", "Natural Mink"): 18.75,
        ("Female", "Natural Point"): 9.375, ("Male", "Natural Point"): 9.375,
        ("Female", "Natural Solid"): 9.375, ("Male", "Natural Solid"): 9.375,
        ("Female", "Blue Mink"): 6.25, ("Male", "Blue Mink"): 6.25,
        ("Female", "Blue Point"): 3.125, ("Male", "Blue Point"): 3.125,
        ("Female", "Blue Solid"): 3.125, ("Male", "Blue Solid"): 3.125,
    }),
    # 淡黒 × 淡黒: 全 Blue。Mink 50% / Point 25% / Solid 25%
    ("Blue Mink", "Blue Mink", {
        ("Female", "Blue Mink"): 25.0, ("Male", "Blue Mink"): 25.0,
        ("Female", "Blue Point"): 12.5, ("Male", "Blue Point"): 12.5,
        ("Female", "Blue Solid"): 12.5, ("Male", "Blue Solid"): 12.5,
    }),
    ("Platinum Mink", "Platinum Mink", {
        ("Female", "Platinum Mink"): 25.0, ("Male", "Platinum Mink"): 25.0,
        ("Female", "Platinum Point"): 12.5, ("Male", "Platinum Point"): 12.5,
        ("Female", "Platinum Solid"): 12.5, ("Male", "Platinum Solid"): 12.5,
    }),
    # チョコ系ミンク: Champagne(濃) / Platinum(淡)。希釈ポイントは Platinum Point で出る。
    ("Champagne Mink", "Champagne Mink", {
        ("Female", "Champagne Mink"): 23.438, ("Male", "Champagne Mink"): 23.438,
        ("Female", "Champagne Point"): 11.719, ("Male", "Champagne Point"): 11.719,
        ("Female", "Champagne Solid"): 11.719, ("Male", "Champagne Solid"): 11.719,
        ("Female", "Platinum Mink"): 1.562, ("Male", "Platinum Mink"): 1.562,
        ("Female", "Platinum Point"): 0.781, ("Male", "Platinum Point"): 0.781,
        ("Female", "Platinum Solid"): 0.781, ("Male", "Platinum Solid"): 0.781,
    }),
    ("Champagne Mink", "Platinum Mink", {
        ("Female", "Champagne Mink"): 18.75, ("Male", "Champagne Mink"): 18.75,
        ("Female", "Champagne Point"): 9.375, ("Male", "Champagne Point"): 9.375,
        ("Female", "Champagne Solid"): 9.375, ("Male", "Champagne Solid"): 9.375,
        ("Female", "Platinum Mink"): 6.25, ("Male", "Platinum Mink"): 6.25,
        ("Female", "Platinum Point"): 3.125, ("Male", "Platinum Point"): 3.125,
        ("Female", "Platinum Solid"): 3.125, ("Male", "Platinum Solid"): 3.125,
    }),
    # 黒系 × チョコ系: B/B × b/b → B/b 黒発現 = 全 Natural (Champagne は出ない)
    ("Natural Mink", "Champagne Mink", {
        ("Female", "Natural Mink"): 23.438, ("Male", "Natural Mink"): 23.438,
        ("Female", "Natural Point"): 11.719, ("Male", "Natural Point"): 11.719,
        ("Female", "Natural Solid"): 11.719, ("Male", "Natural Solid"): 11.719,
        ("Female", "Blue Mink"): 1.562, ("Male", "Blue Mink"): 1.562,
        ("Female", "Blue Point"): 0.781, ("Male", "Blue Point"): 0.781,
        ("Female", "Blue Solid"): 0.781, ("Male", "Blue Solid"): 0.781,
    }),
]

# ---------------------------------------------------------------------------
# ポイント+白斑 (Ragdoll / Snowshoe)。Mitted / Bi-Color は S 座位のヘテロ (S/s) で、
# S/s × S/s → Mitted or Bi-Color(S/s) 50% / Point(s/s, 白斑なし) 25% / Point-White(S/S) 25%
# の 1:2:1 に分離する (不完全優性 S)。Snowshoe は Ragdoll と同一グループ (色柄遺伝が同一)。
# ---------------------------------------------------------------------------
_POINT_WHITE_CROSSES = [
    ("Seal Point Mitted", "Seal Point Mitted", {
        ("Female", "Seal Point Mitted"): 23.438, ("Male", "Seal Point Mitted"): 23.438,
        ("Female", "Seal Point"): 11.719, ("Male", "Seal Point"): 11.719,
        ("Female", "Seal Point-White"): 11.719, ("Male", "Seal Point-White"): 11.719,
        ("Female", "Blue Point Mitted"): 1.562, ("Male", "Blue Point Mitted"): 1.562,
        ("Female", "Blue Point"): 0.781, ("Male", "Blue Point"): 0.781,
        ("Female", "Blue Point-White"): 0.781, ("Male", "Blue Point-White"): 0.781,
    }),
    ("Seal Point Bi-Color", "Seal Point Bi-Color", {
        ("Female", "Seal Point Bi-Color"): 23.438, ("Male", "Seal Point Bi-Color"): 23.438,
        ("Female", "Seal Point"): 11.719, ("Male", "Seal Point"): 11.719,
        ("Female", "Seal Point-White"): 11.719, ("Male", "Seal Point-White"): 11.719,
        ("Female", "Blue Point Bi-Color"): 1.562, ("Male", "Blue Point Bi-Color"): 1.562,
        ("Female", "Blue Point"): 0.781, ("Male", "Blue Point"): 0.781,
        ("Female", "Blue Point-White"): 0.781, ("Male", "Blue Point-White"): 0.781,
    }),
    ("Blue Point Mitted", "Blue Point Mitted", {
        ("Female", "Blue Point Mitted"): 25.0, ("Male", "Blue Point Mitted"): 25.0,
        ("Female", "Blue Point"): 12.5, ("Male", "Blue Point"): 12.5,
        ("Female", "Blue Point-White"): 12.5, ("Male", "Blue Point-White"): 12.5,
    }),
]

# ---------------------------------------------------------------------------
# Turkish Van (固定: S/S。Van パターン白斑)
#   ※ normal モードは Van→-White に正規化する (データ正本 §5.2) ため出力名は "-White"。
#   黒系(Black-White) / 赤系(Red-White。伴性 O)。Black♂ × Red♀ → 息子 Red-White・娘 Calico。
# ---------------------------------------------------------------------------
_VAN_CROSSES = [
    ("Black-White Van", "Black-White Van", {
        ("Female", "Black-White"): 46.875, ("Male", "Black-White"): 46.875,
        ("Female", "Blue-White"): 3.125, ("Male", "Blue-White"): 3.125,
    }),
    ("Red-White Van", "Red-White Van", {
        ("Female", "Red-White"): 46.875, ("Male", "Red-White"): 46.875,
        ("Female", "Cream-White"): 3.125, ("Male", "Cream-White"): 3.125,
    }),
    # 黒系♂ × 赤系♀: 息子 Red-White・娘 Calico (トーティ+白斑)。希釈で Cream-White/Dilute Calico
    ("Black-White Van", "Red-White Van", {
        ("Male", "Red-White"): 46.875, ("Female", "Calico"): 46.875,
        ("Male", "Cream-White"): 3.125, ("Female", "Dilute Calico"): 3.125,
    }),
]

# Somali は Abyssinian の長毛版で色柄遺伝は同一 (A/A C/C w/w s/s Ta/Ta)。
# 毛長は毛色計算に影響しないため同一クロス表を共有する。
BREED_CROSSES: dict[str, list] = {
    "Abyssinian": _ABYSSINIAN_CROSSES,
    "Somali": _ABYSSINIAN_CROSSES,
    "Burmese": _BURMESE_CROSSES,
    "European Burmese": _EUROPEAN_BURMESE_CROSSES,
    "Havana Brown": _HAVANA_BROWN_CROSSES,
    "Toyger": _TOYGER_CROSSES,
    "Pixiebob": _PIXIEBOB_CROSSES,
    "Bombay": _BOMBAY_CROSSES,
    "Chartreux": _SOLID_BLUE_CROSSES,
    "Korat": _SOLID_BLUE_CROSSES,
    "Russian Blue": _SOLID_BLUE_CROSSES,
    "Nebelung": _NEBELUNG_CROSSES,
    "Lykoi": _LYKOI_CROSSES,
    "Khao Manee": _KHAO_MANEE_CROSSES,
    "Australian Mist": _AUSTRALIAN_MIST_CROSSES,
    "Singapura": _SINGAPURA_CROSSES,
    # ポイント系 (C=cs/cs)。プレーンなポイント色は遺伝的に同一結果のため同一クロス表を共有する。
    # (Birman/Ragdoll/Snowshoe の Mitted/Bi-Color 固有色は別途扱う。ここではポイント色のみ検証)
    "Siamese": _POINT_CROSSES,
    "Balinese": _POINT_CROSSES,
    "Colorpoint Shorthair": _POINT_CROSSES,
    "Balinese-(Javanese)": _POINT_CROSSES,
    # Thai (旧タイプ Siamese)。C=cs/cs w/w s/s で Siamese と同一ポイント遺伝。
    "Thai": _POINT_CROSSES,
    "Birman": _POINT_CROSSES,
    # Ragdoll / Snowshoe はプレーン点色 + Mitted/Bi-Color を持つ (同一グループ)。
    "Ragdoll": _POINT_CROSSES + _POINT_WHITE_CROSSES,
    "Snowshoe": _POINT_CROSSES + _POINT_WHITE_CROSSES,
    # スポテッド系 (A/A Sp/Sp)。遺伝同一のため共有。
    "Egyptian Mau": _SPOTTED_CROSSES,
    "Ocicat": _SPOTTED_CROSSES,
    # ミンク系 (cb/cs)。
    "Tonkinese": _TONKINESE_CROSSES,
    # Van 白斑 (S/S)。
    "Turkish Van": _VAN_CROSSES,
}


def _flatten() -> list[tuple[str, str, str, dict]]:
    cases: list[tuple[str, str, str, dict]] = []
    for breed, crosses in BREED_CROSSES.items():
        for sire, dam, expected in crosses:
            cases.append((breed, sire, dam, expected))
    return cases


_CASES = _flatten()


@pytest.fixture(scope="module")
def calc() -> CoatColorCalculator:
    return CoatColorCalculator()


@pytest.mark.parametrize(
    "breed, sire, dam, expected",
    _CASES,
    ids=[f"{b}:{s}x{d}" for b, s, d, _ in _CASES],
)
def test_breed_coat_color_cross(
    breed: str, sire: str, dam: str, expected: dict, calc: CoatColorCalculator
) -> None:
    """品種指定クロスで、期待する毛色が正しい確率で出る (未分類ゼロ・合計100%)。"""

    report = calc.calculate_report(sire, dam, breed, "normal")

    # 未分類 (分類不能な子猫) が残っていないこと = その品種の全結果に名前が付く。
    assert report.unmatched_probability < 0.0001, (
        f"{breed} {sire}×{dam}: 未分類 {report.unmatched_probability:.4f} が残っている"
        f" (samples={report.unmatched_samples[:2]})"
    )

    actual = {
        (r.sex, r.color): round(r.probability_pct, 3) for r in report.results
    }
    assert actual == expected, (
        f"{breed} {sire}×{dam}: 出力が期待と不一致\n  期待={expected}\n  実際={actual}"
    )
    # 表示合計は 100% (再正規化ではなく、未分類ゼロの帰結として)。
    assert round(sum(actual.values()), 2) == 100.0
