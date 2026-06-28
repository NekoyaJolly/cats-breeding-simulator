"""座位単位のメンデル分離と基底カラー判定の精度テスト。"""

from __future__ import annotations

from fractions import Fraction

import pytest

from cat_breeding_simulator.mendelian import (
    AutosomalPair,
    LocusState,
    a_locus_state,
    b_locus_state,
    base_color_state,
    c_locus_state,
    cross_autosomal_loci,
    cross_autosomal_locus,
    cross_o_locus,
    d_locus_state,
    golden_series_state,
    i_locus_state,
    o_locus_state,
)
from cat_breeding_simulator.master_data import AUTOSOMAL_LOCI


def _assert_distribution(
    actual: dict[AutosomalPair, Fraction],
    expected: dict[AutosomalPair, Fraction],
) -> None:
    """分布を分数で比較し、合計が100%であることも同時に確認する。"""

    assert actual == expected
    assert sum(actual.values()) == Fraction(1, 1)


def _assert_locus_distribution(
    actual: dict[LocusState, Fraction],
    expected: dict[LocusState, Fraction],
) -> None:
    """複数座位の分布を表示順に依存しない正規化キーで比較する。"""

    assert actual == expected
    assert sum(actual.values()) == Fraction(1, 1)


def _state(**loci: AutosomalPair) -> LocusState:
    """テスト期待値用に座位辞書を順序非依存キーへ変換する。"""

    return tuple(sorted(loci.items()))


def _by_color(distribution: dict[LocusState, Fraction]) -> dict[str, Fraction]:
    """B/D分布を基底カラー別に集計する。"""

    colors: dict[str, Fraction] = {}
    for state, probability in distribution.items():
        state_map = dict(state)
        color = base_color_state(state_map["B"], state_map["D"])
        colors[color] = colors.get(color, Fraction(0, 1)) + probability
    return colors


def _conditional_o_states(
    sire: AutosomalPair,
    dam: AutosomalPair,
) -> dict[str, dict[str, Fraction]]:
    """O座位分布を性別ごとの条件付き確率へ変換する。"""

    distribution = cross_o_locus(sire, dam)
    by_sex: dict[str, dict[str, Fraction]] = {"Male": {}, "Female": {}}
    sex_totals: dict[str, Fraction] = {"Male": Fraction(0, 1), "Female": Fraction(0, 1)}
    for (sex, alleles), probability in distribution.items():
        sex_totals[sex] += probability
        state = o_locus_state(sex, alleles)
        by_sex[sex][state] = by_sex[sex].get(state, Fraction(0, 1)) + probability
    for sex, states in by_sex.items():
        total = sex_totals[sex]
        by_sex[sex] = {state: probability / total for state, probability in states.items()}
    return by_sex


def test_requested_loci_are_supported_by_current_app() -> None:
    """今回の任意検証対象は、現行アプリの座位定義に含まれる場合だけ後続テスト対象にする。"""

    assert "C" in AUTOSOMAL_LOCI
    assert "I" in AUTOSOMAL_LOCI
    assert "Wb" in AUTOSOMAL_LOCI


@pytest.mark.parametrize(
    "sire, dam, expected, expected_states",
    [
        (("B", "B"), ("b", "b"), {("B", "b"): Fraction(1, 1)}, {"black_series"}),
        (
            ("B", "b"),
            ("b", "b"),
            {("B", "b"): Fraction(1, 2), ("b", "b"): Fraction(1, 2)},
            {"black_series", "chocolate_series"},
        ),
        (("b", "b"), ("b", "b"), {("b", "b"): Fraction(1, 1)}, {"chocolate_series"}),
        (
            ("b", "b"),
            ("bl", "bl"),
            {("b", "bl"): Fraction(1, 1)},
            {"chocolate_series"},
        ),
        (
            ("b", "bl"),
            ("bl", "bl"),
            {("b", "bl"): Fraction(1, 2), ("bl", "bl"): Fraction(1, 2)},
            {"chocolate_series", "cinnamon_series"},
        ),
        (
            ("B", "bl"),
            ("b", "b"),
            {("B", "b"): Fraction(1, 2), ("b", "bl"): Fraction(1, 2)},
            {"black_series", "chocolate_series"},
        ),
    ],
)
def test_b_locus_distribution(
    sire: AutosomalPair,
    dam: AutosomalPair,
    expected: dict[AutosomalPair, Fraction],
    expected_states: set[str],
) -> None:
    """B座位は B > b > bl の優性順で分離し、キャリア状態も正規化キーで比較できる。"""

    actual = cross_autosomal_locus("B", sire, dam)
    _assert_distribution(actual, expected)
    assert {b_locus_state(pair) for pair in actual} == expected_states


