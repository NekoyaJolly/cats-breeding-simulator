"""リター実績から推定APIのテスト。"""

from __future__ import annotations

from fastapi.testclient import TestClient

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
