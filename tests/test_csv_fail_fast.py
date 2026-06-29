"""CSV ローダーの Fail-Fast 検証。

マスタ CSV の欠落・破損時に、空データで起動を続けず RuntimeError で即座に落ちること
(= Docker のコピー漏れ等を起動時に露見させる) を保証する。
"""

import os

import pytest

from cat_breeding_simulator import color_master, display_alias_map, master_data

# (ローダー関数, 期待されるファイル名)。エラーメッセージにファイル名が含まれることも確認する。
LOADERS = [
    (master_data._load_color_base_loci, "cat_color_genetic_map.csv"),
    (master_data._load_color_definitions, "cat_color_genetic_map.csv"),
    (master_data._load_breed_filters, "cat_breed_genetic_map.csv"),
    (color_master._load_master_rows, "cat_color_master.csv"),
    (display_alias_map._load_map_rows, "cat_color_display_alias_map.csv"),
]


@pytest.mark.parametrize("loader, filename", LOADERS)
def test_loader_raises_when_csv_missing(loader, filename, monkeypatch):
    """CSV がどの探索パスにも無いとき、RuntimeError を送出し原因を明示する。"""

    # すべての探索パスを「存在しない」扱いにする。
    monkeypatch.setattr(os.path, "exists", lambda _path: False)
    with pytest.raises(RuntimeError) as excinfo:
        loader()
    # 原因特定のため、メッセージに対象ファイル名が含まれること。
    assert filename in str(excinfo.value)


def test_color_base_loci_raises_on_broken_csv(monkeypatch, tmp_path):
    """文字コードが壊れた CSV を握りつぶさず、RuntimeError として表面化させる。"""

    # utf-8 として不正なバイト列を持つ CSV を、探索先頭 (相対パス) に置く。
    broken = tmp_path / "cat_color_genetic_map.csv"
    broken.write_bytes(b"\xff\xfe CoatColor\n \x80\x81 broken")
    monkeypatch.chdir(tmp_path)

    with pytest.raises(RuntimeError):
        master_data._load_color_base_loci()
