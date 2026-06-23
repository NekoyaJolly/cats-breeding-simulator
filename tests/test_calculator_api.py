"""毛色確率計算APIの回帰テスト。"""

from __future__ import annotations

from fastapi.testclient import TestClient

from main import app


client = TestClient(app)


def test_calculate_returns_probabilities_that_sum_to_100() -> None:
    response = client.post(
        "/api/v1/calculate",
        json={"sire_color": "Cream Tabby-White", "dam_color": "Dilute Calico", "breed": "Munchkin"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "success"
    assert payload["parameters"] == {
        "sire_color": "Cream Tabby-White",
        "dam_color": "Dilute Calico",
        "breed": "Munchkin",
    }
    assert round(sum(result["probability_pct"] for result in payload["results"]), 4) == 100.0
    assert {result["sex"] for result in payload["results"]} == {"Male", "Female"}
    assert any("Calico" in result["color"] for result in payload["results"])
    assert any("Cream" in result["color"] for result in payload["results"])


def test_breed_filter_enforces_siamese_point_genotypes() -> None:
    response = client.post(
        "/api/v1/calculate",
        json={"sire_color": "Pointed", "dam_color": "Pointed", "breed": "Siamese"},
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
    assert "not valid for a male" in response.json()["detail"]
