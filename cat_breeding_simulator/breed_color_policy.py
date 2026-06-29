"""猫種ごとのカラー候補方針 (cat_breed_color_policy.csv) の読み込み。

このモジュールは UI/API の候補制御だけを担当する。メンデル計算や
cat_breed_genetic_map.csv の固定遺伝子制約には混ぜない。
"""

from __future__ import annotations

import csv
import os
import re
from dataclasses import dataclass

from cat_breeding_simulator.color_master import COLOR_MASTER, InputColorOption, normalize_color_name


@dataclass(frozen=True, slots=True)
class BreedColorPolicy:
    """1猫種分のカラー候補方針。"""

    breed: str
    current_breed_key: str
    policy_status: str
    fixed_genetic_policy: str
    allowed_color_policy: str
    excluded_color_policy: str
    display_name_policy: str
    out_of_scope_notes: str
    implementation_notes: str


_POLICY_COLUMNS: tuple[str, ...] = (
    "Breed",
    "CurrentBreedKey",
    "PolicyStatus",
    "FixedGeneticPolicy",
    "AllowedColorPolicy",
    "ExcludedColorPolicy",
    "DisplayNamePolicy",
    "OutOfScopeNotes",
    "ImplementationNotes",
)

_IGNORED_POLICY_TOKENS: frozenset[str] = frozenset({"", "aoc"})
_POINT_BICOLOR_LABEL = "Point Bi-Color"
_POINT_MITTED_LABEL = "Point Mitted"

# CSV 上の猫種別呼称を、現行 cat_color_master.csv の canonical 入力名へ寄せる。
# 方針 CSV を UI 候補へ展開するための橋渡しであり、遺伝子型制約ではない。
_POLICY_TERM_ALIASES: dict[str, tuple[str, ...]] = {
    "Sable Brown": ("Sable",),
    "Brown": ("Chocolate",),
    "Tortoiseshell": ("Tortoiseshell", "Tortie"),
    "Brown Tortie": ("Chocolate Tortie",),
    "Lavender": ("Lilac",),
    "Lavender Spotted": ("Lilac Spotted",),
    "Lavender Silver Spotted": ("Lilac Silver Spotted",),
    "Tawny Spotted": ("Brown Spotted Tabby",),
    "Bronze": ("Brown Tabby",),
    "Sepia Agouti": ("Sepia Agouti",),
}


def _load_policy_rows() -> list[dict[str, str]]:
    """猫種カラー方針 CSV を fail-fast で読む。"""

    filename = "cat_breed_color_policy.csv"
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
                    reader = csv.DictReader(f)
                    if reader.fieldnames is None:
                        rows: list[dict[str, str]] = []
                    else:
                        missing = [column for column in _POLICY_COLUMNS if column not in reader.fieldnames]
                        if missing:
                            raise RuntimeError(
                                f"{filename} の必須列が不足しています: {', '.join(missing)}"
                            )
                        rows = [
                            {column: (row.get(column) or "").strip() for column in _POLICY_COLUMNS}
                            for row in reader
                            if row.get("Breed")
                        ]
            except (OSError, UnicodeDecodeError, csv.Error) as exc:
                raise RuntimeError(
                    f"{filename} の読み込みに失敗しました ({path}): {exc}"
                ) from exc
            if not rows:
                raise RuntimeError(f"{filename} に有効なデータがありません ({path})。")
            return rows
    raise RuntimeError(
        f"{filename} が見つかりません (起動を中止)。探索パス: {paths_to_try}"
    )


def _policy_from_row(row: dict[str, str]) -> BreedColorPolicy:
    """CSV 行を型付きの方針へ変換する。"""

    return BreedColorPolicy(
        breed=row["Breed"],
        current_breed_key=row["CurrentBreedKey"],
        policy_status=row["PolicyStatus"],
        fixed_genetic_policy=row["FixedGeneticPolicy"],
        allowed_color_policy=row["AllowedColorPolicy"],
        excluded_color_policy=row["ExcludedColorPolicy"],
        display_name_policy=row["DisplayNamePolicy"],
        out_of_scope_notes=row["OutOfScopeNotes"],
        implementation_notes=row["ImplementationNotes"],
    )


def _policy_key(policy: BreedColorPolicy) -> str:
    """現在の計算エンジンで使う猫種キーを正規化する。"""

    return policy.current_breed_key or policy.breed


