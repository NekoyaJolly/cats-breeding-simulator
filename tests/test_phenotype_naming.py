"""命名レイヤ (phenotype_naming.PhenotypeNamer) の単体スモークテスト。

engine からの抽出後も、命名モジュールが単体で機能することを軽く確認する
(交配経由の振る舞いは既存の calculator/cross テスト群が網羅)。
"""

from __future__ import annotations

import pytest

from cat_breeding_simulator.master_data import KittenGenotype
from cat_breeding_simulator.phenotype_naming import (
    GENOTYPE_TO_COLOR_MAP,
    PhenotypeNamer,
)


# 発現状態を指定して子猫遺伝子型を組み立てるテスト用ヘルパ。
# expressed_genotype_key が参照する 9 座位 (O/B/D/A/C/W/S/I/Wb) を埋める。
_ALLELE_PAIRS: dict[str, tuple[str, str]] = {
    "BB": ("B", "B"), "bb": ("b", "b"), "blbl": ("bl", "bl"),
    "DD": ("D", "D"), "dd": ("d", "d"),
    "AA": ("A", "A"), "aa": ("a", "a"),
    "CC": ("C", "C"), "cscs": ("cs", "cs"), "cbcb": ("cb", "cb"), "cbcs": ("cb", "cs"),
    "ww": ("w", "w"), "WW": ("W", "W"),
    "ss": ("s", "s"), "Ss": ("S", "s"), "SS": ("S", "S"),
    "ii": ("i", "i"), "Ii": ("I", "i"),
    "wbwb": ("wb", "wb"), "Wbwb": ("Wb", "wb"),
    "OY": ("O", "Y"), "oY": ("o", "Y"), "Oo": ("O", "o"), "OO": ("O", "O"), "oo": ("o", "o"),
}


def _kitten(
    sex: str,
    o: str,
    b: str = "BB",
    d: str = "DD",
    a: str = "aa",
    c: str = "CC",
    w: str = "ww",
    s: str = "ss",
    i: str = "ii",
    wb: str = "wbwb",
) -> KittenGenotype:
    loci = {
        "O": _ALLELE_PAIRS[o],
        "B": _ALLELE_PAIRS[b],
        "D": _ALLELE_PAIRS[d],
        "A": _ALLELE_PAIRS[a],
        "C": _ALLELE_PAIRS[c],
        "W": _ALLELE_PAIRS[w],
        "S": _ALLELE_PAIRS[s],
        "I": _ALLELE_PAIRS[i],
        "Wb": _ALLELE_PAIRS[wb],
    }
    return KittenGenotype(sex=sex, loci=loci)


def test_reverse_lookup_map_is_populated() -> None:
    # PHENOTYPE_GENOTYPES の逆引き表が構築されている。
    assert len(GENOTYPE_TO_COLOR_MAP) > 0


def test_is_female_only_color() -> None:
    namer = PhenotypeNamer()
    assert namer.is_female_only_color("Blue Patched Tabby") is True
    assert namer.is_female_only_color("Tortoiseshell") is True
    assert namer.is_female_only_color("Black") is False
    assert namer.is_female_only_color("Silver Tabby") is False


def test_construct_fallback_name_black() -> None:
    namer = PhenotypeNamer()
    # 黒 (B/B, A/A タビー, D/D 濃色, フルカラー) の子猫 → "Brown Tabby"。
    loci = {
        "B": ("B", "B"),
        "D": ("D", "D"),
        "A": ("A", "A"),
        "C": ("C", "C"),
        "W": ("w", "w"),
        "S": ("s", "s"),
        "Mc": ("Mc", "Mc"),
        "Ta": ("ta", "ta"),
        "Sp": ("sp", "sp"),
        "I": ("i", "i"),
        "Wb": ("wb", "wb"),
        "O": ("o", "Y"),
    }
    kitten = KittenGenotype(sex="Male", loci=loci)
    assert namer.construct_fallback_name(kitten) == "Brown Tabby"


def test_construct_fallback_dominant_white_is_white() -> None:
    """優性白 (W/-) は遺伝背景に依らず "White"。"""

    namer = PhenotypeNamer()
    assert namer.construct_fallback_name(_kitten("Female", "oo", w="WW")) == "White"


def test_construct_fallback_point_is_unclassified() -> None:
    """点紋系 (フルカラーでない) は通常モードの構築対象外 → None (未分類)。"""

    namer = PhenotypeNamer()
    assert namer.construct_fallback_name(_kitten("Female", "oo", c="cscs")) is None


