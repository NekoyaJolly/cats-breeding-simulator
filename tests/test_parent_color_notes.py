"""親色が子に出現しないときの注釈 (parent_color_notes) の回帰テスト。

劣性形質 (チョコレート b/b・希釈 d/d・非アグーチ a/a 等) は、相手親がその因子を
持たない限り子に出ない。入力した親色が子に出ないケースを検知し、原因の劣性因子を
注釈として返す (normal モードのみ)。
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def _notes(sire: str, dam: str, mode: str = "normal") -> list[dict[str, object]]:
    response = client.post(
        "/api/v1/calculate",
        json={"sire_color": sire, "dam_color": dam, "mode": mode},
    )
    assert response.status_code == 200
    return response.json()["parent_color_notes"]


def test_lilac_not_in_offspring_of_black_based_dam() -> None:
    # 父 Lilac (b/b a/a d/d) × 母 Blue Patched Tabby-White (B/B A/A) → Lilac は出ない。
    notes = _notes("Lilac", "Blue Patched Tabby-White")
    assert len(notes) == 1
    note = notes[0]
    assert note["parent"] == "sire"
    assert note["color"] == "Lilac"
    factors = " / ".join(str(f) for f in note["blocked_factors"])
    # 母が黒(B)・タビー(A)のため、チョコレート(b) と 非アグーチ/ソリッド(a) が原因。
    assert "チョコレート" in factors
    assert "ソリッド" in factors or "非アグーチ" in factors


def test_same_color_parents_have_no_note() -> None:
    # 同色同士は親色が子に出るので注釈なし。
    assert _notes("Lilac", "Lilac") == []
    assert _notes("Black", "Black") == []


def test_dam_color_present_no_note_for_dam() -> None:
    # 母 Blue Patched Tabby-White はこの交配で子に出る → 母への注釈は無い。
    notes = _notes("Lilac", "Blue Patched Tabby-White")
    assert all(note["parent"] != "dam" for note in notes)


def test_notes_only_in_normal_mode() -> None:
    # carrier_exploration は normal とは別。注釈は normal のみ。
    assert _notes("Lilac", "Blue Patched Tabby-White", mode="carrier_exploration") == []


def test_non_orange_parent_blocked_by_red_dam() -> None:
    # 父 Blue Tabby-White (非オレンジ) × 母 Shell Cameo (赤 O/O) → 全子に O が渡り
    # 非オレンジの Blue Tabby は出ない。原因は O 座位 (母が o を渡せない)。
    notes = _notes("Blue Tabby-White", "Shell Cameo")
    sire = next(n for n in notes if n["parent"] == "sire")
    factors = " / ".join(str(f) for f in sire["blocked_factors"])
    assert "非オレンジ" in factors and " o" in factors
    # 希釈 D は normal_mode で必ず展開される (母 D/- は d を渡せる) ため、
    # 誤って希釈 d をブロッカーに挙げてはならない。
    assert "希釈" not in factors and " d" not in factors


def test_dilute_not_blocked_when_other_parent_is_dense() -> None:
    # 希釈の親色は、相手が濃色 (D/-) でも normal_mode 展開で d を渡せるため
    # 希釈 d をブロッカーに挙げない (相手が濃色 = d を持たない、という誤判定の回帰)。
    notes = _notes("Silver Tabby", "Dilute Calico")
    for note in notes:
        factors = " / ".join(str(f) for f in note["blocked_factors"])
        assert "希釈" not in factors, f"希釈 d が誤って計上された: {note}"
