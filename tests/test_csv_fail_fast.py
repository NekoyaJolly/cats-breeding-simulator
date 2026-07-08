"""CSV ローダーの Fail-Fast とマスター契約の検証。

マスタ CSV の欠落・破損時に、空データで起動を続けず RuntimeError で即座に落ちること
(= Docker のコピー漏れ等を起動時に露見させる) を保証する。
"""

import csv
import os
from pathlib import Path

import pytest

from cat_breeding_simulator import breed_color_policy, color_master, display_alias_map, master_data
from scripts.build_cat_color_master import load_source_colors, validate

# (ローダー関数, 期待されるファイル名)。エラーメッセージにファイル名が含まれることも確認する。
LOADERS = [
    (master_data._load_color_base_loci, "cat_color_genetic_map.csv"),
    (master_data._load_color_definitions, "cat_color_genetic_map.csv"),
    (master_data._load_breed_filters, "cat_breed_genetic_map.csv"),
    (breed_color_policy._load_policy_rows, "cat_breed_color_policy.csv"),
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


@pytest.mark.parametrize("loader, filename", LOADERS)
def test_loader_raises_on_invalid_header(loader, filename, monkeypatch, tmp_path):
    """必須列を欠くCSV (DictReaderは例外を出さないが有効行0件) を破損として検知する。"""

    # 探索先頭 (相対パス = cwd) に、必須列を欠いたヘッダの CSV を置く。
    (tmp_path / filename).write_text("WrongColumn,Other\nfoo,bar\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    with pytest.raises(RuntimeError):
        loader()


@pytest.mark.parametrize("loader, filename", LOADERS)
def test_loader_raises_on_empty_file(loader, filename, monkeypatch, tmp_path):
    """空ファイル (有効行0件) でも空データで起動を続けず RuntimeError にする。"""

    (tmp_path / filename).write_text("", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    with pytest.raises(RuntimeError):
        loader()


def test_dockerfile_copies_all_fail_fast_csv_files() -> None:
    """Cloud Run 起動時に必要な Fail-Fast CSV を Docker イメージへ同梱する。"""

    dockerfile_text = Path("Dockerfile").read_text(encoding="utf-8")
    required_filenames = {filename for _loader, filename in LOADERS}
    missing_filenames = sorted(
        filename for filename in required_filenames if filename not in dockerfile_text
    )
    assert missing_filenames == [], (
        "Dockerfile に同梱されていない Fail-Fast CSV があります: "
        + ", ".join(missing_filenames)
    )


def test_cat_color_master_matches_schema_and_v9_contract() -> None:
    """cat_color_master.csv がスキーマと V9 の表示/入力契約に合っている。"""

    master_path = Path("docs/architecture/cat_color_master.csv")
    with master_path.open(encoding="utf-8-sig", newline="") as csv_file:
        rows = list(csv.DictReader(csv_file))

    errors = validate(rows, set(load_source_colors().keys()))

    assert errors == []


def test_no_ambiguous_solid_canonical_colors() -> None:
    """ソリッド(非タビー・非ポイント)の表示 canonical 色は expressed_key が一意であること。

    reverse-lookup は同一 expressed_key の候補を親名スコアで選ぶため、ソリッド色に重複命名が
    あると『Brown(≡Black)』『Silver(≡Black Smoke)』のような不完全/別名が親名次第で出力される
    (実機で繰り返し見つかった粗)。タビー/度合いの正当な衝突は agouti=tabby・pattern 差なので
    対象外。既知の同義・特殊 (AOC / キャリコ同義 / Cameo 通称 / Van 略記) は許可リストで明示する。
    """
    from collections import defaultdict

    from cat_breeding_simulator.color_master import COLOR_MASTER
    from cat_breeding_simulator.master_data import (
        COLOR_BASE_LOCI,
        expressed_genotype_key,
    )

    groups: dict[tuple, list[str]] = defaultdict(list)
    for name, entries in COLOR_BASE_LOCI.items():
        resolved = COLOR_MASTER.resolve(name)
        if resolved is None or resolved.status != "canonical":
            continue
        entry = entries[0]
        loci = dict(entry.autosomal)
        loci["O"] = entry.o
        sex = "male" if "Y" in entry.o else "female"
        key = expressed_genotype_key(loci, sex)
        # agouti=solid かつ c_state=full (ポイント/セピア除く) のみ対象。
        if key[3] != "solid" or key[4] != "full":
            continue
        groups[key].append(name)

    # 既知の同義・特殊 (レビュー済で許容)。新たな重複はここに無ければ落ちる。
    allowed = {
        frozenset({"Black", "Black(A.O.C)", "Black(AOC)"}),  # AOC 特殊表示
        frozenset({"Cameo", "Cameo Smoke"}),  # 赤シルバー通称
        frozenset({"Cameo-White", "Cameo Red Smoke-White"}),
        frozenset({"Cameo-White Van", "Cameo Red Smoke-White Van"}),
        frozenset({"Van Calico", "Tortoiseshell-White Van"}),  # キャリコ同義
        frozenset({"Dilute Calico Van", "Blue Cream-White Van"}),
        frozenset({"Blue Cream Smoke-White Van", "Blue Silver Pt T-W Van"}),  # 既知エッジ(Van略記)
    }
    offenders = [
        names
        for names in groups.values()
        if len(names) > 1 and frozenset(names) not in allowed
    ]
    assert not offenders, (
        "ソリッド色に重複命名 (bare名バグの疑い)。canonical を1つに畳むか許可リストへ: "
        + "; ".join(str(v) for v in offenders)
    )