@pytest.mark.parametrize(
    ("kitten", "expected"),
    [
        # トーティ系 (O/o メス)
        (_kitten("Female", "Oo"), "Tortoiseshell"),
        (_kitten("Female", "Oo", d="dd"), "Blue Cream"),
        (_kitten("Female", "Oo", a="AA", i="Ii"), "Silver Patched Tabby"),
        (_kitten("Female", "Oo", a="AA", i="Ii", d="dd"), "Blue Silver Patched Tabby"),
        # オレンジ系ソリッド (O/Y オス)
        (_kitten("Male", "OY"), "Red"),
        (_kitten("Male", "OY", i="Ii"), "Cameo"),
        (_kitten("Male", "OY", i="Ii", d="dd"), "Cream Smoke"),
        # 非オレンジ アグーチ シルバー (シルバータビー)
        (_kitten("Male", "oY", a="AA", i="Ii"), "Silver Tabby"),
        (_kitten("Male", "oY", a="AA", i="Ii", d="dd"), "Blue Silver Tabby"),
        # 非オレンジ ソリッド シルバー (スモーク)
        (_kitten("Male", "oY", i="Ii"), "Black Smoke"),
        (_kitten("Male", "oY", i="Ii", d="dd"), "Blue Smoke"),
    ],
)
def test_construct_fallback_solid_and_tortie_names(kitten: KittenGenotype, expected: str) -> None:
    """ソリッド/トーティ/スモークの基本命名が遺伝状態と一致する。"""

    namer = PhenotypeNamer()
    assert namer.construct_fallback_name(kitten) == expected


@pytest.mark.parametrize(
    ("kitten", "expected"),
    [
        # 非オレンジ・アグーチ・ワイドバンド = tipping (Golden / Silver)
        (_kitten("Female", "oo", a="AA", wb="Wbwb"), "Golden"),
        (_kitten("Female", "oo", a="AA", d="dd", wb="Wbwb"), "Blue Golden"),
        (_kitten("Female", "oo", a="AA", i="Ii", wb="Wbwb"), "Silver"),
        (_kitten("Female", "oo", a="AA", wb="Wbwb", s="Ss"), "Golden-White"),
        # B/D 座位を残す接頭辞 (_wideband_base_prefix)
        (_kitten("Female", "oo", a="AA", b="bb", wb="Wbwb"), "Chocolate Golden"),
        (_kitten("Female", "oo", a="AA", b="bb", d="dd", wb="Wbwb"), "Lilac Golden"),
        (_kitten("Female", "oo", a="AA", b="blbl", wb="Wbwb"), "Cinnamon Golden"),
        (_kitten("Female", "oo", a="AA", b="blbl", d="dd", wb="Wbwb"), "Fawn Golden"),
    ],
)
def test_construct_fallback_wideband_tipping(kitten: KittenGenotype, expected: str) -> None:
    """ワイドバンド tipping は非オレンジ・アグーチでのみ Golden/Silver として命名する。"""

    namer = PhenotypeNamer()
    assert namer.construct_fallback_name(kitten) == expected


def test_construct_fallback_tipping_degree_from_parents() -> None:
    """tipping の濃淡 (Shell/Shaded/Chinchilla) は親カラー名から推論する。"""

    namer = PhenotypeNamer()
    base = _kitten("Female", "oo", a="AA", wb="Wbwb")
    assert namer.construct_fallback_name(base, "Shaded Golden", "Black") == "Shaded Golden"
    assert namer.construct_fallback_name(base, "Chinchilla Golden", "x") == "Chinchilla Golden"
    # "Tortoiseshell" の部分文字列 "shell" を誤検出しない (単語境界判定)。
    assert namer.construct_fallback_name(base, "Tortoiseshell", "Black") == "Golden"


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Black Pt Silver Tabby", "Silver Pt Tabby"),
        ("Black Silver Tabby", "Silver Tabby"),
        ("Blue Pt Silver Tabby", "Blue Silver Pt Tabby"),
        ("Blue Mackerel Silver Tabby", "Blue Silver Mackerel Tabby"),
        ("Red Silver Tabby", "Cameo Tabby"),
        ("Cream Silver Tabby", "Cream Cameo Tabby"),
        ("Chocolate Silver Tabby", "Chocolate Silver Tabby"),
        ("Lilac Silver Tabby", "Lilac Silver Tabby"),
        ("Cinnamon Silver Tabby", "Cinnamon Silver Tabby"),
        ("Fawn Silver Tabby", "Fawn Silver Tabby"),
        # 非シルバーのタビーは Black → Brown へ正規化
        ("Black Pt Tabby", "Brown Pt Tabby"),
        ("Black Tabby", "Brown Tabby"),
    ],
)
def test_clean_phenotype_name_silver_and_tabby_normalization(raw: str, expected: str) -> None:
    """Silver/Tabby 系の表示名整形が、各接頭辞パターンで正しく変換される。"""

    namer = PhenotypeNamer()
    assert namer.clean_phenotype_name(raw) == expected
