"""130 (Silver Tabby) x 204 (Blue Pt Tabby-White) 通常計算の出力健全性テスト。

通常モードでは、表現されている優性形質のうち D(濃色)・I(シルバー) は
X/- = {X/X, X/x} として扱う。よって父 Silver Tabby は D/-・I/- となり、子には
Blue 系 (父 D/d)・Brown 系 (父 I/i) が正しく出る。母 O/o によりメスには
Patched Tabby 系が出る。

一方、A(タビー) は normal_mode では A/A 相当に固定し A/a を展開しない。
よって a/a 前提の Solid / Smoke / Tortie / Calico / Tortoiseshell は通常結果に出さない
(母 O/o のトーティは Patched Tabby であり Calico/Tortoiseshell ではない)。
B/C 系の潜在キャリア (チョコ/シナモン/ポイント/セピア) も展開しない。

本テストは、これら非展開カラーが出ないこと・全出力がタビー系であること・
オス禁止ルール・0%禁止・未分類ゼロ・合計100% を回帰検証する。
明示キャリア/全キャリア探索モードでは別の許容範囲となるため分離する。
"""

from __future__ import annotations

import pytest

from cat_breeding_simulator.engine import CoatColorCalculator

# 父 130 / 母 204 から解決されるカラー名
SIRE_COLOR = "Silver Tabby"
DAM_COLOR = "Blue Pt Tabby-White"

# 通常結果に現れてはならない語/表記。
# 注意:
#   - "Point" は "Lynx Point" / "Seal Point" 等も巻き込んで禁止 ("Pt"=Patched略記は別語で対象外)。
#   - A(タビー) を normal_mode で展開しないため、a/a 前提の Solid / Smoke / Tortie /
#     Calico / Tortoiseshell は通常結果に出ない (B/D 条件未明示の希釈トーティ Blue Cream/
#     Blue Tortie も同様に禁止)。Solid 単独色は test_all_colors_are_tabby_pattern で別途検出する。
#   - "Lilac"/"Chocolate"/"Cinnamon"/"Fawn" は B 座 (b/bl) 由来 = カテゴリCなので禁止。
FORBIDDEN_SUBSTRINGS = (
    "Mink",
    "Sepia",
    "Point",
    "Mitted",
    "Bi-Color",
    "Bi-C",
    "Van",
    "Champagne",
    "Platinum",
    "Sable",
    "Chocolate",
    "Cinnamon",
    "Lilac",
    "Fawn",
    "Choco",
    "Lynx Point",
    # a/a 前提 (A を normal_mode で展開しないため出ない)
    "Smoke",
    "Tortie",
    "Tortoiseshell",
    "Calico",
)

# オス結果に現れてはならないトーティ・クリーム混合・キャリコ系。
MALE_FORBIDDEN_SUBSTRINGS = (
    "Tortie",
    "Tortoiseshell",
    "Calico",
    "Blue Cream",
    "Lilac Cream",
)


@pytest.fixture(scope="module")
def report():
    calculator = CoatColorCalculator()
    return calculator.calculate_report(SIRE_COLOR, DAM_COLOR, breed=None)


def test_no_forbidden_colors_in_normal_mode(report) -> None:
    offenders = [
        (r.sex, r.color, token)
        for r in report.results
        for token in FORBIDDEN_SUBSTRINGS
        if token in r.color
    ]
    assert not offenders, f"通常結果に禁止カラーが含まれている: {offenders}"


def test_all_colors_are_tabby_pattern(report) -> None:
    """A を normal_mode で展開しないため、全出力はタビー/パッチドタビー系になる。

    Solid (Black/Blue/Red/Cream/Silver/Cameo 単独) や Smoke/Tortie/Calico/Tortoiseshell
    のような a/a 前提カラーは出てはならない。これらは "Tabby" を名前に含まないため、
    全出力が "Tabby" を含むことで検出する。
    """

    non_tabby = sorted({r.color for r in report.results if "Tabby" not in r.color})
    assert not non_tabby, f"タビー系でない (a/a前提の) カラーが出力されている: {non_tabby}"


def test_males_have_no_tortie_or_cream_mix(report) -> None:
    offenders = [
        (r.color, token)
        for r in report.results
        if r.sex == "Male"
        for token in MALE_FORBIDDEN_SUBSTRINGS
        if token in r.color
    ]
    assert not offenders, f"オス結果にメス限定カラーが含まれている: {offenders}"


def test_no_zero_or_negative_probabilities(report) -> None:
    bad = [(r.sex, r.color, r.probability_pct) for r in report.results if r.probability_pct <= 0]
    assert not bad, f"0%以下の項目が出力されている: {bad}"


def test_no_unmatched_genotypes(report) -> None:
    # 分類不能を捨てて再正規化していないこと = 未分類率がゼロであること
    assert report.unmatched_probability == 0, (
        f"未分類の遺伝子型が残っている: prob={report.unmatched_probability}, "
        f"samples={report.unmatched_samples}"
    )


def test_probabilities_sum_to_100(report) -> None:
    total = round(sum(r.probability_pct for r in report.results), 4)
    assert abs(total - 100.0) < 0.01, f"表示確率の合計が100%ではない: {total}"


def test_expected_direction_colors_present(report) -> None:
    """通常モードで現れるべき代表カラー (タビー/パッチドタビー系) を検証する。

    - 父 I/- (シルバー優性ヘテロ未確定) → 非シルバーの Brown 系
    - 父 D/- (濃色優性ヘテロ未確定) → 希釈の Blue 系・Blue Silver 系
    - 母 O/o → メスに Patched Tabby 系 (※ a/a 前提の Calico/Tortoiseshell ではない)
    A は展開しないため出力は全てタビー系。出力名は cat_color_master.csv で canonical 形
    (Pt→Patched) に正規化される。低確率でも分類が成立し方向性が出ることを確認する。
    """

    colors = {(r.sex, r.color) for r in report.results}
    expected_present = {
        ("Female", "Silver Tabby"),
        ("Male", "Silver Tabby"),
        ("Male", "Cameo Tabby"),
        ("Male", "Red Tabby"),
        ("Female", "Brown Tabby"),    # 父 I/i 由来 (非シルバー)
        ("Male", "Brown Tabby"),
        ("Female", "Blue Tabby"),      # 父 D/d 由来 (希釈)
        ("Female", "Blue Silver Tabby"),
        # 母 O/o 由来は Patched Tabby 系 (canonical 形: Pt→Patched)。
        ("Female", "Silver Patched Tabby"),
        ("Female", "Brown Patched Tabby"),   # 父 I/i + 母 O/o
        ("Female", "Blue Patched Tabby"),    # 父 D/d + 母 O/o
    }
    missing = expected_present - colors
    assert not missing, f"期待される方向性のカラーが欠落している: {missing}"
