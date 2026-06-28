"""リター実績から推定APIのテスト。"""

from __future__ import annotations

from fastapi.testclient import TestClient

from cat_breeding_simulator.engine import CoatColorCalculator
from cat_breeding_simulator.litter_inference import LitterInferenceService, LitterParent, ObservedKitten
from cat_breeding_simulator.master_data import ParentGenotype
from main import app


client = TestClient(app)


def _finding_keys(findings: list[dict[str, object]]) -> set[tuple[str, str, str]]:
    return {
        (str(finding["parent"]), str(finding["locus"]), str(finding["genotype"]))
        for finding in findings
    }


def test_litter_inference_representative_case() -> None:
    """Blue父×Red Tabby母の実績から、D/O/A/B座位の代表推定を返す。"""

    response = client.post(
        "/api/v1/litter-inference",
        json={
            "sire": {"color": "Blue"},
            "dam": {"color": "Red Tabby"},
            "kittens": [
                {"id": "k1", "sex": "male", "color": "Cream Tabby"},
                {"id": "k2", "sex": "female", "color": "Brown Patched Tabby"},
                {"id": "k3", "sex": "female", "color": "Blue Patched Tabby"},
            ],
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "success"
    assert body["response_category"] == "推定可能"
    assert body["candidate_pair_count"] > 0
    assert body["contradictions"] == []

    confirmed = _finding_keys(body["confirmed"])
    assert ("父猫", "D座位", "d/d") in confirmed
    assert ("母猫", "D座位", "D/d") in confirmed
    assert ("父猫", "O座位", "Xo/Y") in confirmed
    assert ("母猫", "O座位", "XO/XO") in confirmed

    conditional = _finding_keys(body["conditional"])
    assert ("母猫", "A座位", "A/-") in conditional

    inferred = _finding_keys(body["inferred"])
    assert ("母猫", "O座位", "XO/XO") in inferred

    unconfirmed = _finding_keys(body["unconfirmed"])
    assert any(parent == "父猫" and locus == "B座位" for parent, locus, _ in unconfirmed)
    assert any(parent == "母猫" and locus == "B座位" for parent, locus, _ in unconfirmed)
    assert any("B座位" in test for test in body["recommended_tests"])
    assert any("Red / Cream" in warning for warning in body["warnings"])


def test_litter_inference_warns_for_calico_white_spotting() -> None:
    """Calico系の観察色は、白斑確認の警告を返す。"""

    response = client.post(
        "/api/v1/litter-inference",
        json={
            "sire": {"color": "Blue"},
            "dam": {"color": "Red Tabby"},
            "kittens": [
                {"id": "k1", "sex": "female", "color": "Dilute Calico"},
            ],
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert any("白斑" in warning for warning in body["warnings"])
    assert any("S座位" in test for test in body["recommended_tests"])


def test_litter_inference_warns_for_tortie_white_spotting_review() -> None:
    """Tortie系の観察色も、白斑確認の警告を返す。"""

    response = client.post(
        "/api/v1/litter-inference",
        json={
            "sire": {"color": "Black"},
            "dam": {"color": "Red"},
            "kittens": [
                {"id": "k1", "sex": "female", "color": "Tortoiseshell"},
            ],
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert any(
        "Calico / Tortie" in warning and "白斑" in warning
        for warning in body["warnings"]
    )
    assert any("S座位" in test for test in body["recommended_tests"])


# --- PERF-3: 座位独立分解が従来の総当たり (brute-force) と同一の生存ペアを返すことの等価テスト ---
# 旧実装 (possible_kitten_genotypes で結合集合を物質化し署名一致を見る) を本テスト内に
# 参照実装として保持し、新実装 (_surviving_pairs のビットマスク座位別照合) と突き合わせる。


def _signature(sex: str, loci: dict[str, tuple[str, str]], ignore: set[str]) -> tuple:
    return (
        sex,
        tuple(
            sorted(
                (locus, tuple(sorted(alleles)))
                for locus, alleles in loci.items()
                if locus not in ignore
            )
        ),
    )


def _pair_key(genotype: ParentGenotype) -> tuple:
    return (
        genotype.sex,
        tuple(sorted((locus, tuple(sorted(alleles))) for locus, alleles in genotype.loci.items())),
    )


def _bruteforce_surviving(
    calc: CoatColorCalculator,
    sire_color: str,
    dam_color: str,
    kittens: list[tuple[str, str]],
) -> set[tuple]:
    sire_candidates = calc.parent_genotype_candidates(
        sire_color, "male", None, include_unconfirmed_carriers=True
    )
    dam_candidates = calc.parent_genotype_candidates(
        dam_color, "female", None, include_unconfirmed_carriers=True
    )
    observed: list[tuple[set[str], set[tuple]]] = []
    for sex, color in kittens:
        candidates = calc.parent_genotype_candidates(
            color, sex, None, include_unconfirmed_carriers=True
        )
        ignore = LitterInferenceService._ignored_loci_for_observed(color)
        observed_sex = "Male" if sex == "male" else "Female"
        sigs = {_signature(observed_sex, candidate.loci, ignore) for candidate in candidates}
        observed.append((ignore, sigs))

    surviving: set[tuple] = set()
    for sire in sire_candidates:
        for dam in dam_candidates:
            generated = calc.possible_kitten_genotypes(sire, dam)
            if all(
                bool(sigs & {_signature(kitten.sex, kitten.loci, ignore) for kitten in generated})
                for ignore, sigs in observed
            ):
                surviving.add((_pair_key(sire), _pair_key(dam)))
    return surviving


def _new_surviving(
    calc: CoatColorCalculator,
    sire_color: str,
    dam_color: str,
    kittens: list[tuple[str, str]],
) -> set[tuple]:
    service = LitterInferenceService(calc)
    sire_candidates = calc.parent_genotype_candidates(
        sire_color, "male", None, include_unconfirmed_carriers=True
    )
    dam_candidates = calc.parent_genotype_candidates(
        dam_color, "female", None, include_unconfirmed_carriers=True
    )
    observed = [
        service._observed_kitten_profiles(ObservedKitten(id=str(i), sex=sex, color=color), None)
        for i, (sex, color) in enumerate(kittens)
    ]
    pairs = service._surviving_pairs(sire_candidates, dam_candidates, observed)
    return {(_pair_key(sire), _pair_key(dam)) for sire, dam in pairs}


def test_litter_surviving_pairs_match_bruteforce() -> None:
    """座位独立分解の生存ペア集合が、結合列挙の総当たりと完全一致する。"""

    calc = CoatColorCalculator()
    cases: list[tuple[str, str, list[tuple[str, str]]]] = [
        ("Black", "Black", [("female", "Black")]),
        ("Black", "Black", [("female", "Chocolate")]),
        ("Black", "Black", [("male", "Blue")]),
        ("Blue", "Red Tabby", [("male", "Cream Tabby"), ("female", "Brown Patched Tabby")]),
        ("Black", "Red", [("female", "Tortoiseshell")]),
        ("Seal Point", "Seal Point", [("male", "Seal Point")]),
        ("Black", "Black", [("female", "Dilute Calico")]),
    ]
    for sire_color, dam_color, kittens in cases:
        brute = _bruteforce_surviving(calc, sire_color, dam_color, kittens)
        fast = _new_surviving(calc, sire_color, dam_color, kittens)
        assert fast == brute, f"不一致: {sire_color} x {dam_color} {kittens}"


def test_litter_inference_rejects_too_many_kittens() -> None:
    """観察子猫が上限 (12頭) を超えると 422 で拒否する。"""

    kittens = [{"id": f"k{i}", "sex": "female", "color": "Black"} for i in range(13)]
    response = client.post(
        "/api/v1/litter-inference",
        json={"sire": {"color": "Black"}, "dam": {"color": "Black"}, "kittens": kittens},
    )
    assert response.status_code == 422
    assert "12" in str(response.json()["detail"])


def test_litter_inference_kitten_sex_restriction_error_has_kitten_context() -> None:
    """子猫の性別制約エラーは、親入力ではなく観察子猫の文脈で返す。"""

    response = client.post(
        "/api/v1/litter-inference",
        json={
            "sire": {"color": "Black"},
            "dam": {"color": "Red"},
            "kittens": [
                {"id": "kitten-sex", "sex": "male", "color": "Blue Tortie"},
            ],
        },
    )

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert "子猫" in detail
    assert "kitten-sex" in detail
    assert "オス" in detail
    assert "父猫" not in detail
    assert "母猫" not in detail
