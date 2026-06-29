"""計算モード (normal / explicit_carrier) と座位別キャリア展開の回帰テスト。

normal_mode では未明示キャリア (B/b, B/bl, C/cs, C/cb, A/a, Wb) を閉じる。
explicit_carrier_mode では sire_carriers / dam_carriers で指定された座位のみ開ける。
carrier_exploration_mode は Phase 2 (本テストでは明示エラーを検証)。

シミュレーター正本 V9 §2.1〜2.4 に準拠。運用正本 §5 のテスト構成に合わせ、
モード/キャリア挙動の必須テストを本ファイルに集約する。
"""

from __future__ import annotations

import pytest

from cat_breeding_simulator.engine import BreedingCalculationError, CoatColorCalculator


def _pct(results, substring: str) -> float:
    return round(sum(r.probability_pct for r in results if substring in r.color), 3)


def _has(results, substring: str) -> bool:
    return any(substring in r.color for r in results)


@pytest.fixture
def calc() -> CoatColorCalculator:
    return CoatColorCalculator()


# --- C-locus (ポイント) ---

def test_c_locus_normal_no_point(calc) -> None:
    """Point × Full(C/C) は normal では Point を出さない (C/cs 非展開)。"""
    results = calc.calculate("Seal Point", "Black", mode="normal")
    assert not _has(results, "Point")


def test_c_locus_explicit_point_50(calc) -> None:
    """Point × carrier(C/cs) は explicit で Point 50%。"""
    results = calc.calculate("Seal Point", "Black", mode="explicit_carrier", dam_carriers={"C": "C/cs"})
    assert abs(_pct(results, "Point") - 50.0) < 0.5


# --- B-locus (チョコレート) ---

def test_b_locus_normal_no_chocolate(calc) -> None:
    """Chocolate × Black(B/B) は normal では Chocolate を出さない (B/b 非展開)。"""
    results = calc.calculate("Chocolate", "Black", mode="normal")
    assert not _has(results, "Chocolate")
    assert not _has(results, "Lilac")


def test_b_locus_explicit_chocolate_series_50(calc) -> None:
    """Chocolate × carrier(B/b) は explicit でチョコ系 (b/b) 50%。

    親が D/- (濃色ヘテロ未確定) のため b/b は Chocolate(濃) と Lilac(希釈) に分かれるが、
    チョコ系 (b/b) 合計は 50% になる。
    """
    results = calc.calculate("Chocolate", "Black", mode="explicit_carrier", dam_carriers={"B": "B/b"})
    chocolate_series = _pct(results, "Chocolate") + _pct(results, "Lilac")
    assert _has(results, "Chocolate")
    assert abs(chocolate_series - 50.0) < 0.5


# --- A-locus (タビー/ソリッド) ---

def test_a_locus_normal_no_solid(calc) -> None:
    """Tabby × Tabby は normal では Solid を出さない (A/a 非展開, 全出力タビー系)。"""
    results = calc.calculate("Brown Tabby", "Brown Tabby", mode="normal")
    assert all("Tabby" in r.color for r in results)


def test_a_locus_explicit_solid_25(calc) -> None:
    """A/a × A/a は explicit で Solid 25% (a/a)。"""
    results = calc.calculate(
        "Brown Tabby", "Brown Tabby",
        mode="explicit_carrier",
        sire_carriers={"A": "A/a"}, dam_carriers={"A": "A/a"},
    )
    solid = round(sum(r.probability_pct for r in results if "Tabby" not in r.color), 3)
    assert abs(solid - 25.0) < 0.5


# --- D-locus (希釈) ---

def test_d_locus_explicit_dilute_50(calc) -> None:
    """d/d × D/d は希釈 (Blue 系) 50%。"""
    results = calc.calculate("Blue", "Black", mode="explicit_carrier", dam_carriers={"D": "D/d"})
    assert abs(_pct(results, "Blue") - 50.0) < 0.5


# --- I-locus (シルバー) ---

def test_i_locus_explicit_silver_50(calc) -> None:
    """I/i × i/i は Silver 50% (explicit で I/i に固定)。"""
    results = calc.calculate(
        "Silver Tabby", "Brown Tabby",
        mode="explicit_carrier", sire_carriers={"I": "I/i"},
    )
    assert abs(_pct(results, "Silver") - 50.0) < 0.5


