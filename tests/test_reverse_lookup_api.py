"""目標カラーから探す逆引きAPIのテスト。"""

from __future__ import annotations

import pytest
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


@pytest.mark.parametrize(
    "target_color, expected_locus, expected_probability",
    [
        ("Blue", "D座位", 25.0),
        ("Chocolate", "B座位", 23.4376),
        ("Seal Point", "C座位", 23.4376),
    ],
)
def test_reverse_lookup_black_pair_reports_hidden_condition_by_locus(
    target_color: str,
    expected_locus: str,
    expected_probability: float,
) -> None:
    """黒同士で目標劣性カラーを狙う場合、座位ごとの条件付き候補として返す。"""

    response = client.post(
        "/api/v1/reverse-lookup",
        json={
            "target_color": target_color,
            "cats": [
                {"id": "sire-1", "name": "黒の父", "sex": "male", "color": "Black"},
                {"id": "dam-1", "name": "黒の母", "sex": "female", "color": "Black"},
            ],
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["response_category"] == "条件付きで期待できる"
    candidate = body["candidates"][0]
    assert candidate["confirmed_probability_pct"] == 0
    assert candidate["conditional_max_probability_pct"] == expected_probability
    assert candidate["confirmation_needed"]
    assert candidate["recommended_tests"]
    assert all(expected_locus in item for item in candidate["confirmation_needed"])
    assert all(expected_locus in item for item in candidate["recommended_tests"])


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


def test_reverse_lookup_target_only_returns_requirement_guidance() -> None:
    """登録猫が無くても、目標カラーから必要条件と登録案内を返す。"""

    response = client.post(
        "/api/v1/reverse-lookup",
        json={"target_color": "Blue Tabby", "target_sex": "male", "cats": []},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["target_sex"] == "male"
    assert body["candidates"] == []
    assert any(condition.startswith("D座位") for condition in body["target_conditions"])
    assert any("父猫・母猫" in condition for condition in body["unchecked_conditions"])
    assert any("父猫として評価する登録猫" in check for check in body["recommended_checks"])


def test_reverse_lookup_solid_nonwhite_pair_cannot_confirm_tabby_white_target() -> None:
    """Black × Black では、A座位とS座位を要する Brown Tabby-White を確認できない。"""

    response = client.post(
        "/api/v1/reverse-lookup",
        json={
            "target_color": "Brown Tabby-White",
            "cats": [
                {"id": "sire-1", "name": "黒の父", "sex": "male", "color": "Black"},
                {"id": "dam-1", "name": "黒の母", "sex": "female", "color": "Black"},
            ],
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["candidates"] == []
    assert body["response_category"] == "現在の登録情報では確認できない"
    assert any(condition.startswith("A座位") for condition in body["target_conditions"])
    assert any(condition.startswith("S座位") for condition in body["target_conditions"])
    assert any("A座位" in condition for condition in body["unchecked_conditions"])
    assert any("S座位" in condition for condition in body["unchecked_conditions"])


def test_reverse_lookup_non_orange_pair_cannot_confirm_tortie_target() -> None:
    """非オレンジ同士では、O/o を要する Tortoiseshell 候補を確認できない。"""

    response = client.post(
        "/api/v1/reverse-lookup",
        json={
            "target_color": "Tortoiseshell",
            "target_sex": "female",
            "cats": [
                {"id": "sire-1", "name": "黒の父", "sex": "male", "color": "Black"},
                {"id": "dam-1", "name": "黒の母", "sex": "female", "color": "Black"},
            ],
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["target_sex"] == "female"
    assert body["candidates"] == []
    assert body["response_category"] == "現在の登録情報では確認できない"
    assert any(condition.startswith("O座位") for condition in body["target_conditions"])


def test_reverse_lookup_resolves_target_with_registered_breed_context() -> None:
    """猫種固有名の目標カラーは、登録猫の猫種文脈で解決して探索する。"""

    response = client.post(
        "/api/v1/reverse-lookup",
        json={
            "target_color": "Sable",
            "cats": [
                {
                    "id": "sire-1",
                    "name": "セーブルの父",
                    "sex": "male",
                    "color": "Sable",
                    "breed": "Burmese",
                },
                {
                    "id": "dam-1",
                    "name": "セーブルの母",
                    "sex": "female",
                    "color": "Sable",
                    "breed": "Burmese",
                },
            ],
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "success"
    assert body["target_color"] == "Sable"
    assert len(body["candidates"]) == 1
    candidate = body["candidates"][0]
    assert candidate["category"] == "確定で期待できる"
    assert candidate["confirmed_probability_pct"] > 0


def test_reverse_lookup_can_filter_target_by_kitten_sex() -> None:
    """目標性別を指定した場合は、該当性別の子猫だけを目標確率に含める。"""

    response = client.post(
        "/api/v1/reverse-lookup",
        json={
            "target_color": "Red",
            "target_sex": "male",
            "cats": [
                {"id": "sire-1", "name": "赤の父", "sex": "male", "color": "Red"},
                {"id": "dam-1", "name": "赤の母", "sex": "female", "color": "Red"},
            ],
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["target_sex"] == "male"
    candidate = body["candidates"][0]
    assert candidate["category"] == "確定で期待できる"
    assert candidate["confirmed_probability_pct"] == 46.875
    assert all(entry["sex"] == "Male" for entry in candidate["target_possible_colors"])
    assert any(
        entry["sex"] == "Male" and entry["color"] == "Red"
        for entry in candidate["target_possible_colors"]
    )
    assert all(
        not (entry["sex"] == "Male" and entry["color"] == "Red")
        for entry in candidate["other_possible_colors"]
    )


def test_reverse_lookup_black_white_target_shows_male_target_outcome() -> None:
    """Cameo×Calico の Black-White 目標では、目標内訳にオス結果を表示する。"""

    response = client.post(
        "/api/v1/reverse-lookup",
        json={
            "target_color": "Black-White",
            "cats": [
                {"id": "sire-1", "name": "カメオ父", "sex": "male", "color": "Cameo"},
                {"id": "dam-1", "name": "キャリコ母", "sex": "female", "color": "Calico"},
            ],
        },
    )

    assert response.status_code == 200
    body = response.json()
    candidate = body["candidates"][0]
    assert any(
        entry["sex"] == "Male" and entry["color"] == "Black-White"
        for entry in candidate["target_possible_colors"]
    )
    assert all(
        entry["color"] != "Cameo Red Smoke-White"
        for entry in candidate["other_possible_colors"]
    )
    assert any("o/Y（オス）" in condition for condition in body["target_conditions"])


def test_reverse_lookup_rejects_female_only_alias_for_sire() -> None:
    """逆引きAPIでも通常シミュレーター同様、別名解決後のメス限定色を父猫に指定できない。"""

    response = client.post(
        "/api/v1/reverse-lookup",
        json={
            "target_color": "Lilac",
            "cats": [
                {"id": "sire-1", "name": "別名入力の父", "sex": "male", "color": "Blue Tortie"},
                {"id": "dam-1", "name": "黒の母", "sex": "female", "color": "Black"},
            ],
        },
    )

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert "Blue Cream" in detail
    assert "メス限定" in detail
    assert "父猫" in detail


def test_reverse_lookup_rejects_too_many_cats() -> None:
    """登録猫が上限 (50頭) を超えると 422 で拒否する。"""

    cats = [
        {
            "id": f"c{i}",
            "name": f"cat{i}",
            "sex": "male" if i % 2 == 0 else "female",
            "color": "Black",
        }
        for i in range(51)
    ]
    response = client.post(
        "/api/v1/reverse-lookup",
        json={"target_color": "Blue", "cats": cats},
    )
    assert response.status_code == 422
    assert "50" in str(response.json()["detail"])
