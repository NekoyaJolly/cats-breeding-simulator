"""往復整合ゲート (Gate 1 / 正確性ゲート)。

順方向 (教科書照合済み＝test_mendelian_loci で担保) を「真実の錨」とし、逆引き・リター推定の
主張が順方向の実出力と矛盾しないことを機械で保証する。あわせて White (優性白) の順方向
(§2.1/§2.2)・リター推定 (§3 R2a/R2b) の「あるべき値」と、リター専用期待値 (§4.3 R1) を固定する。

既存の golden / 130x204 / mendelian を壊さないこと (それらは別ファイルで常時グリーン)。

構成:
  - REPRESENTATIVE_CASES: §4.1 の代表12ケース。軸1(1-7)=順方向の網羅、軸2(8-12)=逆モードが転ぶ所。
  - 契約1 (test_reverse_lookup_roundtrips_to_forward): 逆引き候補を順方向に戻すと目標が出る & %整合。
  - 契約2 (test_litter_inference_roundtrips_to_forward): リター推定の親を順方向に戻すと全子猫が出る。
  - 契約3 (test_reverse_lookup_negative_matches_forward): 逆引きで出ない → 順方向でも0%。
  - White 順方向/リター推定の期待値固定 (WHITE-2 / WHITE-3)。
  - GATE-2: リター専用期待値 (§4.3 R1 現状 / §3 R2 修正後)。
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from cat_breeding_simulator.color_master import COLOR_MASTER
from cat_breeding_simulator.engine import CoatColorCalculator
from cat_breeding_simulator.litter_inference import (
    LitterInferenceService,
    LitterParent,
    ObservedKitten,
)
from main import app

client = TestClient(app)

# 契約2 のリター往復はサービス内部 (surviving_pairs) を使うため、テスト専用の実体を持つ。
_CALCULATOR = CoatColorCalculator()
_LITTER_SERVICE = LitterInferenceService(_CALCULATOR)


# --- §4.1 代表12ケース (target は無ければ None) --------------------------------
# (No, target, sire, dam, breed)。軸1(1-7): 表現型を広く突く順方向の審判。
# 軸2(8-12): 見た目が遺伝子型を隠す/複対立/確定土台/優性W/伴性I。
REPRESENTATIVE_CASES: list[tuple[int, str | None, str, str, str | None]] = [
    (1, None, "Shaded Silver", "Chinchilla Golden", None),
    (2, None, "Red Tabby-White", "Brown Patched Tabby", None),
    (3, None, "Blue Point Mitted", "Seal Point Bi-Color", "Ragdoll"),
    (4, None, "Red Mackerel Tabby-White", "Blue Patched Tabby", None),
    (5, "Blue Tabby", "Cream Tabby-White", "Lilac Tabby", None),
    (6, None, "Blue Chinchilla Golden", "Shell Cameo", None),
    (7, None, "Blue Tabby-White", "Dilute Calico", None),
    (8, "Black", "Black", "Black", None),
    (9, "Natural Mink", "Natural Mink", "Natural Mink", "Tonkinese"),
    (10, "Black", "Cinnamon", "Black", None),
    (11, "White", "White", "Black", None),
    (12, "Cameo", "Black Smoke", "Red", None),
]


# --- 低レベルヘルパー ----------------------------------------------------------


def _calculate(sire: str, dam: str, breed: str | None = None) -> list[dict[str, object]]:
    """順方向 (normal) 計算を API で実行し、結果行を返す (審判)。"""

    payload: dict[str, object] = {"sire_color": sire, "dam_color": dam, "mode": "normal"}
    if breed:
        payload["breed"] = breed
    response = client.post("/api/v1/calculate", json=payload)
    assert response.status_code == 200, response.text
    return response.json()["results"]


def _forward_probability_of(
    results: list[dict[str, object]], target: str, target_sex: str | None = None
) -> float:
    """順方向結果の中で、目標カラー (任意で性別) の確率合計を返す。"""

    target_names = {target, COLOR_MASTER.canonical_name(target)}
    expected_sex = None if target_sex is None else ("Male" if target_sex == "male" else "Female")
    total = 0.0
    for entry in results:
        if expected_sex is not None and entry["sex"] != expected_sex:
            continue
        names = {entry["color"], COLOR_MASTER.canonical_name(str(entry["color"]))}
        if target_names & names:
            total += float(entry["probability_pct"])
    return round(total, 4)


def _reverse_lookup(
    target: str, cats: list[dict[str, object]], target_sex: str | None = None
) -> dict[str, object] | None:
    """逆引き API を実行し、最上位候補 (無ければ None) を返す。"""

    payload: dict[str, object] = {"target_color": target, "cats": cats}
    if target_sex:
        payload["target_sex"] = target_sex
    response = client.post("/api/v1/reverse-lookup", json=payload)
    assert response.status_code == 200, response.text
    candidates = response.json()["candidates"]
    return candidates[0] if candidates else None


def _cats(entries: list[tuple[str, str, str | None]]) -> list[dict[str, object]]:
    """(sex, color, breed) のタプル列を逆引き API 入力の登録猫へ変換する。"""

    cats: list[dict[str, object]] = []
    for index, (sex, color, breed) in enumerate(entries):
        cat: dict[str, object] = {
            "id": f"cat-{index}",
            "name": f"{color}-{sex}",
            "sex": sex,
            "color": color,
        }
        if breed:
            cat["breed"] = breed
        cats.append(cat)
    return cats


def _litter_inference(
    sire: str, dam: str, breed: str | None, kittens: list[tuple[str, str]]
):
    observed = [
        ObservedKitten(id=str(index), sex=sex, color=color)
        for index, (sex, color) in enumerate(kittens)
    ]
    return _LITTER_SERVICE.infer(
        LitterParent(sire, breed), LitterParent(dam, breed), observed
    )


def _representative_surviving_pair(
    sire: str, dam: str, breed: str | None, kittens: list[tuple[str, str]]
):
    """リター推定が採用する代表的な親ペアを返す。無ければ None。

    サービス公開 API を使う。White 親は座位別逆算の代表値から組み立てる (全下地列挙をしない)。
    """

    observed = [
        ObservedKitten(id=str(index), sex=sex, color=color)
        for index, (sex, color) in enumerate(kittens)
    ]
    return _LITTER_SERVICE.representative_parents(
        LitterParent(sire, breed), LitterParent(dam, breed), observed
    )


def _forward_colors_from_pair(
    sire_genotype, dam_genotype, sire_color: str, dam_color: str, breed: str | None
) -> dict[str, set[str]]:
    """親遺伝子型ペアを順方向の命名パイプラインに通し、性別別の canonical 色集合を返す。

    リター推定の生存判定は「発現キー + 無視座位」で照合するため、実際の命名 (順方向) で
    観察色が再現されるかは別問題。ここで順方向命名を通して往復整合を検証する。
    """

    produced: dict[str, set[str]] = {"Male": set(), "Female": set()}
    for kitten in _CALCULATOR.possible_kitten_genotypes(sire_genotype, dam_genotype):
        name = _CALCULATOR._namer.classify_phenotype(kitten, sire_color, dam_color, breed)
        if name is None:
            continue
        name = _CALCULATOR._namer.post_process_color_name(name, sire_color, dam_color, breed)
        produced[kitten.sex].add(COLOR_MASTER.canonical_name(name))
    return produced


# --- 軸1: 順方向 (審判) の網羅 --------------------------------------------------


@pytest.mark.parametrize(
    "case", REPRESENTATIVE_CASES, ids=[f"case{c[0]}" for c in REPRESENTATIVE_CASES]
)
def test_representative_forward_is_valid(
    case: tuple[int, str | None, str, str, str | None]
) -> None:
    """代表12ケースの順方向出力が健全 (合計100%・0%禁止・未分類ゼロ) で、目標があれば出現する。"""

    _no, target, sire, dam, breed = case
    payload: dict[str, object] = {"sire_color": sire, "dam_color": dam, "mode": "normal"}
    if breed:
        payload["breed"] = breed
    response = client.post("/api/v1/calculate", json=payload)
    assert response.status_code == 200, response.text
    body = response.json()
    results = body["results"]

    assert results, f"順方向結果が空: {sire} x {dam}"
    total = round(sum(float(entry["probability_pct"]) for entry in results), 2)
    assert abs(total - 100.0) < 0.05, f"合計が100%でない ({total}%): {sire} x {dam}"
    assert all(float(entry["probability_pct"]) > 0 for entry in results), "0%以下の行がある"
    assert body["diagnostics"]["unmatched_probability"] == 0, "未分類が残っている (審判が信頼できない)"

    if target is not None:
        assert _forward_probability_of(results, target) > 0, (
            f"目標 {target} が順方向に出現しない: {sire} x {dam}"
        )


# --- 契約1: 逆引き往復 ---------------------------------------------------------
# 逆引きの確定候補を calculate に戻すと、目標色が主張%と整合して出現する。
# (target, target_sex, cats[(sex, color, breed)])
REVERSE_CASES: list[tuple[str, str | None, list[tuple[str, str, str | None]]]] = [
    ("Black", None, [("male", "Black", None), ("female", "Black", None)]),
    ("Lilac", None, [("male", "Lilac", None), ("female", "Lilac", None)]),
    ("Red", "male", [("male", "Red", None), ("female", "Red", None)]),
    (
        "Natural Mink",
        None,
        [("male", "Natural Mink", "Tonkinese"), ("female", "Natural Mink", "Tonkinese")],
    ),
]


@pytest.mark.parametrize("target, target_sex, cats", REVERSE_CASES)
def test_reverse_lookup_roundtrips_to_forward(
    target: str, target_sex: str | None, cats: list[tuple[str, str, str | None]]
) -> None:
    """逆引きの確定候補を順方向に戻すと、目標が出現し、確定%が順方向%と一致する。"""

    candidate = _reverse_lookup(target, _cats(cats), target_sex)
    assert candidate is not None, f"逆引き候補が得られない: {target}"

    breed = candidate["sire"].get("breed") or candidate["dam"].get("breed")
    forward = _calculate(candidate["sire"]["color"], candidate["dam"]["color"], breed)
    forward_probability = _forward_probability_of(forward, target, target_sex)

    # 契約: 目標が確かに順方向で出る。
    assert forward_probability > 0, f"順方向に目標 {target} が出ない"
    # 契約: 確定候補の主張%は順方向(normal)の目標%と一致する (両モードで%の意味が揃う)。
    assert candidate["category"] == "確定で期待できる"
    assert abs(float(candidate["confirmed_probability_pct"]) - forward_probability) < 0.5, (
        f"逆引き確定% {candidate['confirmed_probability_pct']} と順方向% {forward_probability} が不一致"
    )


# --- 契約3: 反例 (負のテスト) --------------------------------------------------
# 逆引きで「出ない」とされたペアは、順方向でも目標色0%。
REVERSE_NEGATIVE_CASES: list[tuple[str, str | None, list[tuple[str, str, str | None]]]] = [
    ("White", None, [("male", "Black", None), ("female", "Blue", None)]),
    ("Tortoiseshell", "female", [("male", "Black", None), ("female", "Black", None)]),
    ("Brown Tabby-White", None, [("male", "Black", None), ("female", "Black", None)]),
]


@pytest.mark.parametrize("target, target_sex, cats", REVERSE_NEGATIVE_CASES)
def test_reverse_lookup_negative_matches_forward(
    target: str, target_sex: str | None, cats: list[tuple[str, str, str | None]]
) -> None:
    """逆引きで候補が出ないペアは、順方向でも目標色が0%であることを確認する。"""

    candidate = _reverse_lookup(target, _cats(cats), target_sex)
    assert candidate is None, f"候補が出ないはずが得られた: {target}"

    (sire_sex, sire_color, breed), (_dam_sex, dam_color, _dam_breed) = cats
    forward = _calculate(sire_color, dam_color, breed)
    assert _forward_probability_of(forward, target, target_sex) == 0, (
        f"逆引きで出ないのに順方向で {target} が出る (審判との矛盾)"
    )


# --- 契約2: リター往復 ---------------------------------------------------------
# リター推定が「推定可能」を返したら、採用した生存親ペアを順方向命名に戻すと
# 観察された全子猫が確率>0 で出現する (White 親も矛盾にしない)。
# (name, sire, dam, breed, kittens[(sex, color)])
LITTER_CASES: list[tuple[str, str, str, str | None, list[tuple[str, str]]]] = [
    ("R1_black_black_chocolate", "Black", "Black", None, [("female", "Chocolate")]),
    ("R2a_white_black_blackM", "White", "Black", None, [("male", "Black")]),
    (
        "R2b_white_black_blackM_blueF",
        "White",
        "Black",
        None,
        [("male", "Black"), ("female", "Blue")],
    ),
    ("black_black_blueF", "Black", "Black", None, [("female", "Blue")]),
    ("black_black_seal_pointF", "Black", "Black", None, [("female", "Seal Point")]),
    (
        "blue_redtabby_litter",
        "Blue",
        "Red Tabby",
        None,
        [("male", "Cream Tabby"), ("female", "Brown Patched Tabby"), ("female", "Blue Patched Tabby")],
    ),
]


@pytest.mark.parametrize(
    "name, sire, dam, breed, kittens", LITTER_CASES, ids=[c[0] for c in LITTER_CASES]
)
def test_litter_inference_roundtrips_to_forward(
    name: str, sire: str, dam: str, breed: str | None, kittens: list[tuple[str, str]]
) -> None:
    """リター推定の親を順方向に戻すと、観察された全子猫が確率>0 で出現する。"""

    report = _litter_inference(sire, dam, breed, kittens)
    # White 親を含んでも「矛盾」にしない (WHITE-3)。
    assert report.response_category != "矛盾", f"{name}: 矛盾になってはならない"

    pair = _representative_surviving_pair(sire, dam, breed, kittens)
    assert pair is not None, f"{name}: 生存親ペアが無い"
    produced = _forward_colors_from_pair(pair[0], pair[1], sire, dam, breed)

    for sex, color in kittens:
        sex_key = "Male" if sex == "male" else "Female"
        canonical = COLOR_MASTER.canonical_name(color)
        assert canonical in produced[sex_key], (
            f"{name}: 推定親の順方向に観察子猫 {sex} {color} が出現しない"
        )


# --- White 順方向の期待値固定 (§2.1 / §2.2, WHITE-2) ----------------------------


def _forward_rows(sire: str, dam: str) -> set[tuple[str, str, float]]:
    return {
        (str(entry["sex"]), str(entry["color"]), float(entry["probability_pct"]))
        for entry in _calculate(sire, dam)
    }


def test_white_sire_forward_matches_spec_2_1() -> None:
    """父 White × 母 Black は §2.1 と一致する。

    オスは母由来で色が確定 (White25% + 母の色25%)。メスは White(下不明)父の X を受け継ぎ
    色が定まらないため、母の色に割らず全て AOC (White25% + AOC25%)。
    """

    assert _forward_rows("White", "Black") == {
        ("Male", "White", 25.0),
        ("Female", "White", 25.0),
        ("Male", "Black", 25.0),
        ("Female", "AOC", 25.0),
    }


def test_white_dam_forward_matches_spec_2_2() -> None:
    """母 White × 父 Black は §2.2 (白50% + AOC50%) と一致する。父White情報より不確定。"""

    assert _forward_rows("Black", "White") == {
        ("Male", "White", 25.0),
        ("Female", "White", 25.0),
        ("Male", "AOC", 25.0),
        ("Female", "AOC", 25.0),
    }


def test_white_forward_sums_to_100_and_no_zero() -> None:
    """White 順方向も合計100%・0%禁止を守る (両親White含む)。"""

    for sire, dam in (("White", "Black"), ("Black", "White"), ("White", "White"), ("White", "Blue")):
        rows = _forward_rows(sire, dam)
        assert abs(sum(pct for _s, _c, pct in rows) - 100.0) < 0.001, f"{sire}x{dam} 合計≠100"
        assert all(pct > 0 for _s, _c, pct in rows), f"{sire}x{dam} に0%行"


def test_aoc_is_not_canonicalized() -> None:
    """AOC は集約カテゴリであり、canonical 正規化で別名へ寄せられない (§7 落とし穴)。"""

    assert COLOR_MASTER.canonical_name("AOC") == "AOC"
    colors = {str(entry["color"]) for entry in _calculate("Black", "White")}
    assert "AOC" in colors


# --- GATE-2 / WHITE-3: リター専用期待値 ----------------------------------------


def _finding_keys(findings) -> set[tuple[str, str, str]]:
    return {(f.parent, f.locus, f.genotype) for f in findings}


def test_litter_R1_black_black_chocolate_locks_current_output() -> None:
    """§4.3 R1: Black×Black→Chocolate(♀) の確定/未確認を現状出力で固定する。"""

    report = _litter_inference("Black", "Black", None, [("female", "Chocolate")])
    assert report.response_category == "推定可能"
    assert report.contradictions == []

    confirmed = _finding_keys(report.confirmed)
    for role in ("父猫", "母猫"):
        assert (role, "A座位", "a/a") in confirmed
        assert (role, "I座位", "i/i") in confirmed
        assert (role, "S座位", "s/s") in confirmed
        assert (role, "Wb座位", "wb/wb") in confirmed
        assert (role, "W座位", "w/w") in confirmed
    assert ("父猫", "O座位", "Xo/Y") in confirmed
    assert ("母猫", "O座位", "Xo/Xo") in confirmed

    # B系保因は確定だが b/b^l の別は子1匹では未確定 (= 未確認カテゴリ)。
    unconfirmed = _finding_keys(report.unconfirmed)
    assert ("父猫", "B座位", "B/b / B/b^l") in unconfirmed
    assert ("母猫", "B座位", "B/b / B/b^l") in unconfirmed
    assert any("B座位" in test for test in report.recommended_tests)


def test_litter_R2a_white_sire_is_inferable_not_contradiction() -> None:
    """§3 R2a: White(父)×Black(母)→Black(♂) は矛盾ではなく推定可能。父 W/w 確定。"""

    report = _litter_inference("White", "Black", None, [("male", "Black")])
    assert report.response_category == "推定可能"
    assert report.contradictions == []

    confirmed = _finding_keys(report.confirmed)
    # 色付きの子が生まれた = 父は W/W ではない → W/w 確定。
    assert ("父猫", "W座位", "W/w") in confirmed
    # 父の O は Y (オスは母由来のみ)。下の X (o/O) は逆算対象外 = 確定しない。
    assert ("父猫", "O座位", "Xo/Y") not in confirmed
    assert ("父猫", "O座位", "XO/Y") not in confirmed


def test_litter_R2b_white_sire_confirms_dilute_carriers() -> None:
    """§3 R2b: White(父)×Black(母)→Black(♂)/Blue(♀) は W/w 確定 + 両親 D/d 確定。"""

    report = _litter_inference(
        "White", "Black", None, [("male", "Black"), ("female", "Blue")]
    )
    assert report.response_category == "推定可能"
    assert report.contradictions == []

    confirmed = _finding_keys(report.confirmed)
    assert ("父猫", "W座位", "W/w") in confirmed
    # Blue(♀)=d/d の観察から、母 (Black=濃色) は d を渡せる = D/d を確定。
    assert ("母猫", "D座位", "D/d") in confirmed
    # 父は下不明 (優性白の下は D/d でも d/d でもあり得る) ため、d 保因は未確認カテゴリで示す。
    unconfirmed = _finding_keys(report.unconfirmed)
    assert ("父猫", "D座位", "D/d / d/d") in unconfirmed
    # 父の下地 (A/I 等) は下不明なので確定しない (誤って a/a 等を確定しない)。
    assert ("父猫", "A座位", "a/a") not in confirmed
    assert ("父猫", "I座位", "i/i") not in confirmed
