"""ゴールデン交配スナップショットテスト。

代表的な交配 (3モード・主要座位・猫種制約・親色不在注釈・ワイドバンド未分類など) の
/api/v1/calculate 出力を tests/fixtures/golden_crosses.json に固定し、出力が1箇所でも
変わったら落ちる回帰ネットにする。命名/確率まわりのリファクタ時の安全網。

意図的に出力を変えたとき (期待値の更新) は再生成する:
    GOLDEN_REGEN=1 python -m pytest tests/test_golden_crosses.py
差分を git で必ず目視レビューしてからコミットすること。
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from main import app

client = TestClient(app)
FIXTURE_PATH = Path(__file__).parent / "fixtures" / "golden_crosses.json"

# (父, 母, 猫種 or None, モード)。狙い: 3モード全部 + A/B/C/D/I/O/S 各座位 +
# トーティ/♀限定 + 白斑 + 希釈不可逆 + 親色不在注釈 + bl/優性白/スモーク/猫種制約/
# シルバーtipping/Golden(未分類)/sepia/mink。
CROSSES: list[tuple[str, str, str | None, str]] = [
    ("Black", "Black", None, "normal"),
    ("Blue Patched Tabby-White", "Black", None, "normal"),
    ("Blue", "Cream Tabby", None, "normal"),
    ("Brown Tabby", "Brown Tabby", None, "normal"),
    ("Cameo Tabby", "Blue Patched Tabby-White", None, "normal"),
    ("Chocolate", "Black", None, "normal"),
    ("Cream Tabby-White", "Dilute Calico", None, "normal"),
    ("Lilac", "Blue Patched Tabby-White", None, "carrier_exploration"),
    ("Lilac", "Blue Patched Tabby-White", None, "normal"),
    ("Red", "Tortoiseshell", None, "normal"),
    ("Seal Point", "Black", None, "normal"),
    ("Silver Tabby", "Black", None, "explicit_carrier"),
    ("Silver Tabby", "Blue Patched Tabby-White", None, "normal"),
    ("Silver Tabby", "Dilute Calico", None, "normal"),
    # --- 追加カバレッジ ---
    ("Chinchilla Silver", "Shaded Silver", None, "normal"),       # シルバー tipping
    ("Chinchilla Golden", "Black", None, "normal"),               # ワイドバンド: 非オレンジ子に Golden が出る
    ("Chinchilla Golden", "Cream Tabby-White", None, "normal"),   # ワイドバンド: 赤ダム=純Goldenは出ないが未分類は解消
    ("Cinnamon", "Black", None, "normal"),                        # bl アレル (B座位 第3)
    ("White", "Black", None, "normal"),                           # 優性白 (W座位 上位)
    ("Black Smoke", "Cream", None, "normal"),                     # スモーク (I on solid) + 赤
    ("Seal Point", "Seal Point", "Siamese", "normal"),            # 猫種制約 + ポイント
    ("Sable", "Sable", "Burmese", "normal"),                      # セピア cb + 猫種
    ("Natural Mink", "Natural Mink", "Tonkinese", "normal"),      # ミンク cs/cb + 猫種
]


def _key(cross: tuple[str, str, str | None, str]) -> str:
    sire, dam, breed, mode = cross
    return f"{sire}|{dam}|{breed or '-'}|{mode}"


def _payload(cross: tuple[str, str, str | None, str]) -> dict[str, str]:
    sire, dam, breed, mode = cross
    payload = {"sire_color": sire, "dam_color": dam, "mode": mode}
    if breed:
        payload["breed"] = breed
    return payload


def _fetch(cross: tuple[str, str, str | None, str]) -> dict[str, object]:
    response = client.post("/api/v1/calculate", json=_payload(cross))
    return {"status": response.status_code, "body": response.json()}


def _regenerate() -> None:
    data = {_key(cross): _fetch(cross) for cross in CROSSES}
    FIXTURE_PATH.parent.mkdir(parents=True, exist_ok=True)
    FIXTURE_PATH.write_text(
        json.dumps(data, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _load_golden() -> dict[str, object]:
    if not FIXTURE_PATH.exists():
        return {}
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def golden() -> dict[str, object]:
    # 再生成は「実行フェーズ」で1回だけ行う (収集フェーズ/--collect-only に副作用を出さない)。
    # 再生成: GOLDEN_REGEN=1 python -m pytest tests/test_golden_crosses.py
    if os.environ.get("GOLDEN_REGEN") == "1":
        _regenerate()
    return _load_golden()


@pytest.mark.parametrize("cross", CROSSES, ids=[_key(c) for c in CROSSES])
def test_golden_cross(
    cross: tuple[str, str, str | None, str], golden: dict[str, object]
) -> None:
    expected = golden.get(_key(cross))
    assert expected is not None, (
        f"golden 未登録: {_key(cross)}。"
        "`GOLDEN_REGEN=1 python -m pytest tests/test_golden_crosses.py` で再生成。"
    )
    assert _fetch(cross) == expected
