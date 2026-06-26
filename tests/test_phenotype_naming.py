"""命名レイヤ (phenotype_naming.PhenotypeNamer) の単体スモークテスト。

engine からの抽出後も、命名モジュールが単体で機能することを軽く確認する
(交配経由の振る舞いは既存の calculator/cross テスト群が網羅)。
"""

from __future__ import annotations

from cat_breeding_simulator.master_data import KittenGenotype
from cat_breeding_simulator.phenotype_naming import (
    GENOTYPE_TO_COLOR_MAP,
    PhenotypeNamer,
)


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
