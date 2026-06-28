"""目標カラーから探す逆引きAPIのテスト。"""

from __future__ import annotations

from fastapi.testclient import TestClient

from main import app


client = TestClient(app)


def test_reverse_lookup_returns_confirmed_candidate() -> None:
    """登録済み条件だけで目標カラーが出る交配候補を返す。"""

    response = client.post(
        "/api/v1/reverse-lookup",
        json={
            "target_color": "Lilac",
            "cats": [
                {"id": "sire-1", "name": "父ライラック", "sex": "male", "color": "Lilac"},
                {"id": "dam-1", "name": "母ライラック", "sex": "female", "color": "Lilac"},
            ],
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "success"
    assert len(body["candidates"]) == 1
    candidate = body["candidates"][0]
    assert candidate["category"] == "確定で期待できる"
    assert candidate["sire"]["name"] == "父ライラック"
    assert candidate["dam"]["name"] == "母ライラック"
    assert candidate["confirmed_probability_pct"] > 0
    assert candidate["conditional_max_probability_pct"] >= candidate["confirmed_probability_pct"]
    assert "登録済みの毛色・確認済み因子だけで成立" in candidate["establishment_conditions"]
    assert candidate["locus_evidence"]


def test_reverse_lookup_returns_conditional_candidate_with_tests() -> None:
    """未確認因子が合う場合だけ目標カラーが出る候補は、条件と推奨検査を返す。"""

    response = client.post(
        "/api/v1/reverse-lookup",
        json={
            "target_color": "Seal Point",
            "cats": [
                {"id": "sire-1", "name": "父ポイント", "sex": "male", "color": "Seal Point"},
                {"id": "dam-1", "name": "母ブラック", "sex": "female", "color": "Black"},
            ],
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body["candidates"]) == 1
    candidate = body["candidates"][0]
    assert candidate["confirmed_probability_pct"] == 0
    assert candidate["conditional_max_probability_pct"] > 0
    assert candidate["category"] == "条件付きで期待できる"
    assert any("C座位" in condition for condition in candidate["confirmation_needed"])
    assert any("C座位" in test for test in candidate["recommended_tests"])
    assert any(evidence["locus"] == "C" for evidence in candidate["locus_evidence"])


def test_reverse_lookup_separates_confirmed_and_conditional_probabilities() -> None:
    """ブルー♂×チョコレート♀→ライラックは、B座位とD座位の確認が必要な条件付き候補になる。"""

    response = client.post(
        "/api/v1/reverse-lookup",
        json={
            "target_color": "Lilac",
            "cats": [
                {"id": "sire-1", "name": "青系の父", "sex": "male", "color": "Blue"},
                {"id": "dam-1", "name": "チョコの母", "sex": "female", "color": "Chocolate"},
            ],
        },
    )

    assert response.status_code == 200
    candidate = response.json()["candidates"][0]
    assert candidate["confirmed_probability_pct"] == 0
    assert candidate["conditional_max_probability_pct"] == 25.0
    assert any("青系の父" in item and "B座位" in item for item in candidate["confirmation_needed"])
    assert any("チョコの母" in item and "D座位" in item for item in candidate["confirmation_needed"])
    assert candidate["other_possible_colors"]


def test_reverse_lookup_ignores_same_sex_pairs() -> None:
    """父母が揃わない登録内容では候補を返さない。"""

    response = client.post(
        "/api/v1/reverse-lookup",
        json={
            "target_color": "Black",
            "cats": [
                {"id": "sire-1", "name": "父1", "sex": "male", "color": "Black"},
                {"id": "sire-2", "name": "父2", "sex": "male", "color": "Chocolate"},
            ],
        },
    )

    assert response.status_code == 200
    assert response.json()["candidates"] == []


def test_reverse_lookup_no_candidate_includes_unchecked_loci() -> None:
    """候補が確認できない場合も、目標条件と確認できない座位を返す。"""

    response = client.post(
        "/api/v1/reverse-lookup",
        json={
            "target_color": "White",
            "cats": [
                {"id": "sire-1", "name": "黒の父", "sex": "male", "color": "Black"},
                {"id": "dam-1", "name": "青の母", "sex": "female", "color": "Blue"},
            ],
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["candidates"] == []
    assert body["response_category"] == "現在の登録情報では確認できない"
    assert any(condition.startswith("W座位") for condition in body["target_conditions"])
    assert any("W座位" in condition for condition in body["unchecked_conditions"])
