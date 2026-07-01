"""毛色確率計算APIの回帰テスト。"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from cat_breeding_simulator.engine import BreedingCalculationError, CoatColorCalculator
from cat_breeding_simulator.color_master import COLOR_MASTER
from cat_breeding_simulator.display_alias_map import DISPLAY_ALIAS_MAP
from cat_breeding_simulator.master_data import COLOR_BASE_LOCI, BREED_FILTERS, COLOR_DEFINITIONS
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


def test_calculate_report_cache_not_poisoned_by_caller_mutation() -> None:
    """メモ化レポートを呼び出し側が破壊的変更しても、後続呼び出しが汚染されない。

    singleton 共有の calculator でキャッシュ実体を直接返すと、results 等の可変リストへの
    偶発的変更が以降のリクエストに波及する。返却時コピー (_copy_report) でこれを防ぐ。
    """

    calculator = CoatColorCalculator()
    first = calculator.calculate_report("Black", "Black")
    original_len = len(first.results)
    assert original_len > 0

    first.results.clear()  # 呼び出し側の偶発的な破壊的変更を模す

    second = calculator.calculate_report("Black", "Black")
    assert len(second.results) == original_len


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


def test_breed_specific_input_requires_matching_breed_context() -> None:
    """breed_specific 色は、猫種指定があっても文脈不一致なら拒否する。"""

    calculator = CoatColorCalculator()
    with pytest.raises(BreedingCalculationError):
        calculator.calculate("Ruddy", "Ruddy", breed="Persian")


def test_blue_silver_x_silver_patched_outputs_red_family_not_ruddy() -> None:
    """Blue Silver × Silver Patched Tabby の一般結果に Ruddy を混ぜない。"""

    calculator = CoatColorCalculator()
    report = calculator.calculate_report("Blue Silver", "Silver Patched Tabby")
    colors = _colors(report)
    assert "Ruddy" not in colors
    assert {"Cameo Tabby", "Red Tabby", "Cream Cameo Tabby", "Cream Tabby"} & colors
    assert report.unmatched_probability == 0


def test_display_map_van_normalized_to_white_in_general() -> None:
    """一般表示では Van を -White に正規化する (データ正本 §5.2)。"""

    assert DISPLAY_ALIAS_MAP.resolve_display_name("Black-White Van", None) == "Black-White"
    assert DISPLAY_ALIAS_MAP.resolve_display_name("Van Calico", None) == "Calico"
    assert DISPLAY_ALIAS_MAP.resolve_display_name("Dilute Calico Van", None) == "Dilute Calico"
    assert DISPLAY_ALIAS_MAP.resolve_display_name("Tortoiseshell-White Van", None) == "Calico"
    assert DISPLAY_ALIAS_MAP.resolve_display_name("Blue Cream-White Van", None) == "Dilute Calico"


def test_general_output_collapses_van_tortie_white_aliases() -> None:
    """一般結果では Van/トーティ白斑の alias を表示用 canonical 名へ寄せる。"""

    calculator = CoatColorCalculator()
    report = calculator.calculate_report("Black Smoke-White", "Blue Cream Point-White")
    colors = _colors(report)

    assert "Van Calico" not in colors
    assert "Blue Cream-White" not in colors
    assert "Calico" in colors
    assert "Dilute Calico" in colors
    assert report.unmatched_probability == 0


def test_display_map_breed_name_composes_with_white_suffix() -> None:
    """-White / -White Van 接尾辞を保ったまま基底名を猫種別呼称へ変換する。"""

    resolve = DISPLAY_ALIAS_MAP.resolve_display_name
    assert resolve("Brown Ticked Tabby-White", "Abyssinian") == "Ruddy-White"
    assert resolve("Black-White Van", "Oriental Shorthair") == "Ebony-White"
    # 未登録猫種は素通し
    assert resolve("Black", "Persian") == "Black"


def test_display_map_japanese_bobtail_mike_names() -> None:
    """Japanese Bobtail の三毛系を猫種固有呼称へ変換する。"""

    resolve = DISPLAY_ALIAS_MAP.resolve_display_name
    assert resolve("Calico", "Japanese Bobtail") == "Mike"
    assert resolve("Dilute Calico", "Japanese Bobtail") == "Dilute Mike"
    assert resolve("Tortie Smoke-White", "Japanese Bobtail") == "Smoke Mike"
    assert resolve("Blue Cream Smoke-White", "Japanese Bobtail") == "Dilute Smoke Mike"
    assert resolve("Calico", "Persian") == "Calico"


def test_display_map_tonkinese_solid_class_names() -> None:
    """Tonkinese 文脈では Sepia 側の内部名を Solid class 表示へ変換する。"""

    resolve = DISPLAY_ALIAS_MAP.resolve_display_name
    assert resolve("Sable", "Tonkinese") == "Natural Solid"
    assert resolve("Champagne", "Tonkinese") == "Champagne Solid"
    assert resolve("Platinum", "Tonkinese") == "Platinum Solid"
    assert resolve("Sable", "Burmese") == "Sable"


def test_display_map_burmese_blue_name() -> None:
    """Burmese 文脈では内部の Blue Solid を登録表示の Blue へ変換する。"""

    resolve = DISPLAY_ALIAS_MAP.resolve_display_name
    assert resolve("Blue Solid", "Burmese") == "Blue"
    assert resolve("Blue Solid", "Tonkinese") == "Blue Solid"


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


# --- 認定カラー (猫種で使える毛色) 関連 ---


def test_breed_incompatible_color_names_breed_and_color() -> None:
    """猫種の認定カラーに無い色を相手に指定 → 曖昧な汎用エラーでなく、毛色と猫種を名指す。"""

    response = client.post(
        "/api/v1/calculate",
        json={"sire_color": "Sable", "dam_color": "Black", "breed": "Burmese"},
    )
    assert response.status_code == 422
    detail = response.json()["detail"]
    # 矛盾相手の毛色 (Black) と猫種 (Burmese)、認定カラー文言を含む。
    assert "Black" in detail and "Burmese" in detail and "認定カラー" in detail


def test_breed_colors_endpoint_constrained() -> None:
    """制約を持つ猫種は使える毛色 (認定カラー) を返す。"""

    response = client.get("/api/v1/breed-colors", params={"breed": "Burmese"})
    assert response.status_code == 200
    body = response.json()
    assert body["constrained"] is True
    assert "Sable" in body["colors"]
    assert "Black" not in body["colors"]  # Black は Burmese 非対応


def test_breed_colors_endpoint_uses_policy_for_non_point_breeds() -> None:
    """猫種カラー方針がある猫種は、遺伝制約が無くても候補を方針で絞る。"""

    response = client.get("/api/v1/breed-colors", params={"breed": "American Shorthair"})
    assert response.status_code == 200
    body = response.json()
    assert body["constrained"] is True
    assert "Black" in body["colors"]
    assert "Seal Point" not in body["colors"]
    assert "Seal Point-White" not in body["colors"]


def test_breed_colors_endpoint_all_color_breed_stays_unconstrained() -> None:
    """オールカラー猫種は constrained=false / colors=[] で全候補表示を維持する。"""

    response = client.get("/api/v1/breed-colors", params={"breed": "Cornish Rex"})
    assert response.status_code == 200
    body = response.json()
    assert body["constrained"] is False
    assert body["colors"] == []


def test_breed_colors_endpoint_point_white_policy() -> None:
    """Birman は一般の Point-White 系を候補にし、Ragdoll 固有呼称を混ぜない。"""

    response = client.get("/api/v1/breed-colors", params={"breed": "Birman"})
    assert response.status_code == 200
    body = response.json()
    assert body["constrained"] is True
    assert "Seal Point-White" in body["colors"]
    assert "Seal Point" not in body["colors"]
    assert "Seal Point Bi-Color" not in body["colors"]
    assert "Seal Point Mitted" not in body["colors"]


def test_breed_colors_endpoint_ragdoll_point_variants() -> None:
    """Ragdoll は通常 Point と Bi-Color / Mitted 系を猫種候補に含める。"""

    response = client.get("/api/v1/breed-colors", params={"breed": "Ragdoll"})
    assert response.status_code == 200
    body = response.json()
    assert body["constrained"] is True
    assert "Seal Point" in body["colors"]
    assert "Seal Point Bi-Color" in body["colors"]
    assert "Seal Point Mitted" in body["colors"]
    assert "Seal Point-White" not in body["colors"]


def test_breed_colors_endpoint_snowshoe_point_variants() -> None:
    """Snowshoe は Point Bi-Color / Point Mitted 系を猫種候補にする。"""

    response = client.get("/api/v1/breed-colors", params={"breed": "Snowshoe"})
    assert response.status_code == 200
    body = response.json()
    assert body["constrained"] is True
    assert "Seal Point Bi-Color" in body["colors"]
    assert "Seal Point Mitted" in body["colors"]
    assert "Seal Point-White" not in body["colors"]


def test_snowshoe_fixed_c_locus_without_fixed_s_locus() -> None:
    """Snowshoe は C座位を cs/cs 固定し、S座位は表現型から読むため猫種全体では固定しない。"""

    assert BREED_FILTERS["Snowshoe"].get("C") == ("cs", "cs")
    assert "S" not in BREED_FILTERS["Snowshoe"]


def test_snowshoe_rejects_full_color_parent() -> None:
    """Snowshoe にフルカラー親を指定した場合、ポイント固定に反するため認定カラー外で弾く。"""

    response = client.post(
        "/api/v1/calculate",
        json={"sire_color": "Black", "dam_color": "Black", "breed": "Snowshoe"},
    )
    assert response.status_code == 422
    detail = response.json()["detail"]
    assert "Black" in detail and "Snowshoe" in detail and "認定カラー" in detail


def _tonkinese_class_totals(results: list[dict[str, object]]) -> dict[str, float]:
    """Tonkinese の Point/Mink/Solid class 別に確率を集計する。"""

    totals = {"point": 0.0, "mink": 0.0, "solid": 0.0}
    for result in results:
        color = str(result["color"])
        probability = float(result["probability_pct"])
        if "Mink" in color:
            totals["mink"] += probability
        elif "Point" in color:
            totals["point"] += probability
        elif "Solid" in color:
            totals["solid"] += probability
    return totals


def test_tonkinese_has_class_based_c_locus_without_breed_wide_c_filter() -> None:
    """Tonkinese は breed 全体を C=cb/cs 固定せず、色クラスから C座位を読む。"""

    assert "C" not in BREED_FILTERS["Tonkinese"]
    breeds = {breed["value"]: breed for breed in client.get("/api/v1/breeds").json()["breeds"]}
    assert breeds["Tonkinese"]["affects_genetics"] is True


def test_tonkinese_accepts_point_mink_solid_classes_and_rejects_full_color() -> None:
    """Tonkinese は Point/Mink/Solid class を受け、通常フルカラーは認定カラー外で弾く。"""

    tonkinese_colors = (
        "Natural Point",
        "Natural Mink",
        "Natural Solid",
        "Blue Point",
        "Blue Mink",
        "Blue Solid",
        "Champagne Point",
        "Champagne Mink",
        "Champagne Solid",
        "Platinum Point",
        "Platinum Mink",
        "Platinum Solid",
    )
    for color in tonkinese_colors:
        response = client.post(
            "/api/v1/calculate",
            json={"sire_color": color, "dam_color": color, "breed": "Tonkinese"},
        )
        assert response.status_code == 200, response.json()

    rejected = client.post(
        "/api/v1/calculate",
        json={"sire_color": "Black", "dam_color": "Black", "breed": "Tonkinese"},
    )
    assert rejected.status_code == 422
    detail = rejected.json()["detail"]
    assert "Black" in detail and "Tonkinese" in detail and "認定カラー" in detail


def test_tonkinese_point_by_solid_produces_only_mink_class() -> None:
    """Tonkinese の Point(cs/cs) × Solid(cb/cb) は C座位上 100% Mink(cb/cs)。"""

    response = client.post(
        "/api/v1/calculate",
        json={
            "sire_color": "Natural Point",
            "dam_color": "Natural Solid",
            "breed": "Tonkinese",
        },
    )
    assert response.status_code == 200
    results = response.json()["results"]
    assert results
    totals = _tonkinese_class_totals(results)
    assert totals["mink"] == pytest.approx(100.0, abs=0.02)
    assert totals["point"] == pytest.approx(0.0, abs=0.02)
    assert totals["solid"] == pytest.approx(0.0, abs=0.02)


def test_tonkinese_platinum_point_by_solid_produces_platinum_mink() -> None:
    """Tonkinese の Platinum Point × Platinum Solid は Platinum Mink だけになる。"""

    response = client.post(
        "/api/v1/calculate",
        json={
            "sire_color": "Platinum Point",
            "dam_color": "Platinum Solid",
            "breed": "Tonkinese",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["diagnostics"]["unmatched_probability"] == 0
    colors = {str(result["color"]) for result in body["results"]}
    assert colors == {"Platinum Mink"}


def test_tonkinese_mink_by_mink_splits_point_mink_solid_classes() -> None:
    """Tonkinese の Mink(cb/cs) × Mink(cb/cs) は 25/50/25 に分離する。"""

    response = client.post(
        "/api/v1/calculate",
        json={
            "sire_color": "Natural Mink",
            "dam_color": "Natural Mink",
            "breed": "Tonkinese",
        },
    )
    assert response.status_code == 200
    results = response.json()["results"]
    totals = _tonkinese_class_totals(results)
    assert totals["point"] == pytest.approx(25.0, abs=0.02)
    assert totals["mink"] == pytest.approx(50.0, abs=0.02)
    assert totals["solid"] == pytest.approx(25.0, abs=0.02)

    colors = {str(result["color"]) for result in results}
    assert "Natural Solid" in colors
    assert "Sable" not in colors
    assert "Platinum" not in colors


def test_breed_colors_endpoint_unknown_breed_returns_422() -> None:
    """未対応の猫種は /calculate と同様に 422 で弾く (API 間の挙動を揃える)。"""

    response = client.get("/api/v1/breed-colors", params={"breed": "ドラゴン"})
    assert response.status_code == 422
    assert "未対応の猫種" in response.json()["detail"]


def test_golden_locus_data_contract() -> None:
    """Golden 系は V9 正本どおり non_silver + agouti + Wb/tipping として保持する。"""

    wrong: list[tuple[str, dict[str, tuple[str, str]]]] = []
    for name, bases in COLOR_BASE_LOCI.items():
        if "Golden" not in name:
            continue
        for base in bases:
            autosomal = base.autosomal
            if (
                autosomal.get("A") != ("A", "A")
                or autosomal.get("I") != ("i", "i")
                or autosomal.get("Wb") != ("Wb", "Wb")
            ):
                wrong.append((name, autosomal))

    assert not wrong, f"Golden 系なのに A/A + i/i + Wb/Wb でない行: {wrong}"


def test_cream_tortie_o_locus_data_contract() -> None:
    """Blue/Lilac/Chocolate Cream 系はトーティ表現なので O/o として保持する。"""

    tortie_cream_markers = ("Blue Cream", "Lilac Cream", "Choco Cream", "Chocolate Cream")
    wrong: list[tuple[str, tuple[str, str]]] = []
    for name, bases in COLOR_BASE_LOCI.items():
        if not any(marker in name for marker in tortie_cream_markers):
            continue
        for base in bases:
            if base.o != ("O", "o"):
                wrong.append((name, base.o))

    assert not wrong, f"Cream 系トーティ名なのに O/o でない行: {wrong}"


def test_white_spotting_locus_data_contract() -> None:
    """白斑名は V9 正本どおり -White=S/s、Van=S/S として保持する。"""

    bicolor_markers = ("-White", "-W", " Bi-Color", " Bi-C", " Mitted")
    wrong_bicolor: list[tuple[str, tuple[str, str] | None]] = []
    wrong_van: list[tuple[str, tuple[str, str] | None]] = []
    for name, bases in COLOR_BASE_LOCI.items():
        is_van = " Van" in name
        is_bicolor = any(marker in name for marker in bicolor_markers)
        if not is_van and not is_bicolor:
            continue
        for base in bases:
            s_locus = base.autosomal.get("S")
            if is_van:
                if s_locus != ("S", "S"):
                    wrong_van.append((name, s_locus))
            elif s_locus != ("S", "s"):
                wrong_bicolor.append((name, s_locus))

    assert not wrong_bicolor, f"-White/-W/Bi-Color/Mitted 名なのに S/s でない行: {wrong_bicolor}"
    assert not wrong_van, f"Van 名なのに S/S でない行: {wrong_van}"


@pytest.mark.parametrize(
    "color_name",
    [
        "Blue Chinchilla Golden-White",
        "Blue Chinchilla Silver-White",
        "Blue Golden",
        "Blue Golden-White",
        "Blue Shaded Golden-White",
        "Blue Shaded Silver-White",
    ],
)
def test_tipping_fallback_outputs_exist_in_master(color_name: str) -> None:
    """Wb/tipping fallback が出す汎用名は master で通常表示できる。"""

    resolved = COLOR_MASTER.resolve(color_name)
    assert resolved is not None
    assert resolved.primary_name == color_name
    assert resolved.display_allowed is True
    assert resolved.input_allowed is True


@pytest.mark.parametrize(
    "color_name",
    [
        "Chocolate Tabby-White",
        "Chocolate Silver Tabby-White",
        "Lilac Silver Tabby",
        "Chocolate Silver Patched Tabby",
        "Chocolate Silver Patched Tabby-White",
        "Lilac Patched Tabby-White",
        "Lilac Silver Patched Tabby",
        "Lilac Silver Patched Tabby-White",
    ],
)
def test_chocolate_lilac_fallback_outputs_exist_in_master(color_name: str) -> None:
    """Chocolate/Lilac 系 fallback が出す標準名は master で通常表示できる。"""

    resolved = COLOR_MASTER.resolve(color_name)
    assert resolved is not None
    assert resolved.primary_name == color_name
    assert resolved.display_allowed is True
    assert resolved.input_allowed is True


def test_point_white_fallback_output_exists_in_master_but_not_general_display() -> None:
    """Point-White 補完名は入力可だが、一般候補としては常時表示しない。"""

    resolved = COLOR_MASTER.resolve("Cream Lynx Point-White")
    assert resolved is not None
    assert resolved.primary_name == "Cream Lynx Point-White"
    assert resolved.display_allowed is False
    assert resolved.input_allowed is True


@pytest.mark.parametrize(
    "color_name",
    [
        "Blue Silver Lynx Point",
        "Blue Silver Lynx Point-White",
        "Silver Lynx Point-White",
        "Lilac Lynx Point-White",
        "Blue Silver Cream Lynx Point",
        "Silver Tortie Lynx Point",
        "Blue Silver Cream Lynx Point-White",
        "Chocolate Silver Lynx Point",
        "Lilac Silver Lynx Point",
        "Lilac Silver Lynx Point-White",
        "Blue Shaded Golden Lynx Point",
        "Blue Shaded Golden Lynx Point-White",
        "Blue Shaded Silver Lynx Point",
        "Blue Shaded Silver Lynx Point-White",
        "Shaded Golden Lynx Point",
        "Shaded Golden Lynx Point-White",
        "Shaded Silver Lynx Point",
        "Shaded Silver Lynx Point-White",
        "Silver Tortie Lynx Point-White",
        "Chocolate Silver Tortie Lynx Point-White",
        "Lilac Silver Cream Lynx Point",
        "Lilac Silver Cream Lynx Point-White",
        "Lilac Cream Lynx Point-White",
        "Chocolate Tortie Point-White",
    ],
)
def test_point_audit_outputs_exist_in_master_but_not_general_display(color_name: str) -> None:
    """監査で出る Point 系補完名は入力可だが、一般候補としては常時表示しない。"""

    resolved = COLOR_MASTER.resolve(color_name)
    assert resolved is not None
    assert resolved.primary_name == color_name
    assert resolved.display_allowed is False
    assert resolved.input_allowed is True


@pytest.mark.parametrize("color_name", ["Lilac Cream-White", "Chocolate Tortie-White"])
def test_tortie_white_fallback_outputs_exist_in_master(color_name: str) -> None:
    """非Pointのトーティ白斑補完名は master で通常表示できる。"""

    resolved = COLOR_MASTER.resolve(color_name)
    assert resolved is not None
    assert resolved.primary_name == color_name
    assert resolved.display_allowed is True
    assert resolved.input_allowed is True


# --- Sp (スポテッド) 座位: 座位マスタ正本 V9 §5.11 / §7 Phase B ---


def test_sp_locus_data_contract() -> None:
    """Sp_Locus 列がデータに正しく載っている (CSV 退行検知)。

    スポット色行は Sp/Sp、非スポット色行は sp/sp。猫種は Egyptian Mau・Ocicat のみ
    Sp/Sp 固定で、Bengal は固定しない (マーブル個体を残すため)。
    """

    assert COLOR_BASE_LOCI["Brown Spotted Tabby"][0].autosomal["Sp"] == ("Sp", "Sp")
    assert COLOR_BASE_LOCI["Brown Tabby"][0].autosomal["Sp"] == ("sp", "sp")
    assert BREED_FILTERS["Egyptian Mau"].get("Sp") == ("Sp", "Sp")
    assert BREED_FILTERS["Ocicat"].get("Sp") == ("Sp", "Sp")
    assert "Sp" not in BREED_FILTERS["Bengal"]

    # 不変条件: 名前がスポット (full "Spotted" または略記 "Sp" トークン) の色行は
    # 全て Sp/Sp でなければならない。"Sp Tabby-White" / "Pt Sp Tabby" 等の略記漏れを検知する。
    def _is_spotted_name(name: str) -> bool:
        tokens = name.replace("-", " ").split()
        return "Spotted" in tokens or "Sp" in tokens

    wrong = [
        name
        for name, bases in COLOR_BASE_LOCI.items()
        if _is_spotted_name(name)
        for base in bases
        if base.autosomal.get("Sp") != ("Sp", "Sp")
    ]
    assert not wrong, f"スポット名なのに Sp_Locus が Sp/Sp でない行: {wrong}"


def test_spotted_breed_keeps_spotted_in_output() -> None:
    """Egyptian Mau のスポット交配は出力の柄に Spotted を保持する。"""

    response = client.post(
        "/api/v1/calculate",
        json={
            "sire_color": "Brown Spotted Tabby",
            "dam_color": "Brown Spotted Tabby",
            "breed": "Egyptian Mau",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["results"]
    assert all("Spotted" in result["color"] for result in payload["results"])


def test_spotted_fixed_breed_rejects_non_spotted_color() -> None:
    """Sp/Sp 固定猫種 (Egyptian Mau) に非スポット色を指定 → 認定カラー外として弾く。"""

    response = client.post(
        "/api/v1/calculate",
        json={
            "sire_color": "Brown Tabby",
            "dam_color": "Brown Tabby",
            "breed": "Egyptian Mau",
        },
    )
    assert response.status_code == 422
    detail = response.json()["detail"]
    assert "Egyptian Mau" in detail and "認定カラー" in detail


def test_unfixed_breed_allows_non_spotted_color() -> None:
    """Sp を固定しない猫種 (Bengal) は非スポット色も受け付ける (マーブル個体を排除しない)。"""

    response = client.post(
        "/api/v1/calculate",
        json={
            "sire_color": "Brown Tabby",
            "dam_color": "Brown Tabby",
            "breed": "Bengal",
        },
    )
    assert response.status_code == 200
    assert response.json()["results"]


def test_spotted_propagates_by_phenotype_without_breed() -> None:
    """猫種無指定でも、表現された親 (Spotted) から子へスポットが伝播する (express-then-infer)。"""

    response = client.post(
        "/api/v1/calculate",
        json={"sire_color": "Brown Spotted Tabby", "dam_color": "Brown Tabby"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert any("Spotted" in result["color"] for result in payload["results"])


# --- Classic タビー (mc/mc) 追加 / Oriental 基底名の canonical 化 ---


def test_classic_tabby_inputtable_and_named() -> None:
    """Classic タビー (mc/mc) が入力可能で、出力の柄に Classic を保持する。

    mc/mc × mc/mc は不可逆で Mc/- を生まないため、子は全て Classic タビーになる。
    """

    response = client.post(
        "/api/v1/calculate",
        json={"sire_color": "Brown Classic Tabby", "dam_color": "Brown Classic Tabby"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["results"]
    assert all("Classic" in result["color"] for result in payload["results"])


def test_oriental_tabby_names_canonicalize_to_general() -> None:
    """Oriental 基底名 (Lavender/Ebony/Chestnut のタビー変種) が一般 canonical へ正規化される。

    黒系タビーの canonical は Brown Tabby (アグーチ黒=ブラウン)。
    """

    assert COLOR_MASTER.canonical_name("Lavender Tabby") == "Lilac Tabby"
    assert COLOR_MASTER.canonical_name("Ebony Tabby") == "Brown Tabby"
    assert COLOR_MASTER.canonical_name("Chestnut Tabby") == "Chocolate Tabby"
    assert COLOR_MASTER.canonical_name("Lavender Patched Tabby") == "Lilac Patched Tabby"


def test_oriental_display_restores_breed_name_for_tabby() -> None:
    """一般 canonical 化した色も、Oriental 文脈では猫種固有名で表示する。"""

    canonical = COLOR_MASTER.canonical_name("Chestnut Tabby")  # -> Chocolate Tabby
    assert DISPLAY_ALIAS_MAP.resolve_display_name(canonical, None) == "Chocolate Tabby"
    assert DISPLAY_ALIAS_MAP.resolve_display_name(canonical, "Oriental") == "Chestnut Tabby"
