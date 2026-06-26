"""猫種一覧 API (GET /api/v1/breeds) と猫種バリデーションの回帰テスト。

猫種は任意入力だが、指定された場合は既知の猫種のみ受け付ける (従来は未知の猫種を
黙って無視していた)。affects_genetics で計算結果に影響する猫種を区別する。
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from cat_breeding_simulator.engine import BreedingCalculationError, CoatColorCalculator
from main import app

client = TestClient(app)


def test_breeds_endpoint_returns_breeds() -> None:
    response = client.get("/api/v1/breeds")
    assert response.status_code == 200
    breeds = response.json()["breeds"]
    values = {breed["value"] for breed in breeds}
    # 代表的な猫種が含まれる。
    assert "Abyssinian" in values
    assert "Siamese" in values
    # ASCII 英字を含まない文字化け行 (例: "ｱｷ") は除外される。
    assert all(any("a" <= c.lower() <= "z" for c in v) for v in values)


def test_breeds_affects_genetics_flag() -> None:
    breeds = {b["value"]: b for b in client.get("/api/v1/breeds").json()["breeds"]}
    # 座位制約のある猫種は affects_genetics=true。
    assert breeds["Abyssinian"]["affects_genetics"] is True
    # 制約のない猫種は affects_genetics=false。
    assert breeds["Maine Coon"]["affects_genetics"] is False


def test_unknown_breed_raises() -> None:
    calc = CoatColorCalculator()
    with pytest.raises(BreedingCalculationError, match="未対応の猫種"):
        calc.calculate_report("Black", "Black", breed="NotARealBreed")


def test_known_breed_ok() -> None:
    calc = CoatColorCalculator()
    # 既知の猫種は通る (例外なし)。
    report = calc.calculate_report("Seal Point", "Seal Point", breed="Siamese")
    assert report.results


def test_calculate_endpoint_rejects_unknown_breed() -> None:
    response = client.post(
        "/api/v1/calculate",
        json={"sire_color": "Black", "dam_color": "Black", "breed": "Nope", "mode": "normal"},
    )
    assert response.status_code == 422
    assert "未対応の猫種" in response.json()["detail"]
