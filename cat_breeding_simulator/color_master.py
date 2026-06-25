"""色柄概念マスター (cat_color_master.csv) の読み込みと名前解決レイヤ。

責務は「名前の正規化」のみ。遺伝計算ロジック (engine.py) は変更しない。

提供する機能:
  - 入力色名 (PrimaryName / Aliases / SourceNames) を canonical 概念へ解決する
    (Status=alias は CanonicalColorId の canonical 行へ寄せる)。
  - 計算結果の色名を canonical PrimaryName へ正規化する。

正本は `docs/architecture/cat_color_master.csv`。仕様は `cat_color_master_schema.md`。
ファイルが見つからない場合は空マスタとして動作し、呼び出し側は従来挙動へフォールバックする。
"""

from __future__ import annotations

import csv
import os
import re
from dataclasses import dataclass
from functools import lru_cache

# 略称・タイポの展開。突合用キーで Pt/Mc/Sp/Tc/-W 等の表記揺れを master の正規表記へ寄せる。
# scripts/build_cat_color_master.py の expand_abbreviations と整合させること
# (どちらかを変えたら両方を合わせる)。
_ABBREV_SUBS: tuple[tuple[str, str], ...] = (
    (r"\bBrowm\b", "Brown"),
    (r"\bTobie\b", "Torbie"),
    (r"\bP-F\b", "Peke-Face"),
    (r"\bBi-C\b", "Bi-Color"),
    (r"-W Van\b", "-White Van"),
    (r"\bT-W\b", "Tabby-White"),
    (r"Tabby-W\b", "Tabby-White"),
    (r"-W\b", "-White"),
    (r"\bMc\b", "Mackerel"),
    (r"\bSp\b", "Spotted"),
    (r"\bTc\b", "Ticked"),
    (r"\bPt\b", "Patched"),
    (r"\bChoco\b", "Chocolate"),
)


@lru_cache(maxsize=4096)
def normalize_color_name(name: str) -> str:
    """色名を突合用キーへ正規化する (略称展開 + 空白整理 + casefold)。

    出力命名の後処理で繰り返し呼ばれるため結果をキャッシュする (純粋関数)。
    """

    text = re.sub(r"\s+", " ", name.strip())
    for pattern, repl in _ABBREV_SUBS:
        text = re.sub(pattern, repl, text, flags=re.IGNORECASE)
    text = re.sub(r"\s+", " ", text).strip()
    return text.casefold()


def _split_pipe(value: str) -> list[str]:
    """master の `|` 区切りカラム (Aliases / SourceNames) を分解する。"""

    return [item.strip() for item in (value or "").split("|") if item.strip()]


@dataclass(frozen=True, slots=True)
class ResolvedColor:
    """入力色名の解決結果。"""

    matched_color_id: str
    canonical_color_id: str
    primary_name: str               # canonical 概念の表示名
    status: str                     # canonical / alias / breed_specific / review / excluded
    breed_context: str
    display_allowed: bool
    input_allowed: bool
    # engine (PHENOTYPE_GENOTYPES) へ渡せる候補名。canonical 概念を優先した順序。
    engine_candidate_names: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class InputColorOption:
    """入力サジェスト用の 1 色エントリ。"""

    value: str                      # 送信に用いる canonical PrimaryName
    status: str                     # canonical / breed_specific
    # master の BreedContext をそのまま保持する (一般色は "general"、猫種固有色は猫種名)。
    # API 層で "general" を "" へ正規化する (api.colors_endpoint)。
    breed_context: str
    sex_restriction: str            # female_only / unrestricted
    # 突合用キー群 (PrimaryName / Aliases / SourceNames / 略称 / 畳み込んだ alias 名)。
    keywords: tuple[str, ...]


