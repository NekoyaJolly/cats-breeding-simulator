"""毛色確率計算APIの回帰テスト。"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from cat_breeding_simulator.engine import CoatColorCalculator
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
    assert "not valid for a male" in response.json()["detail"]
