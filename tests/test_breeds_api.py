"""猫種一覧 API (GET /api/v1/breeds) と猫種バリデーションの回帰テスト。

猫種は任意入力だが、指定された場合は既知の猫種のみ受け付ける (従来は未知の猫種を
黙って無視していた)。affects_genetics で計算結果に影響する猫種を区別する。
"""

from __future__ import annotations

import csv
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from cat_breeding_simulator.engine import BreedingCalculationError, CoatColorCalculator
from main import app

client = TestClient(app)

BREED_POLICY_PATH = Path("docs/architecture/cat_breed_color_policy.csv")
BREED_POLICY_COLUMNS = {
    "Breed",
    "CurrentBreedKey",
    "PolicyStatus",
    "FixedGeneticPolicy",
    "AllowedColorPolicy",
    "ExcludedColorPolicy",
    "DisplayNamePolicy",
    "OutOfScopeNotes",
    "ImplementationNotes",
}
BREED_POLICY_STATUSES = {"documented", "needs_review", "future_breed"}


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


def test_coat_variants_collapsed_to_base() -> None:
    values = {b["value"] for b in client.get("/api/v1/breeds").json()["breeds"]}
    # コートバリアント (SH/LH/SE/NL 等) は base に集約され、変種名は一覧に出ない。
    assert "Kinkaro" in values
    assert "Scottish Fold" in values
    assert not any("(" in v and ")" in v and _is_coat_variant(v) for v in values)


def _is_coat_variant(name: str) -> bool:
    import re

    match = re.match(r"^.*\(([^)]*)\)\s*$", name)
    if not match:
        return False
    tokens = [t for t in re.split(r"[.\s]+", match.group(1)) if t]
    return bool(tokens) and all(
        t.upper() in {"SH", "LH", "NL", "SE", "LE", "ST", "LWH", "SWH"} for t in tokens
    )


def test_collapsed_base_breed_validates() -> None:
    calc = CoatColorCalculator()
    # base 集約された猫種 (BREED_FILTERS には変種名しか無い) も入力として通る。
    report = calc.calculate_report("Black", "Black", breed="Kinkaro")
    assert report.results


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


def test_garbage_breed_in_filters_is_rejected() -> None:
    # CSV 由来のゴミ行 ("ｱｷ") は BREED_FILTERS には存在するが、一覧/計算とも弾く。
    calc = CoatColorCalculator()
    with pytest.raises(BreedingCalculationError, match="未対応の猫種"):
        calc.calculate_report("Black", "Black", breed="ｱｷ")


def test_calculate_endpoint_rejects_unknown_breed() -> None:
    response = client.post(
        "/api/v1/calculate",
        json={"sire_color": "Black", "dam_color": "Black", "breed": "Nope", "mode": "normal"},
    )
    assert response.status_code == 422
    assert "未対応の猫種" in response.json()["detail"]


def test_breed_color_policy_csv_has_required_shape() -> None:
    """猫種カラー方針CSVは固定遺伝子・許容色・表示名・対象外メモを分離して保持する。"""

    with BREED_POLICY_PATH.open(encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)
        assert set(reader.fieldnames or []) == BREED_POLICY_COLUMNS
        rows = list(reader)

    assert rows
    assert {row["PolicyStatus"] for row in rows} <= BREED_POLICY_STATUSES


def test_breed_color_policy_documents_tonkinese_classes() -> None:
    """Tonkinese は breed 全体を cb/cs 固定せず、色クラスごとの C座位を記録する。"""

    with BREED_POLICY_PATH.open(encoding="utf-8") as csv_file:
        rows = list(csv.DictReader(csv_file))

    tonkinese = next(row for row in rows if row["Breed"] == "Tonkinese")
    assert tonkinese["PolicyStatus"] == "documented"
    assert "No fixed C policy at breed level" in tonkinese["FixedGeneticPolicy"]
    assert "Point=cs/cs" in tonkinese["FixedGeneticPolicy"]
    assert "Mink=cb/cs" in tonkinese["FixedGeneticPolicy"]
    assert "Solid/Sepia=cb/cb" in tonkinese["FixedGeneticPolicy"]
    assert "Natural Point" in tonkinese["AllowedColorPolicy"]
    assert "Natural Mink" in tonkinese["AllowedColorPolicy"]
    assert "Natural Solid" in tonkinese["AllowedColorPolicy"]
    assert "Sepia class" in tonkinese["DisplayNamePolicy"]
    assert "Point class" in tonkinese["ImplementationNotes"]