def _split_policy_terms(value: str) -> list[str]:
    """方針カラムの `|` 区切りを、候補展開用トークンへ分解する。"""

    first_sentence = value.split(";", maxsplit=1)[0]
    terms: list[str] = []
    for raw_term in first_sentence.split("|"):
        term = raw_term.strip()
        term = re.sub(r"\s+only$", "", term, flags=re.IGNORECASE).strip()
        if normalize_color_name(term) in _IGNORED_POLICY_TOKENS:
            continue
        if "=" in term:
            continue
        terms.append(term)
    return terms


def _input_options() -> list[InputColorOption]:
    """入力可能な色候補を取得する。"""

    return COLOR_MASTER.list_input_colors()


def _compact_color_key(value: str) -> str:
    """色名を部分一致用に畳み込む。"""

    return re.sub(r"[\s\-_/().,・。．]+", "", normalize_color_name(value))


def _is_point_color(value: str) -> bool:
    """Point を含む色名か。Patched の略記 Pt は master 側で展開済みなので混ざらない。"""

    return "point" in _compact_color_key(value)


def _is_point_white(value: str) -> bool:
    """一般表記の Point-White 系か。"""

    key = _compact_color_key(value)
    return "pointwhite" in key


def _is_point_bicolor(value: str) -> bool:
    """Ragdoll / Snowshoe 文脈の Point Bi-Color 系か。"""

    key = _compact_color_key(value)
    return "pointbicolor" in key or "pointvanbicolor" in key


def _is_point_mitted(value: str) -> bool:
    """Ragdoll / Snowshoe 文脈の Point Mitted 系か。"""

    return "pointmitted" in _compact_color_key(value)


def _is_plain_point(value: str) -> bool:
    """白斑表記を伴わない通常の Point 系か。"""

    return (
        _is_point_color(value)
        and not _is_point_white(value)
        and not _is_point_bicolor(value)
        and not _is_point_mitted(value)
    )


def _append_color(seen: set[str], ordered: list[str], color: str) -> None:
    """重複を保ちながら候補へ追加する。"""

    if color not in seen:
        seen.add(color)
        ordered.append(color)


def _append_matching_options(
    seen: set[str],
    ordered: list[str],
    predicate,
) -> None:
    """入力候補のうち predicate に合うものを追加する。"""

    for option in _input_options():
        if predicate(option.value):
            _append_color(seen, ordered, option.value)


def _append_exact_term(seen: set[str], ordered: list[str], term: str) -> None:
    """方針 CSV の単独色名を canonical 入力名へ解決して追加する。"""

    aliases = _POLICY_TERM_ALIASES.get(term, (term,))
    for alias in aliases:
        resolved = COLOR_MASTER.resolve(alias)
        if resolved is not None and resolved.input_allowed:
            _append_color(seen, ordered, resolved.primary_name)
            return


def _append_allowed_term(seen: set[str], ordered: list[str], term: str) -> bool:
    """方針トークンを候補へ展開する。展開できたら True を返す。"""

    if term == "Point 系":
        _append_matching_options(seen, ordered, _is_plain_point)
        return True
    if term == "Point & White":
        _append_matching_options(seen, ordered, _is_point_white)
        return True
    if term == _POINT_BICOLOR_LABEL:
        _append_matching_options(seen, ordered, _is_point_bicolor)
        return True
    if term == _POINT_MITTED_LABEL:
        _append_matching_options(seen, ordered, _is_point_mitted)
        return True
    if term == "Point 系以外":
        _append_matching_options(seen, ordered, lambda value: not _is_point_color(value))
        return True

    before = len(ordered)
    _append_exact_term(seen, ordered, term)
    return len(ordered) > before


def _policy_for_breed(breed_key: str) -> BreedColorPolicy | None:
    """現在の猫種キーに一致する方針を返す。"""

    normalized = breed_key.casefold()
    return _BREED_COLOR_POLICIES.get(normalized)


def allowed_color_names_for_breed(breed_key: str) -> list[str] | None:
    """猫種方針 CSV から UI/API 候補の色名一覧を返す。

    方針が無い、または現行 master に展開できない場合は None を返し、呼び出し側が
    従来の遺伝制約ベース候補へフォールバックできるようにする。
    """

    policy = _policy_for_breed(breed_key)
    if policy is None:
        return None

    seen: set[str] = set()
    ordered: list[str] = []
    for term in _split_policy_terms(policy.allowed_color_policy):
        _append_allowed_term(seen, ordered, term)

    if not ordered and "Point 系" in policy.excluded_color_policy:
        _append_matching_options(seen, ordered, lambda value: not _is_point_color(value))

    return sorted(ordered) if ordered else None


_BREED_COLOR_POLICIES: dict[str, BreedColorPolicy] = {
    _policy_key(policy).casefold(): policy
    for policy in (_policy_from_row(row) for row in _load_policy_rows())
    if _policy_key(policy)
}