@pytest.mark.parametrize(
    "sire, dam, expected, expected_states",
    [
        (("D", "D"), ("d", "d"), {("D", "d"): Fraction(1, 1)}, {"dense"}),
        (
            ("D", "d"),
            ("d", "d"),
            {("D", "d"): Fraction(1, 2), ("d", "d"): Fraction(1, 2)},
            {"dense", "dilute"},
        ),
        (("d", "d"), ("d", "d"), {("d", "d"): Fraction(1, 1)}, {"dilute"}),
    ],
)
def test_d_locus_distribution(
    sire: AutosomalPair,
    dam: AutosomalPair,
    expected: dict[AutosomalPair, Fraction],
    expected_states: set[str],
) -> None:
    """D座位は d/d のときだけダイリュートになる。"""

    actual = cross_autosomal_locus("D", sire, dam)
    _assert_distribution(actual, expected)
    assert {d_locus_state(pair) for pair in actual} == expected_states


@pytest.mark.parametrize(
    "loci, expected",
    [
        (
            {"B": (("B", "B"), ("b", "b")), "D": (("d", "d"), ("D", "D"))},
            {_state(B=("B", "b"), D=("D", "d")): Fraction(1, 1)},
        ),
        (
            {"B": (("B", "B"), ("b", "b")), "D": (("d", "d"), ("D", "d"))},
            {
                _state(B=("B", "b"), D=("D", "d")): Fraction(1, 2),
                _state(B=("B", "b"), D=("d", "d")): Fraction(1, 2),
            },
        ),
        (
            {"B": (("B", "b"), ("b", "b")), "D": (("d", "d"), ("D", "D"))},
            {
                _state(B=("B", "b"), D=("D", "d")): Fraction(1, 2),
                _state(B=("b", "b"), D=("D", "d")): Fraction(1, 2),
            },
        ),
        (
            {"B": (("B", "b"), ("b", "b")), "D": (("d", "d"), ("D", "d"))},
            {
                _state(B=("B", "b"), D=("D", "d")): Fraction(1, 4),
                _state(B=("B", "b"), D=("d", "d")): Fraction(1, 4),
                _state(B=("b", "b"), D=("D", "d")): Fraction(1, 4),
                _state(B=("b", "b"), D=("d", "d")): Fraction(1, 4),
            },
        ),
    ],
)
def test_b_and_d_locus_combination(
    loci: dict[str, tuple[AutosomalPair, AutosomalPair]],
    expected: dict[LocusState, Fraction],
) -> None:
    """B座位とD座位を同時に見ても独立分離の合計は100%になる。"""

    _assert_locus_distribution(cross_autosomal_loci(loci), expected)


def test_chocolate_pair_d_locus_internal_breakdown() -> None:
    """b/b D/d × b/b D/d はチョコレート系75%、ライラック25%になる。"""

    distribution = cross_autosomal_loci(
        {"B": (("b", "b"), ("b", "b")), "D": (("D", "d"), ("D", "d"))}
    )
    assert _by_color(distribution) == {
        "chocolate": Fraction(3, 4),
        "lilac": Fraction(1, 4),
    }
    _assert_locus_distribution(
        distribution,
        {
            _state(B=("b", "b"), D=("D", "D")): Fraction(1, 4),
            _state(B=("b", "b"), D=("D", "d")): Fraction(1, 2),
            _state(B=("b", "b"), D=("d", "d")): Fraction(1, 4),
        },
    )


def test_chocolate_cinnamon_dilute_combination() -> None:
    """b/bl D/d × bl/bl D/d はチョコ/ライラック/シナモン/フォーンへ 37.5/12.5/37.5/12.5 で分離する。"""

    distribution = cross_autosomal_loci(
        {"B": (("b", "bl"), ("bl", "bl")), "D": (("D", "d"), ("D", "d"))}
    )
    assert _by_color(distribution) == {
        "chocolate": Fraction(3, 8),
        "lilac": Fraction(1, 8),
        "cinnamon": Fraction(3, 8),
        "fawn": Fraction(1, 8),
    }


@pytest.mark.parametrize(
    "sire, dam, expected, expected_states",
    [
        (("A", "A"), ("a", "a"), {("A", "a"): Fraction(1, 1)}, {"agouti"}),
        (
            ("A", "a"),
            ("A", "a"),
            {
                ("A", "A"): Fraction(1, 4),
                ("A", "a"): Fraction(1, 2),
                ("a", "a"): Fraction(1, 4),
            },
            {"agouti", "solid"},
        ),
        (("a", "a"), ("a", "a"), {("a", "a"): Fraction(1, 1)}, {"solid"}),
    ],
)
def test_a_locus_distribution(
    sire: AutosomalPair,
    dam: AutosomalPair,
    expected: dict[AutosomalPair, Fraction],
    expected_states: set[str],
) -> None:
    """A座位はA/-がアグーティ、a/aがソリッドとして分離する。"""

    actual = cross_autosomal_locus("A", sire, dam)
    _assert_distribution(actual, expected)
    assert {a_locus_state(pair) for pair in actual} == expected_states


