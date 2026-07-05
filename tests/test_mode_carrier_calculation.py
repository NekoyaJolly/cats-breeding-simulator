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

def test_a_locus_normal_produces_solid(calc) -> None:
    """Tabby × Tabby は normal でも Solid を出す (A をカテゴリA として X/- 展開)。

    タビー猫は A/A か A/a か表現型で区別できないため、両親が A/a のとき (各50% → 両方25%)
    子の 1/4 が a/a となり、全体で約 6.25% がソリッドになる。
    逆方向 (a/a × a/a → タビー) は配偶子に A が無いため発生しない (不可逆ルール維持)。
    """
    results = calc.calculate("Brown Tabby", "Brown Tabby", mode="normal")
    solid = round(sum(r.probability_pct for r in results if "Tabby" not in r.color), 3)
    assert abs(solid - 6.25) < 0.5
    solid_cross = calc.calculate("Black", "Black", mode="normal")
    assert all("Tabby" not in r.color for r in solid_cross)


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


@pytest.mark.parametrize(
    ("sire_color", "dam_color"),
    [
        ("Seal Point", "Seal Point"),
        ("Blue Lynx Point", "Flame Point-White"),
        ("Chocolate Point", "Lilac Cream Point-White"),
    ],
)
def test_c_locus_point_pair_never_returns_full_color(
    calc,
    sire_color: str,
    dam_color: str,
) -> None:
    """cs/cs × cs/cs は C/- のフルカラーへ戻らず、全出力が Point 系になる。"""

    report = calc.calculate_report(sire_color, dam_color, breed=None, mode="normal")
    assert report.results
    assert all("Point" in result.color for result in report.results)
    assert report.unmatched_probability == 0


# --- 130×204 normal (全出力タビー/パッチドタビー系) ---

def test_130x204_normal_includes_solid(calc) -> None:
    """A をカテゴリA として展開するため、タビー親同士でも normal で a/a 前提カラー
    (Solid / Smoke / Tortie 等) が出る。未分類ゼロ・合計100% の不変条件は維持する。"""
    report = calc.calculate_report("Silver Tabby", "Blue Pt Tabby-White", breed=None, mode="normal")
    non_tabby = sorted({r.color for r in report.results if "Tabby" not in r.color})
    assert non_tabby, "A 展開後は a/a 前提カラー (非タビー系) が出るはず"
    assert report.unmatched_probability == 0
    assert abs(round(sum(r.probability_pct for r in report.results), 4) - 100.0) < 0.01


# --- モード情報 (mode / opened_loci / closed_loci / assumptions) ---

def test_normal_mode_metadata(calc) -> None:
    report = calc.calculate_report("Silver Tabby", "Blue Pt Tabby-White", breed=None, mode="normal")
    assert report.mode == "normal"
    assert "A" in (report.opened_loci or [])  # A はカテゴリA として展開座位に移動
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


def test_normal_reveals_solid_from_tabby_parent_without_carrier_mode(calc) -> None:
    """A をカテゴリA として normal で展開するため、Brown Tabby × Black では
    carrier_exploration を使わずとも normal 時点でソリッドが出る。

    A/a の可能性は normal がカバーするため、carrier_exploration の A/a シナリオは
    normal に対する新規色を追加しない (new_colors が空)。B/C 系の潜在キャリア探索とは異なる。
    """
    normal = calc.calculate_report("Brown Tabby", "Black", breed=None, mode="normal")
    assert any("Tabby" not in r.color for r in normal.results)  # normal で既にソリッドが出る
    report = calc.calculate_report("Brown Tabby", "Black", breed=None, mode="carrier_exploration")
    a_scenarios = [s for s in (report.carrier_exploration_results or []) if s.scenario.startswith("A_")]
    for scenario in a_scenarios:
        assert not scenario.new_colors  # normal が既にカバー = 新規色なし


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


# --- P2「もしこの色が出たら」(confirmed_results / conditional_color_groups) ---


def test_color_family_grouping_labels() -> None:
    """色系統グルーピング: BaseSeries×Dilution・ポイント・セピア・シルバーのラベル合成。"""

    from cat_breeding_simulator.color_master import color_family

    assert color_family("Blue") == "ブルー系"          # black + dilute
    assert color_family("Cinnamon") == "シナモン系"     # cinnamon + dense
    assert color_family("Fawn") == "フォーン系"         # cinnamon + dilute
    assert color_family("Sable") == "セピア系"          # C/cb セピアは「もし出たら」に入れる
    assert color_family("Seal Point") == "ポイント系"   # C/cs ポイントは除外対象
    assert color_family("Silver") == "シルバー系"


