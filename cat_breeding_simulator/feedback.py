"""ユーザーフィードバックの受付とメール送信。

常駐ウィジェットから届く短いフィードバック (最大 200 文字) を、Resend 経由で
ADMIN_EMAIL 宛にメール送信する。DB には保存しない (メール送信のみ)。

必要な環境変数:
  - RESEND_API_KEY: Resend の API キー (未設定なら送信せず sent=False)
  - ADMIN_EMAIL: 送信先 (受信箱)。未設定なら sent=False
  - EMAIL_FROM: 送信元アドレス (Resend で検証済みドメイン)。既定 noreply@nekoya.co.jp
  - EMAIL_FROM_NAME: 送信元表示名。既定「猫毛色シミュレーター」

匿名アプリのため、IP 単位の簡易レート制限をインスタンス内メモリで行う。
"""

from __future__ import annotations

import html
import os
import threading
import time
from collections import defaultdict, deque

import httpx

MAX_MESSAGE_LENGTH = 200

_RESEND_ENDPOINT = "https://api.resend.com/emails"

# 簡易レート制限 (IP 単位 / インスタンス内メモリ)。Cloud Run の多インスタンス時は
# インスタンスごとの制限になる点に注意 (低トラフィックのフィードバック用途では許容)。
_RATE_LIMIT_MAX = 5          # ウィンドウあたり最大受付数
_RATE_LIMIT_WINDOW_SEC = 600  # 10 分
# キー数がこれを超えたら期限切れバケットを掃除する (大量の異なる IP 流入時のメモリ肥大対策)。
_RATE_LIMIT_MAX_KEYS = 10000
_rate_lock = threading.Lock()
_rate_hits: dict[str, deque[float]] = defaultdict(deque)


def _purge_expired(now: float) -> None:
    """最新ヒットがウィンドウ外のバケット (= 全て期限切れ) を削除する。要 _rate_lock 保持。"""

    expired = [ip for ip, hits in _rate_hits.items() if not hits or now - hits[-1] > _RATE_LIMIT_WINDOW_SEC]
    for ip in expired:
        del _rate_hits[ip]


def check_rate_limit(client_ip: str) -> bool:
    """client_ip が制限内なら True を返し、ヒットを記録する。超過なら False。"""

    now = time.time()
    with _rate_lock:
        if len(_rate_hits) > _RATE_LIMIT_MAX_KEYS:
            _purge_expired(now)
        hits = _rate_hits[client_ip]
        while hits and now - hits[0] > _RATE_LIMIT_WINDOW_SEC:
            hits.popleft()
        if len(hits) >= _RATE_LIMIT_MAX:
            return False
        hits.append(now)
        return True


def send_feedback_email(message: str) -> bool:
    """Resend で ADMIN_EMAIL 宛にフィードバックを送る。設定不足/失敗時は False。"""

    api_key = os.environ.get("RESEND_API_KEY")
    admin_email = os.environ.get("ADMIN_EMAIL")
    if not api_key or not admin_email:
        # 設定が無い環境 (ローカル/未設定の本番) では送信せず受付のみ扱いにする。
        return False

    email_from = os.environ.get("EMAIL_FROM", "noreply@nekoya.co.jp")
    from_name = os.environ.get("EMAIL_FROM_NAME", "猫毛色シミュレーター")
    safe = html.escape(message)
    payload = {
        "from": f"{from_name} <{email_from}>",
        "to": [admin_email],
        "subject": "[猫毛色シミュレーター] フィードバックが届きました",
        "html": (
            "<p>アプリ利用者からフィードバックが届きました。</p>"
            '<hr /><p style="white-space: pre-wrap;">'
            f"{safe}</p>"
        ),
        "text": f"フィードバックが届きました。\n\n{message}",
    }
    try:
        response = httpx.post(
            _RESEND_ENDPOINT,
            json=payload,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=10.0,
        )
        return response.status_code < 300
    except httpx.HTTPError:
        return False
