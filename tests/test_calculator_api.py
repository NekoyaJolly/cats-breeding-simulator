"""毛色確率計算APIの回帰テスト。"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from cat_breeding_simulator.engine import BreedingCalculationError, CoatColorCalculator
from cat_breeding_simulator.color_master import COLOR_MASTER
from cat_breeding_simulator.display_alias_map import DISPLAY_ALIAS_MAP
from cat_breeding_simulator.master_data import COLOR_DEFINITIONS
from main import app


client = TestClient(app)


# カラー名 -> その正規遺伝子型の D_Locus 集合 (CSV 参照)。
# 同名で複数行あり得るため集合で保持する。
_D_LOCUS_BY_COLOR: dict[str, set[str]] = {}
for _definition in COLOR_DEFINITIONS:
    _D_LOCUS_BY_COLOR.setdefault(_definition["CoatColor"], set()).add(
        _definition.get("D_Locus", "").strip()
    )


@pytest.mark.parametrize(
    "sire_color, dam_color",
    [
        # 両親とも d/d (希釈・劣性ホモ)。子は必ず d/d にしかならない。
        ("Cream Tabby-White", "Dilute Calico"),
        ("Blue", "Blue"),
        ("Blue Tabby", "Cream Tabby"),
    ],
)
def test_dilute_parents_never_produce_dense_offspring(sire_color: str, dam_color: str) -> None:
    """希釈の不可逆性 (絶対ルール): d/d × d/d からは濃色 (D_) の子は生まれない。

    例) Cream Tabby-White (d/d) × Dilute Calico (d/d) で、濃色の "Calico" (D/D) は
    遺伝的に生成され得ず、"Dilute Calico" (d/d) のみが正しい。
    """

    calculator = CoatColorCalculator()
    report = calculator.calculate_report(sire_color, dam_color, breed=None)

    dense = [
        (result.sex, result.color, sorted(_D_LOCUS_BY_COLOR.get(result.color, set())))
        for result in report.results
        if any("D" in d_locus for d_locus in _D_LOCUS_BY_COLOR.get(result.color, set()))
    ]
    assert not dense, f"希釈親同士から濃色の子が出力された (不可逆ルール違反): {dense}"
    assert report.unmatched_probability == 0


def test_breed_filter_enforces_siamese_point_genotypes() -> None:
    response = client.post(
        "/api/v1/calculate",
        json={"sire_color": "Seal Point", "dam_color": "Seal Point", "breed": "Siamese"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["results"]
    assert all("Point" in result["color"] for result in payload["results"])


def test_invalid_sex_specific_color_returns_422() -> None:
    response = client.post(
        "/api/v1/calculate",
        json={"sire_color": "Calico", "dam_color": "Black"},
    )

    assert response.status_code == 422
    detail = response.json()["detail"]
    # メス限定色 (Calico) を父猫に指定 → 日本語で「父猫には指定できない」旨を返す。
    assert "父猫" in detail and "指定できません" in detail


# --- cat_color_master.csv 名前正規化レイヤの回帰テスト ---


def test_master_resolves_alias_to_canonical() -> None:
    """dilute トーティは Cream を正規名にする (Blue Cream が canonical / Blue Tortie が alias)。"""

    # Blue Cream が canonical 概念。
    cream = COLOR_MASTER.resolve("Blue Cream")
    assert cream is not None
    assert cream.status == "canonical"
    assert cream.primary_name == "Blue Cream"

    # Blue Tortie は alias として同じ概念 (blue_cream) へ解決し、表示名は Blue Cream になる。
    tortie = COLOR_MASTER.resolve("Blue Tortie")
    assert tortie is not None
    assert tortie.status == "alias"
    assert tortie.canonical_color_id == "blue_cream"
    assert tortie.primary_name == "Blue Cream"


def test_output_color_names_are_canonical() -> None:
    """出力色名は canonical 形へ正規化される (略記 Pt は残らず Patched になる)。"""

    calculator = CoatColorCalculator()
    report = calculator.calculate_report("Silver Tabby", "Blue Pt Tabby-White", breed=None)
    colors = {result.color for result in report.results}

    assert "Silver Patched Tabby" in colors
    # 略記 "Pt" を単語として含む出力が残っていないこと
    assert not [c for c in colors if "Pt" in c.split()], f"略記 Pt が残存: {colors}"
    # 合計100% / 未分類ゼロは維持
    assert report.unmatched_probability == 0
    assert abs(round(sum(r.probability_pct for r in report.results), 4) - 100.0) < 0.01


def test_alias_female_color_is_usable_as_dam() -> None:
    """alias 名 (Blue Cream) を母に指定しても canonical 解決され計算できる。"""

    calculator = CoatColorCalculator()
    report = calculator.calculate_report("Black", "Blue Cream", breed=None)
    assert report.results
    assert report.unmatched_probability == 0


def test_breed_specific_input_rejected_in_normal_mode() -> None:
    """breed_specific 色 (Sable=Burmese) は猫種未指定の通常モードでは拒否される。"""

    calculator = CoatColorCalculator()
    with pytest.raises(BreedingCalculationError):
        calculator.calculate("Sable", "Black", breed=None)


def test_excluded_input_rejected() -> None:
    """excluded 色 (Smoke 単独) は入力色として拒否される。"""

    calculator = CoatColorCalculator()
    with pytest.raises(BreedingCalculationError):
        calculator.calculate("Smoke", "Black", breed=None)


# --- cat_color_display_alias_map.csv 表示名解決レイヤの回帰テスト ---
#
# 猫種別表示名 (Oriental の Ebony/Chestnut/Lavender、Abyssinian/Somali の Ruddy 等) と
# 一般表示の Van -> -White 正規化 (データ正本 §4 / §5.2) を検証する。
# 統合方針: engine.py のハードコードを CSV 駆動へ置換 (§1.1)。


def _colors(report) -> set[str]:
    return {result.color for result in report.results}


def test_oriental_restores_breed_specific_names() -> None:
    """Oriental 文脈で Black/Chocolate/Lilac が Ebony/Chestnut/Lavender へ復元される。"""

    calculator = CoatColorCalculator()
    # Chestnut (=Chocolate) 同士。濃色の子は Chestnut、希釈の子は Lavender (=Lilac) になる。
    report = calculator.calculate_report("Chestnut", "Chestnut", breed="Oriental Shorthair")
    colors = _colors(report)
    assert "Chestnut" in colors
    assert "Lavender" in colors
    # 一般名 (Chocolate/Lilac) が Oriental 文脈で残らない
    assert "Chocolate" not in colors and "Lilac" not in colors
    assert report.unmatched_probability == 0


def test_oriental_ebony_from_alias_input() -> None:
    """alias 入力 Ebony は canonical(Black) 解決後、Oriental 文脈で Ebony 表示に戻る。"""

    calculator = CoatColorCalculator()
    report = calculator.calculate_report("Ebony", "Ebony", breed="Oriental Longhair")
    colors = _colors(report)
    assert "Ebony" in colors
    assert "Black" not in colors


def test_general_display_keeps_canonical_not_breed_name() -> None:
    """猫種未指定の一般表示では猫種別呼称 (Ebony 等) を出さず canonical(Black) のまま。"""

    calculator = CoatColorCalculator()
    report = calculator.calculate_report("Black", "Black", breed=None)
    colors = _colors(report)
    assert "Black" in colors
    assert "Ebony" not in colors


def test_abyssinian_ruddy_preserved() -> None:
    """Abyssinian/Somali の Ruddy 表示が CSV 駆動でも保持される (置換前と同一)。"""

    calculator = CoatColorCalculator()
    for breed in ("Abyssinian", "Somali"):
        report = calculator.calculate_report("Ruddy", "Ruddy", breed=breed)
        colors = _colors(report)
        assert "Ruddy" in colors, f"{breed} で Ruddy が出力されない: {colors}"


def test_display_map_van_normalized_to_white_in_general() -> None:
    """一般表示では Van を -White に正規化する (データ正本 §5.2)。"""

    assert DISPLAY_ALIAS_MAP.resolve_display_name("Black-White Van", None) == "Black-White"
    assert (
        DISPLAY_ALIAS_MAP.resolve_display_name("Tortoiseshell-White Van", None)
        == "Tortoiseshell-White"
    )


def test_display_map_breed_name_composes_with_white_suffix() -> None:
    """-White / -White Van 接尾辞を保ったまま基底名を猫種別呼称へ変換する。"""

    resolve = DISPLAY_ALIAS_MAP.resolve_display_name
    assert resolve("Brown Ticked Tabby-White", "Abyssinian") == "Ruddy-White"
    assert resolve("Black-White Van", "Oriental Shorthair") == "Ebony-White"
    # 未登録猫種は素通し
    assert resolve("Black", "Persian") == "Black"


def test_ui_path_130x204_only_tabby_via_api() -> None:
    """UI 経路 (API → ColorNameResolver 経由) で 130×204 を計算し、出力健全性を検証する。

    A を normal_mode で展開しないため、全出力はタビー/パッチドタビー系 (Solid/Smoke/
    Tortie/Calico は出ない)。出力名は canonical 形 (Pt→Patched)。合計は 100%。
    """

    # 猫種は指定しない (この経路は猫種非依存。以前は breed="Any" を黙って無視させていたが、
    # 未対応猫種はバリデーションで弾くようになったため breed を省略する)。
    response = client.post(
        "/api/v1/calculate",
        json={"sire_color": "Silver Tabby", "dam_color": "Blue Pt Tabby-White"},
    )
    assert response.status_code == 200
    results = response.json()["results"]
    assert results

    colors = {r["color"] for r in results}
    # 全出力がタビー系 (a/a 前提の Solid/Smoke/Tortie/Calico が無い)
    non_tabby = sorted(c for c in colors if "Tabby" not in c)
    assert not non_tabby, f"UI経路で非タビー系が出力された: {non_tabby}"
    # 出力名は canonical 形 (略記 Pt が単語として残らない)
    assert not [c for c in colors if "Pt" in c.split()]
    # 母 O/o 由来の Patched Tabby が出る
    assert "Silver Patched Tabby" in colors
    # 合計100%
    total = round(sum(r["probability_pct"] for r in results), 4)
    assert abs(total - 100.0) < 0.01, f"合計が100%でない: {total}"
