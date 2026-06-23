"""130 (Silver Tabby) x 204 (Blue Pt Tabby-White) 通常計算の出力健全性テスト。

通常モードでは「優性表現型のヘテロ未確定ルール」に従い、表現されている優性形質は
X/- = {X/X, X/x} として扱う。よって父 Silver Tabby は I/-(シルバー)・D/-(濃色)・A/-(タビー)
となり、子には Brown 系 (父 I/i)・Blue 系 (父 D/d)・パッチド系 (母 O/o) が正しく出る。

一方、表現型から要求されない潜在キャリア (B/b チョコ, B/bl シナモン, C/cs ポイント,
C/cb セピア) は通常モードでは展開しない。本テストは、これらカテゴリC由来の文脈外カラーが
出ないこと・オス禁止ルール・0%禁止・未分類ゼロ・合計100% を回帰検証する。

明示キャリアモードや猫種指定モードでは別の許容範囲となるため、本テストとは分離する。
"""

from __future__ import annotations

import pytest

from cat_breeding_simulator.engine import CoatColorCalculator

# 父 130 / 母 204 から解決されるカラー名
SIRE_COLOR = "Silver Tabby"
DAM_COLOR = "Blue Pt Tabby-White"

# 通常結果に現れてはならない、潜在キャリア (カテゴリC) 由来の語/表記。
# 注意:
#   - "Point" は "Lynx Point" / "Seal Point" 等も巻き込んで禁止 ("Pt"=Patched略記は別語で対象外)。
#   - "Blue Cream" は禁止に含めない。希釈トーティ (d/d) のメスは正当な通常結果であり、
#     父が D/- (濃色ヘテロ未確定) のため希釈系が出るのは正しい。オスのみ別途禁止する。
#   - "Lilac"/"Lilac Cream"/"Chocolate"/"Cinnamon"/"Fawn" は B 座 (b/bl) 由来 = カテゴリCなので禁止。
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
    "Lilac Cream",
    "Choco",
    "Lynx Point",
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
    """優性表現型のヘテロ未確定ルールにより現れるべき代表カラーを検証する。

    - 父 I/- (シルバー優性ヘテロ未確定) → 非シルバーの Brown 系・Calico・Tortoiseshell
    - 父 D/- (濃色優性ヘテロ未確定) → 希釈の Blue 系・Blue Silver 系
    - 父 A/- (タビー優性ヘテロ未確定) → ソリッド系
    - 母 O/o → メスにパッチド (Pt) 系
    低確率でも分類が成立し、これらの方向性が出ることを確認する。
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
        ("Female", "Silver Pt Tabby"),  # 母 O/o 由来 (パッチド)
        ("Female", "Calico"),
        ("Female", "Tortoiseshell"),
    }
    missing = expected_present - colors
    assert not missing, f"期待される方向性のカラーが欠落している: {missing}"
