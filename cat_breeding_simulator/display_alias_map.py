"""表示名マスタ (cat_color_display_alias_map.csv) の読み込みと表示名解決レイヤ。

責務は「猫種・表示文脈に応じた表示名の解決」のみ。遺伝計算ロジック (engine.py) は変更しない。

提供する機能:
  - エンジンが出力する内部標準表現型名 (canonical 正規化済み) を、猫種別呼称へ変換する
    (例: Abyssinian の Brown Ticked Tabby -> Ruddy、Oriental の Black -> Ebony)。
  - 一般表示 (猫種未指定 / 猫種が Van を許可しない) の白斑正規化 (Van -> -White、データ正本 §5.2)。

正本は `docs/architecture/cat_color_display_alias_map.csv`。仕様はデータ正本 V9 §4。
ファイルが見つからない場合は空マスタとして動作し、入力名をそのまま返す (従来挙動へフォールバック)。

設計上の注意:
  - 本レイヤは COLOR_MASTER.canonical_name による正規化の「後」に適用する。
    Ebony/Chestnut/Lavender は master では Black/Chocolate/Lilac の alias であり、
    canonical 正規化を後段に置くと猫種別呼称が一般名へ戻されてしまうため。
  - よって CanonicalPhenotype 列にはエンジンが実際に出力する内部表現型名 (canonical 形) を置く。
"""

from __future__ import annotations

import csv
import os
from dataclasses import dataclass
from functools import lru_cache

# 白斑接尾辞。長い順に判定する (「-White Van」を「-White」より先に剥がす)。
_WHITE_SUFFIXES: tuple[str, ...] = ("-White Van", "-White")


@lru_cache(maxsize=4096)
def _key(name: str) -> str:
    """突合用キー (空白整理 + casefold)。"""

    return " ".join(name.split()).casefold()


def _split_white_suffix(name: str) -> tuple[str, str]:
    """色名から白斑接尾辞 (-White / -White Van) を分離する。無ければ ("name", "")。"""

    for suffix in _WHITE_SUFFIXES:
        if name.endswith(suffix):
            return name[: -len(suffix)].rstrip(), suffix
    return name, ""


@dataclass(frozen=True, slots=True)
class DisplayAliasRow:
    """表示名マスタ 1 行 (使用カラムのみ)。"""

    canonical_phenotype: str
    breed: str
    breed_specific_display_name: str
    display_context: str


class DisplayAliasMap:
    """cat_color_display_alias_map.csv を索引し、表示名解決を提供する。"""

    def __init__(self, rows: list[dict[str, str]]):
        # (CanonicalPhenotype キー, Breed キー) -> 猫種別表示名。breed_specific 行のみ収録する。
        self._breed_specific: dict[tuple[str, str], str] = {}
        # CSV に現れる Breed 値の一覧 (入力 breed への部分一致照合に使う)。
        self._breed_values: list[str] = []
        seen_breeds: set[str] = set()

        for raw in rows:
            row = DisplayAliasRow(
                canonical_phenotype=raw.get("CanonicalPhenotype", "").strip(),
                breed=raw.get("Breed", "").strip(),
                breed_specific_display_name=raw.get("BreedSpecificDisplayName", "").strip(),
                display_context=raw.get("DisplayContext", "").strip(),
            )
            if row.display_context != "breed_specific":
                continue
            if not (row.canonical_phenotype and row.breed and row.breed_specific_display_name):
                continue
            self._breed_specific[(_key(row.canonical_phenotype), _key(row.breed))] = (
                row.breed_specific_display_name
            )
            if row.breed not in seen_breeds:
                seen_breeds.add(row.breed)
                self._breed_values.append(row.breed)

    def _matching_breed_keys(self, breed: str) -> list[str]:
        """入力 breed に部分一致する CSV Breed 値のキー一覧 (例: 'Oriental Shorthair' -> 'oriental')。"""

        breed_key = _key(breed)
        return [_key(value) for value in self._breed_values if _key(value) in breed_key]

    def _resolve_breed_specific(self, name: str, breed: str) -> str | None:
        """猫種別表示名を完全名で解決する。未登録なら None。"""

        for breed_key in self._matching_breed_keys(breed):
            display = self._breed_specific.get((_key(name), breed_key))
            if display is not None:
                return display
        return None

    def resolve_display_name(self, name: str, breed: str | None) -> str:
        """内部表現型名 (canonical 形) を表示名へ解決する。

        手順:
          1. 猫種指定があれば、白斑込みの完全名を猫種別呼称へ変換する。
          2. 白斑接尾辞 (-White / -White Van) を分離する。
          3. 猫種指定があれば、基底名 (接尾辞除去後) を猫種別呼称へ変換する。
          4. 一般表示の Van 正規化 (§5.2): 猫種が Van を許可しない限り Van を落として -White にする。
          5. 接尾辞を再付与して返す。
        """

        if breed:
            display = self._resolve_breed_specific(name, breed)
            if display is not None:
                return display

        core, suffix = _split_white_suffix(name)

        if breed:
            display = self._resolve_breed_specific(core, breed)
            if display is not None:
                core = display

        # データ正本 §5.2: 一般表示 (および Van 非許可猫種) では Van を -White に正規化する。
        # 本マスタには Van を許可する猫種行が無いため、Van 接尾辞は常に -White へ寄せる。
        if suffix == "-White Van":
            suffix = "-White"

        return f"{core}{suffix}"


def _load_map_rows() -> list[dict[str, str]]:
    filename = "cat_color_display_alias_map.csv"
    paths_to_try = [
        filename,
        os.path.join("docs", "architecture", filename),
        os.path.join(os.path.dirname(os.path.dirname(__file__)), "docs", "architecture", filename),
        os.path.join(os.path.dirname(os.path.dirname(__file__)), filename),
    ]
    for path in paths_to_try:
        if os.path.exists(path):
            try:
                with open(path, mode="r", encoding="utf-8-sig", newline="") as f:
                    rows = [dict(row) for row in csv.DictReader(f) if row.get("AliasId")]
            except (OSError, UnicodeDecodeError, csv.Error) as exc:
                raise RuntimeError(
                    f"{filename} の読み込みに失敗しました ({path}): {exc}"
                ) from exc
            # Fail-Fast: 空ファイル・ヘッダ不正・AliasId 列欠落だと有効行 0 件で空マスタになる。
            if not rows:
                raise RuntimeError(
                    f"{filename} に有効なデータがありません ({path})。"
                    " 空ファイル・ヘッダ不正・AliasId 列の欠落の可能性があります。"
                )
            return rows
    # Fail-Fast: 表示名マスタを欠くと猫種別呼称/白斑正規化が無言で無効化される。起動時に落とす。
    raise RuntimeError(
        f"{filename} が見つかりません (起動を中止)。CSV のコピー漏れ等を確認してください。"
        f" 探索パス: {paths_to_try}"
    )


# モジュール読み込み時に索引を構築する (engine から参照する単一インスタンス)。
DISPLAY_ALIAS_MAP = DisplayAliasMap(_load_map_rows())
