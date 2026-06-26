"""フィードバック受付エンドポイント /api/v1/feedback の回帰テスト。

メール基盤 (RESEND_API_KEY / ADMIN_EMAIL) は未設定環境で動くため、送信は行われず
sent=False が返る (受付自体は成功)。レート制限は IP 単位なので各テストで
X-Forwarded-For を変えてバケットを分離する。
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def _post(message: str, ip: str) -> object:
    return client.post(
        "/api/v1/feedback",
        json={"message": message},
        headers={"X-Forwarded-For": ip},
    )


def test_feedback_accepted_without_email_config() -> None:
    # メール未設定環境では送信せず sent=False (受付は 200)。
    response = _post("使いやすいです！要望です。", "10.0.0.1")
    assert response.status_code == 200
    assert response.json() == {"sent": False}


def test_feedback_empty_rejected() -> None:
    # 空白のみは 422。
    response = _post("   ", "10.0.0.2")
    assert response.status_code == 422


def test_feedback_too_long_rejected() -> None:
    # 200 文字超は pydantic で 422。
    response = _post("あ" * 201, "10.0.0.3")
    assert response.status_code == 422


def test_feedback_rate_limited() -> None:
    # 同一 IP から短時間に送り続けると 429 になる。
    ip = "10.0.0.4"
    statuses = [_post(f"メッセージ{i}", ip).status_code for i in range(7)]
    assert 429 in statuses, f"レート制限が効いていない: {statuses}"
    # 別 IP は影響を受けない。
    other = _post("別IPからの送信", "10.0.0.5")
    assert other.status_code == 200
