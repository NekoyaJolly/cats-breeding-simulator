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


# --- Wb (ワイドバンド/tipping) ---

def test_wb_not_auto_generated_in_normal(calc) -> None:
    """normal では非ワイドバンド親からワイドバンド (Shell/Shaded/Chinchilla/Golden) を生成しない。"""
    results = calc.calculate("Brown Tabby", "Brown Tabby", mode="normal")
    wideband = [r.color for r in results if any(w in r.color for w in ("Shell", "Shaded", "Chinchilla", "Golden"))]
    assert not wideband


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


# --- carrier_exploration_mode は予約のみ (Phase 2) ---

def test_carrier_exploration_mode_rejected(calc) -> None:
    with pytest.raises(BreedingCalculationError):
        calc.calculate("Silver Tabby", "Blue Pt Tabby-White", mode="carrier_exploration")


def test_unknown_mode_rejected(calc) -> None:
    with pytest.raises(BreedingCalculationError):
        calc.calculate("Black", "Black", mode="bogus_mode")
