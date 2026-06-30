"""入力サジェスト用 色一覧 API (GET /api/v1/colors) とカナ読み生成の回帰テスト。

master CSV に日本語名が無いため、色名を構成するトークン辞書からカタカナ読みを
合成する (color_reading_ja)。本テストは:
  - エンドポイントが InputAllowed 色を返すこと
  - 略称 (SourceNames) / alias / カナ読みが keywords に含まれ絞り込みに使えること
  - 代表的な色のカナ読みが期待通りであること
を検証する。
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from cat_breeding_simulator.color_reading_ja import reading_ja
from main import app

client = TestClient(app)


def _colors_by_value() -> dict[str, dict[str, object]]:
    response = client.get("/api/v1/colors")
    assert response.status_code == 200
    return {color["value"]: color for color in response.json()["colors"]}


def test_colors_endpoint_returns_input_colors() -> None:
    colors = _colors_by_value()
    # canonical + breed_specific で 300 色超を返す。
    assert len(colors) > 100
    assert "Black" in colors
    assert "Brown Tabby" in colors


def test_reading_ja_compositional() -> None:
    assert reading_ja("Brown Tabby") == "ブラウンタビー"
    assert reading_ja("Blue Patched Spotted Tabby") == "ブルーパッチドスポッテッドタビー"
    assert reading_ja("Ruddy") == "ルディ"
    # 括弧注記は読みから除外される。
    assert reading_ja("Black(AOC)") == "ブラック"


def test_keywords_include_abbreviation_and_reading() -> None:
    colors = _colors_by_value()
    entry = colors["Blue Patched Spotted Tabby"]
    joined = " ".join(str(keyword) for keyword in entry["keywords"])
    # 略称 SourceName で正式名を引ける。
    assert "Blue Pt Sp Tabby" in joined
    # カナ読みが keywords にもある (日本語入力での絞り込み用)。
    assert entry["reading_ja"] in joined
    assert entry["reading_ja"] == "ブルーパッチドスポッテッドタビー"


def test_alias_name_folded_into_canonical_keywords() -> None:
    colors = _colors_by_value()
    # "Ebony" は Black の alias。Black の keywords から引けること。
    black = colors["Black"]
    assert any("Ebony" in str(keyword) for keyword in black["keywords"])


def test_female_only_flag_exposed() -> None:
    colors = _colors_by_value()
    # パッチド (トーティ系) は female_only。
    assert colors["Blue Patched Spotted Tabby"]["sex_restriction"] == "female_only"


def test_breed_context_general_normalized_to_empty() -> None:
    colors = _colors_by_value()
    # 一般色は master 上 BreedContext=general だが、API は "" に正規化して返す
    # ("general" は猫種名ではないため)。
    assert colors["Black"]["breed_context"] == ""
    # どの色も "general" がそのまま漏れない。非空なら実際の猫種名のみ。
    assert all(color["breed_context"] != "general" for color in colors.values())


def test_ruddy_reading_and_breed_context_exposed() -> None:
    """Ruddy はルディ読みで、Abyssinian/Somali 共有の固有呼称として返す。"""

    colors = _colors_by_value()
    ruddy = colors["Ruddy"]
    assert ruddy["reading_ja"] == "ルディ"
    assert "ルディ" in ruddy["keywords"]
    assert "Abyssinian" in str(ruddy["breed_context"])
    assert "Somali" in str(ruddy["breed_context"])
