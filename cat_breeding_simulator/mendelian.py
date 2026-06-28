"""座位単位のメンデル分離を扱う純粋関数群。"""

from __future__ import annotations

from collections import defaultdict
from fractions import Fraction
from typing import Literal

Sex = Literal["male", "female"]
OffspringSex = Literal["Male", "Female"]
AutosomalPair = tuple[str, str]
AutosomalDistribution = dict[AutosomalPair, Fraction]
LocusState = tuple[tuple[str, AutosomalPair], ...]
LocusDistribution = dict[LocusState, Fraction]
OLocusDistribution = dict[tuple[OffspringSex, AutosomalPair], Fraction]


_ALLELE_PRIORITY: dict[str, dict[str, int]] = {
    "B": {"B": 0, "b": 1, "bl": 2},
    "D": {"D": 0, "d": 1},
    "A": {"A": 0, "a": 1},
    "C": {"C": 0, "cb": 1, "cs": 2},
    "I": {"I": 0, "i": 1},
    "Wb": {"Wb": 0, "wb": 1},
    "O": {"O": 0, "o": 1, "Y": 2},
}


def canonical_pair(locus: str, alleles: AutosomalPair) -> AutosomalPair:
    """比較用にアレル順を座位ごとの優性順へ正規化する。"""

    priority = _ALLELE_PRIORITY.get(locus, {})
    ordered = sorted(alleles, key=lambda allele: priority.get(allele, 99))
    return (ordered[0], ordered[1])


def allele_distribution(alleles: AutosomalPair) -> dict[str, Fraction]:
    """親の1座位から配偶子へ渡るアレル確率を返す。"""

    first, second = alleles
    if first == second:
        return {first: Fraction(1, 1)}
    return {first: Fraction(1, 2), second: Fraction(1, 2)}


def cross_autosomal_locus(
    locus: str,
    sire_alleles: AutosomalPair,
    dam_alleles: AutosomalPair,
) -> AutosomalDistribution:
    """常染色体1座位の子遺伝子型分布を分数で返す。"""

    results: defaultdict[AutosomalPair, Fraction] = defaultdict(Fraction)
    sire_distribution = allele_distribution(sire_alleles)
    dam_distribution = allele_distribution(dam_alleles)
    for sire_allele, sire_probability in sire_distribution.items():
        for dam_allele, dam_probability in dam_distribution.items():
            key = canonical_pair(locus, (sire_allele, dam_allele))
            results[key] += sire_probability * dam_probability
    return dict(results)


def cross_autosomal_loci(
    loci: dict[str, tuple[AutosomalPair, AutosomalPair]],
) -> LocusDistribution:
    """複数常染色体座位を独立分離として合成した分布を返す。"""

    combined: LocusDistribution = {(): Fraction(1, 1)}
    for locus, (sire_alleles, dam_alleles) in loci.items():
        locus_distribution = cross_autosomal_locus(locus, sire_alleles, dam_alleles)
        next_combined: defaultdict[LocusState, Fraction] = defaultdict(Fraction)
        for state, current_probability in combined.items():
            state_map = dict(state)
            for offspring_pair, locus_probability in locus_distribution.items():
                state_map[locus] = offspring_pair
                key = tuple(sorted(state_map.items()))
                next_combined[key] += current_probability * locus_probability
        combined = dict(next_combined)
    return combined


def o_locus_gamete_distribution(sex: Sex, alleles: AutosomalPair) -> dict[str, Fraction]:
    """O座位の親配偶子分布を返す。オスではYも配偶子として扱う。"""

    first, second = alleles
    if sex == "male":
        orange_allele = "O" if "O" in alleles else "o"
        return {orange_allele: Fraction(1, 2), "Y": Fraction(1, 2)}
    if first == second:
        return {first: Fraction(1, 1)}
    return {first: Fraction(1, 2), second: Fraction(1, 2)}


def cross_o_locus(sire_alleles: AutosomalPair, dam_alleles: AutosomalPair) -> OLocusDistribution:
    """伴性遺伝のO座位について、性別込みの子遺伝子型分布を返す。"""

    results: defaultdict[tuple[OffspringSex, AutosomalPair], Fraction] = defaultdict(Fraction)
    sire_distribution = o_locus_gamete_distribution("male", sire_alleles)
    dam_distribution = o_locus_gamete_distribution("female", dam_alleles)
    for sire_allele, sire_probability in sire_distribution.items():
        for dam_allele, dam_probability in dam_distribution.items():
            if sire_allele == "Y":
                key: tuple[OffspringSex, AutosomalPair] = ("Male", (dam_allele, "Y"))
            else:
                key = ("Female", canonical_pair("O", (sire_allele, dam_allele)))
            results[key] += sire_probability * dam_probability
    return dict(results)


def b_locus_state(alleles: AutosomalPair) -> str:
    """B座位の発現状態を返す。"""

    if "B" in alleles:
        return "black_series"
    if "b" in alleles:
        return "chocolate_series"
    return "cinnamon_series"


def d_locus_state(alleles: AutosomalPair) -> str:
    """D座位の発現状態を返す。"""

    return "dilute" if alleles == ("d", "d") else "dense"


def a_locus_state(alleles: AutosomalPair) -> str:
    """A座位の発現状態を返す。"""

    return "agouti" if "A" in alleles else "solid"


def c_locus_state(alleles: AutosomalPair) -> str:
    """C座位の発現状態を返す。"""

    if "C" in alleles:
        return "full_color"
    if "cb" in alleles and "cs" in alleles:
        return "mink"
    if alleles == ("cb", "cb"):
        return "sepia"
    return "point"


def i_locus_state(alleles: AutosomalPair) -> str:
    """I座位の発現状態を返す。"""

    return "silver_or_smoke" if "I" in alleles else "non_silver"


def o_locus_state(sex: OffspringSex, alleles: AutosomalPair) -> str:
    """O座位の発現状態を性別込みで返す。"""

    if sex == "Male":
        return "red_series" if "O" in alleles else "non_red"
    if "O" in alleles and "o" in alleles:
        return "tortie"
    if "O" in alleles:
        return "red_series"
    return "non_red"


def base_color_state(b_alleles: AutosomalPair, d_alleles: AutosomalPair) -> str:
    """B座位とD座位から基底カラー状態を返す。"""

    b_state = b_locus_state(b_alleles)
    dilute = d_locus_state(d_alleles) == "dilute"
    if b_state == "black_series":
        return "blue" if dilute else "black"
    if b_state == "chocolate_series":
        return "lilac" if dilute else "chocolate"
    return "fawn" if dilute else "cinnamon"


def golden_series_state(b_alleles: AutosomalPair, d_alleles: AutosomalPair) -> str:
    """ゴールデン修飾後もB/D座位の基底カラーを保持した状態名を返す。"""

    return f"{base_color_state(b_alleles, d_alleles)}_golden"