@pytest.mark.parametrize(
    "sire, dam, expected",
    [
        (("o", "Y"), ("o", "o"), {"Male": {"non_red": Fraction(1, 1)}, "Female": {"non_red": Fraction(1, 1)}}),
        (("O", "Y"), ("o", "o"), {"Male": {"non_red": Fraction(1, 1)}, "Female": {"tortie": Fraction(1, 1)}}),
        (
            ("o", "Y"),
            ("O", "o"),
            {
                "Male": {"red_series": Fraction(1, 2), "non_red": Fraction(1, 2)},
                "Female": {"tortie": Fraction(1, 2), "non_red": Fraction(1, 2)},
            },
        ),
        (
            ("O", "Y"),
            ("O", "o"),
            {
                "Male": {"red_series": Fraction(1, 2), "non_red": Fraction(1, 2)},
                "Female": {"red_series": Fraction(1, 2), "tortie": Fraction(1, 2)},
            },
        ),
        (("O", "Y"), ("O", "O"), {"Male": {"red_series": Fraction(1, 1)}, "Female": {"red_series": Fraction(1, 1)}}),
    ],
)
def test_o_locus_x_linked_distribution(
    sire: AutosomalPair,
    dam: AutosomalPair,
    expected: dict[str, dict[str, Fraction]],
) -> None:
    """O座位は父のX/Yと母のX/Xを分け、性別ごとの条件付き確率で比較する。"""

    assert _conditional_o_states(sire, dam) == expected


@pytest.mark.parametrize(
    "sire, dam, expected, expected_states",
    [
        (("C", "C"), ("cs", "cs"), {("C", "cs"): Fraction(1, 1)}, {"full_color"}),
        (("cs", "cs"), ("cs", "cs"), {("cs", "cs"): Fraction(1, 1)}, {"point"}),
        (("cb", "cb"), ("cs", "cs"), {("cb", "cs"): Fraction(1, 1)}, {"mink"}),
        (
            ("cb", "cs"),
            ("cs", "cs"),
            {("cb", "cs"): Fraction(1, 2), ("cs", "cs"): Fraction(1, 2)},
            {"mink", "point"},
        ),
    ],
)
def test_c_locus_distribution(
    sire: AutosomalPair,
    dam: AutosomalPair,
    expected: dict[AutosomalPair, Fraction],
    expected_states: set[str],
) -> None:
    """C座位はフルカラー、セピア、ポイント、ミンクを分ける。"""

    actual = cross_autosomal_locus("C", sire, dam)
    _assert_distribution(actual, expected)
    assert {c_locus_state(pair) for pair in actual} == expected_states


@pytest.mark.parametrize(
    "sire, dam, expected, expected_states",
    [
        (
            ("I", "i"),
            ("i", "i"),
            {("I", "i"): Fraction(1, 2), ("i", "i"): Fraction(1, 2)},
            {"silver_or_smoke", "non_silver"},
        ),
        (("i", "i"), ("i", "i"), {("i", "i"): Fraction(1, 1)}, {"non_silver"}),
    ],
)
def test_i_locus_distribution(
    sire: AutosomalPair,
    dam: AutosomalPair,
    expected: dict[AutosomalPair, Fraction],
    expected_states: set[str],
) -> None:
    """I座位は I/- がシルバー/スモーク系、i/i が非シルバーになる。"""

    actual = cross_autosomal_locus("I", sire, dam)
    _assert_distribution(actual, expected)
    assert {i_locus_state(pair) for pair in actual} == expected_states


@pytest.mark.parametrize(
    "b_alleles, d_alleles, expected",
    [
        (("B", "B"), ("D", "d"), "black_golden"),
        (("b", "b"), ("D", "D"), "chocolate_golden"),
        (("b", "bl"), ("D", "D"), "chocolate_golden"),
        (("bl", "bl"), ("D", "D"), "cinnamon_golden"),
        (("b", "b"), ("d", "d"), "lilac_golden"),
        (("bl", "bl"), ("d", "d"), "fawn_golden"),
    ],
)
def test_golden_modifier_keeps_b_and_d_base_color(
    b_alleles: AutosomalPair,
    d_alleles: AutosomalPair,
    expected: str,
) -> None:
    """ゴールデン修飾はB座位の系列を置き換えず、d/dなら希釈後の名称になる。"""

    assert golden_series_state(b_alleles, d_alleles) == expected