# --- S-locus (白斑) ---

def test_s_locus_normal_white_50(calc) -> None:
    """S/s × s/s は -White あり 50%。"""
    results = calc.calculate("Brown Tabby-White", "Brown Tabby", mode="normal")
    assert abs(_pct(results, "-White") - 50.0) < 0.5


def test_s_locus_non_white_parents_never_produce_white_spotting(calc) -> None:
    """s/s × s/s は白斑あり (-White) を生まない。"""

    report = calc.calculate_report("Brown Tabby", "Brown Tabby", breed=None, mode="normal")
    white_spotted = [result.color for result in report.results if "-White" in result.color]
    assert not white_spotted
    assert report.unmatched_probability == 0


# --- Wb (ワイドバンド/tipping) ---

def test_wb_not_auto_generated_in_normal(calc) -> None:
    """normal では非ワイドバンド親からワイドバンド (Shell/Shaded/Chinchilla/Golden) を生成しない。"""
    results = calc.calculate("Brown Tabby", "Brown Tabby", mode="normal")
    wideband = [r.color for r in results if any(w in r.color for w in ("Shell", "Shaded", "Chinchilla", "Golden"))]
    assert not wideband


def test_i_locus_non_silver_parents_never_produce_silver_or_smoke(calc) -> None:
    """i/i × i/i は Silver / Smoke 系を生まない。"""

    report = calc.calculate_report("Brown Tabby", "Brown Tabby", breed=None, mode="normal")
    silver_or_smoke = [
        result.color
        for result in report.results
        if "Silver" in result.color or "Smoke" in result.color
    ]
    assert not silver_or_smoke
    assert report.unmatched_probability == 0


def test_unspecified_tabby_pair_does_not_invent_named_tabby_subpatterns(calc) -> None:
    """通常タビー同士から、未明示の Classic / Mackerel / Ticked / Spotted 柄を勝手に出さない。"""

    report = calc.calculate_report("Brown Tabby", "Brown Tabby", breed=None, mode="normal")
    unexpected_patterns = [
        result.color
        for result in report.results
        if any(
            pattern in result.color
            for pattern in ("Classic", "Mackerel", "Ticked", "Spotted")
        )
    ]
    assert not unexpected_patterns
    assert report.unmatched_probability == 0


def test_male_offspring_never_get_female_only_tortie_or_calico_names(calc) -> None:
    """通常XYオスには Tortie / Calico / Blue Cream / Patched Tabby 系を出さない。"""

    report = calc.calculate_report("Red", "Tortoiseshell", breed=None, mode="normal")
    forbidden = (
        "Tortie",
        "Tortoiseshell",
        "Calico",
        "Dilute Calico",
        "Blue Cream",
        "Lilac Cream",
        "Patched",
    )
    offenders = [
        result.color
        for result in report.results
        if result.sex == "Male" and any(token in result.color for token in forbidden)
    ]
    assert not offenders
    assert report.unmatched_probability == 0


def test_black_pair_normal_does_not_invent_closed_or_unexpressed_loci(calc) -> None:
    """Black × Black normal は、未明示の W/S/I/Wb/C/Ta/Sp を勝手に出力しない。

    D座位は normal で D/- 展開されるため Blue は許容する。一方、表現型・猫種・明示
    キャリアに根拠がない優性白/白斑/シルバー/ワイドバンド/ポイント/ティックド/
    スポットは通常結果に混ぜてはならない。
    """

    report = calc.calculate_report("Black", "Black", breed=None, mode="normal")
    forbidden_tokens = (
        "White",
        "Silver",
        "Smoke",
        "Golden",
        "Chinchilla",
        "Shaded",
        "Shell",
        "Point",
        "Mink",
        "Sepia",
        "Ticked",
        "Spotted",
    )
    offenders = [
        (result.sex, result.color, token)
        for result in report.results
        for token in forbidden_tokens
        if token in result.color
    ]
    assert not offenders
    assert report.unmatched_probability == 0


def test_c_locus_point_pair_never_returns_full_color(calc) -> None:
    """cs/cs × cs/cs は C/- のフルカラーへ戻らず、全出力が Point 系になる。"""

    report = calc.calculate_report("Seal Point", "Seal Point", breed=None, mode="normal")
    assert report.results
    assert all("Point" in result.color for result in report.results)
    assert report.unmatched_probability == 0