def test_confirmed_results_excludes_category_a_colors(calc) -> None:
    """確定色 (confirmed_results) は隠れキャリア由来のカテゴリA色 (希釈ブルー) を含まない。

    Ruddy×Ruddy(Abyssinian) は既存 results には D/- 展開で Blue が出るが、confirmed_results は
    Ruddy のみ (確定的な希釈は無い)。B2: 既存 results 側は不変で Blue を残す。
    """

    report = calc.calculate_report("Ruddy", "Ruddy", breed="Abyssinian", mode="normal")
    confirmed = {r.color for r in (report.confirmed_results or [])}
    assert confirmed == {"Ruddy"}
    # B2: 既存 results は不変 (カテゴリA 展開で Blue が出るまま)。
    assert any(r.color == "Blue" for r in report.results)


def test_conditional_blue_group_with_reverse_inference(calc) -> None:
    """Ruddy×Ruddy(Abyssinian): 「ブルー系」が両親 D/d で約25%、ポイント系は出ない。"""

    report = calc.calculate_report("Ruddy", "Ruddy", breed="Abyssinian", mode="normal")
    groups = report.conditional_color_groups or []
    blue = [g for g in groups if g.family_label == "ブルー系"]
    assert blue, "ブルー系グループが無い"
    assert "Blue" in blue[0].colors
    assert abs(blue[0].conditional_probability_pct - 25.0) < 0.5
    assert blue[0].reverse_inference_label == "この色が出たら両親が D/d 保因と確定します"
    assert blue[0].assumed_carriers == {"sire": {"D": "D/d"}, "dam": {"D": "D/d"}}
    # ポイント (C/cs 由来) は色系統に入れない。
    assert not any(g.family_label == "ポイント系" for g in groups)


def test_conditional_excludes_point_even_when_point_offspring_possible(calc) -> None:
    """片親 Point (cs/cs) × Full でも、conditional にポイント系は出さない (色数過多のため除外)。"""

    report = calc.calculate_report("Seal Point", "Black", breed=None, mode="normal")
    groups = report.conditional_color_groups or []
    assert groups, "条件付きグループが生成されていない"
    assert not any(g.family_label == "ポイント系" for g in groups)
    assert not any("Point" in color for g in groups for color in g.colors)


def test_conditional_recessive_parent_reverse_inference_single_parent(calc) -> None:
    """片親が劣性発現 (Chocolate=b/b) のとき、相手 (Black) の B/b 保因を単親逆推論で提示する。"""

    report = calc.calculate_report("Chocolate", "Black", breed=None, mode="normal")
    groups = report.conditional_color_groups or []
    choco = [g for g in groups if g.family_label == "チョコレート系"]
    assert choco, "チョコレート系グループが無い"
    assert choco[0].reverse_inference_label == "この色が出たら母が B/b 保因と確定します"
    assert choco[0].assumed_carriers == {"dam": {"B": "B/b"}}


def test_conditional_sepia_group_shown_point_excluded(calc) -> None:
    """セピアが絡む交配ではセピア系を「もしこの色が出たら」に出し、ポイントは出さない。

    Champagne × Sable (Burmese): 両親セピア (cb/cb)。片親 Champagne が b/b を発現するため
    相手 Sable の B/b 保因を仮定するとチョコ系セピア (Champagne) が条件付きで出る。セピアは
    含め、ポイント (cs 由来) は色系統に入れない。
    """

    report = calc.calculate_report("Champagne", "Sable", breed="Burmese", mode="normal")
    groups = report.conditional_color_groups or []
    sepia = [g for g in groups if g.family_label == "セピア系"]
    assert sepia, "セピア系グループが無い"
    assert sepia[0].colors  # 具体的なセピア色が含まれる
    assert "C/cb" in sepia[0].reverse_inference_label or "B/b" in sepia[0].reverse_inference_label
    assert not any(g.family_label == "ポイント系" for g in groups)


def test_conditional_only_normal_mode(calc) -> None:
    """confirmed_results / conditional_color_groups は normal モードのみ設定される。"""

    explicit = calc.calculate_report(
        "Seal Point", "Black", breed=None,
        mode="explicit_carrier", dam_carriers={"C": "C/cs"},
    )
    assert explicit.confirmed_results is None
    assert explicit.conditional_color_groups is None
    exploration = calc.calculate_report("Seal Point", "Black", breed=None, mode="carrier_exploration")
    assert exploration.confirmed_results is None
    assert exploration.conditional_color_groups is None