class ColorMaster:
    """cat_color_master.csv を索引し、名前解決・正規化を提供する。"""

    def __init__(self, rows: list[dict[str, str]]):
        self._by_id: dict[str, dict[str, str]] = {}
        self._by_name: dict[str, dict[str, str]] = {}

        for row in rows:
            color_id = row.get("ColorId", "")
            if color_id:
                self._by_id[color_id] = row

        # 索引は PrimaryName を最優先し、次に Aliases、最後に SourceNames を積む
        # (setdefault による先勝ち)。これにより別行の SourceName 衝突より PrimaryName を優先する。
        for row in rows:
            self._by_name.setdefault(normalize_color_name(row.get("PrimaryName", "")), row)
        for row in rows:
            for alias in _split_pipe(row.get("Aliases", "")):
                self._by_name.setdefault(normalize_color_name(alias), row)
        for row in rows:
            for source in _split_pipe(row.get("SourceNames", "")):
                if source.startswith("["):  # "[map] ..." 等のマーカーは候補にしない
                    continue
                self._by_name.setdefault(normalize_color_name(source), row)

    def _engine_candidates(self, matched: dict[str, str], canonical: dict[str, str]) -> tuple[str, ...]:
        names: list[str] = [canonical.get("PrimaryName", "")]
        names += [s for s in _split_pipe(canonical.get("SourceNames", "")) if not s.startswith("[")]
        names.append(matched.get("PrimaryName", ""))
        names += [s for s in _split_pipe(matched.get("SourceNames", "")) if not s.startswith("[")]
        seen: set[str] = set()
        ordered: list[str] = []
        for name in names:
            if name and name not in seen:
                seen.add(name)
                ordered.append(name)
        return tuple(ordered)

    def resolve(self, name: str) -> ResolvedColor | None:
        """色名を解決する。未登録なら None を返す。"""

        row = self._by_name.get(normalize_color_name(name))
        if row is None:
            return None
        canonical_id = row.get("CanonicalColorId") or row["ColorId"]
        canonical = self._by_id.get(canonical_id, row)
        return ResolvedColor(
            matched_color_id=row["ColorId"],
            canonical_color_id=canonical_id,
            primary_name=canonical.get("PrimaryName", row.get("PrimaryName", name)),
            status=row.get("Status", ""),
            breed_context=row.get("BreedContext", ""),
            display_allowed=row.get("DisplayAllowed", "") == "true",
            input_allowed=row.get("InputAllowed", "") == "true",
            engine_candidate_names=self._engine_candidates(row, canonical),
        )

    def canonical_name(self, name: str) -> str:
        """出力色名を canonical PrimaryName へ正規化する。未登録なら原名を返す。"""

        resolved = self.resolve(name)
        return resolved.primary_name if resolved is not None else name

    def list_input_colors(self) -> list[InputColorOption]:
        """入力サジェスト用の色一覧を返す。

        - 対象は InputAllowed=true かつ Status が canonical / breed_specific の行
          (alias 行は単独の選択肢にせず、対応 canonical の keywords へ畳み込む)。
        - keywords には PrimaryName / Aliases / SourceNames に加え、その canonical を
          指す alias 行の名前も含める (例: "Ebony" で "Black" を引けるようにする)。
        - 略称 (SourceNames の "Pt"/"Sp" 等) もそのまま keywords に入るため、略称入力で
          正式名を絞り込める。
        """

        # alias 行を canonical ColorId 単位で集約する。
        alias_names: dict[str, list[str]] = {}
        for row in self._by_id.values():
            if row.get("Status", "") != "alias":
                continue
            canonical_id = row.get("CanonicalColorId") or row.get("ColorId", "")
            names = [row.get("PrimaryName", "")]
            names += [s for s in _split_pipe(row.get("SourceNames", "")) if not s.startswith("[")]
            alias_names.setdefault(canonical_id, []).extend(name for name in names if name)

        options: list[InputColorOption] = []
        seen: set[str] = set()
        for row in self._by_id.values():
            if row.get("InputAllowed", "") != "true":
                continue
            if row.get("Status", "") not in ("canonical", "breed_specific"):
                continue
            primary = row.get("PrimaryName", "")
            if not primary or primary in seen:
                continue
            seen.add(primary)

            keywords: list[str] = [primary]
            keywords += _split_pipe(row.get("Aliases", ""))
            keywords += [s for s in _split_pipe(row.get("SourceNames", "")) if not s.startswith("[")]
            keywords += alias_names.get(row.get("ColorId", ""), [])
            # 重複を順序保持で除去する。
            ordered = tuple(dict.fromkeys(keyword for keyword in keywords if keyword))

            options.append(
                InputColorOption(
                    value=primary,
                    status=row.get("Status", ""),
                    breed_context=row.get("BreedContext", ""),
                    sex_restriction=row.get("SexRestriction", ""),
                    keywords=ordered,
                )
            )

        options.sort(key=lambda option: option.value)
        return options


def _load_master_rows() -> list[dict[str, str]]:
    filename = "cat_color_master.csv"
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
                    return [dict(row) for row in csv.DictReader(f) if row.get("ColorId")]
            except Exception:
                return []
    return []


# モジュール読み込み時に索引を構築する (engine から参照する単一インスタンス)。
COLOR_MASTER = ColorMaster(_load_master_rows())