# --- 130×204 normal (全出力タビー/パッチドタビー系) ---

def test_130x204_normal_all_tabby(calc) -> None:
    report = calc.calculate_report("Silver Tabby", "Blue Pt Tabby-White", breed=None, mode="normal")
    non_tabby = sorted({r.color for r in report.results if "Tabby" not in r.color})
    assert not non_tabby, f"130×204 normal に非タビー系が出力された: {non_tabby}"
    assert report.unmatched_probability == 0
    assert abs(round(sum(r.probability_pct for r in report.results), 4) - 100.0) < 0.01


# --- モード情報 (mode / opened_loci / closed_loci / assumptions) ---

def test_normal_mode_metadata(calc) -> None:
    report = calc.calculate_report("Silver Tabby", "Blue Pt Tabby-White", breed=None, mode="normal")
    assert report.mode == "normal"
    assert "A" in (report.closed_loci or [])
    assert "C" in (report.closed_loci or [])
    assert "D" in (report.opened_loci or [])
    assert report.assumptions


def test_explicit_carrier_metadata_opens_locus(calc) -> None:
    report = calc.calculate_report(
        "Seal Point", "Black", breed=None,
        mode="explicit_carrier", dam_carriers={"C": "C/cs"},
    )
    assert report.mode == "explicit_carrier"
    assert "C" in (report.opened_loci or [])
    assert "C" not in (report.closed_loci or [])


# --- carrier_exploration_mode (Phase 2) ---

def test_carrier_exploration_reveals_point_from_one_point_parent(calc) -> None:
    """片親 Point (cs/cs) × 相手 Full の場合、相手 C/cs キャリア仮説で Point が出現する。

    normal の results には Point は出ず、carrier_exploration_results に分離される。
    """
    report = calc.calculate_report("Seal Point", "Black", breed=None, mode="carrier_exploration")
    # baseline (normal) には Point が出ない
    assert not any("Point" in r.color for r in report.results)
    scenarios = report.carrier_exploration_results or []
    c_scenarios = [s for s in scenarios if s.scenario.startswith("C_")]
    assert c_scenarios, "C キャリアシナリオが生成されていない"
    point_scenario = c_scenarios[0]
    assert any("Point" in color for color in point_scenario.new_colors)
    assert point_scenario.probability_basis == "conditional_on_other_parent_carrier"
    assert point_scenario.prior_probability_applied is False
    assert abs(round(sum(r.probability_pct for r in point_scenario.results), 4) - 100.0) < 0.01


def test_carrier_exploration_reveals_solid_from_one_solid_parent(calc) -> None:
    """片親 Solid (a/a) × 相手 Tabby の場合、相手 A/a キャリア仮説で Solid が出現する。"""
    report = calc.calculate_report("Brown Tabby", "Black", breed=None, mode="carrier_exploration")
    scenarios = report.carrier_exploration_results or []
    a_scenarios = [s for s in scenarios if s.scenario.startswith("A_")]
    assert a_scenarios
    assert a_scenarios[0].new_colors  # ソリッドが新規に現れる


def test_carrier_exploration_no_scenario_when_both_dominant(calc) -> None:
    """両親が同型 (Black=a/a, B/B, C/C, D/D) では、片親劣性発現の条件が無く scenario を生成しない。

    両親とも隠れキャリアかもしれない、という探索は自動生成しない (禁止事項)。
    """
    report = calc.calculate_report("Black", "Black", breed=None, mode="carrier_exploration")
    assert report.carrier_exploration_results == []


def test_carrier_exploration_results_separated_from_normal(calc) -> None:
    """carrier_exploration の new_colors は normal results に混ざらない。"""
    report = calc.calculate_report("Seal Point", "Black", breed=None, mode="carrier_exploration")
    normal_colors = {r.color for r in report.results}
    for scenario in report.carrier_exploration_results or []:
        for color in scenario.new_colors:
            assert color not in normal_colors


def test_unknown_mode_rejected(calc) -> None:
    with pytest.raises(BreedingCalculationError):
        calc.calculate("Black", "Black", mode="bogus_mode")
