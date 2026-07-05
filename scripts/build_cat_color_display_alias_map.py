"""表示名マスタ唯一正本 cat_color_display_alias_map.csv を生成するビルドスクリプト。

目的:
    エンジンが出力する「内部標準表現型名」(例: Brown Ticked Tabby / Black) を、
    猫種・表示文脈に応じた正しい表示名 (例: Abyssinian の Ruddy、Oriental の Ebony) へ
    変換するための表示名マスタ docs/architecture/cat_color_display_alias_map.csv を生成する。

設計方針 (データ正本 V9 §4 / §1.1 / §1.2 に準拠):
    - 遺伝定義 (cat_color_genetic_map.csv) と表示名定義 (本 CSV) を分離する。
    - 表示名変換ロジックをコードに固定値で書かず、本 CSV に集約する (§1.1)。
    - CanonicalPhenotype はエンジンが実際に出力する内部表現型名で記述する
      (master の CanonicalColorId とは別概念。逆引きの突合キーになるため一致が必須)。
    - 猫種別呼称 (Oriental: Ebony/Chestnut/Lavender 系、Abyssinian/Somali: Ruddy 系、
      Tonkinese: Solid class 系) を DisplayContext=breed_specific として収録する。
      Any/一般表示には出さない。
    - シード範囲は「名指し例 + 経路網羅」: 名指しされた猫種について、エンジンが normal_mode で
      実際に到達し得る内部表現型 (solid / smoke / tabby / silver_tabby と -White 合成) を覆う。

このスクリプトは engine.py / API ロジック / 運用系ファイルを一切変更しない。

実行:
    PYTHONPATH=. python scripts/build_cat_color_display_alias_map.py
"""

from __future__ import annotations

import csv
import os

# ---------------------------------------------------------------------------
# パス定義 (リポジトリルートからの相対)
# ---------------------------------------------------------------------------
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARCH_DIR = os.path.join(ROOT, "docs", "architecture")
OUTPUT_CSV = os.path.join(ARCH_DIR, "cat_color_display_alias_map.csv")

# §4.2 必須カラム (順序固定)
COLUMNS: tuple[str, ...] = (
    "AliasId",
    "CanonicalPhenotype",
    "GeneralDisplayName",
    "Breed",
    "BreedSpecificDisplayName",
    "Registry",
    "OfficialStatus",
    "DisplayContext",
    "Priority",
    "Notes",
)


# ---------------------------------------------------------------------------
# 変換ルール表
#
# (CanonicalPhenotype=エンジン内部名, BreedSpecificDisplayName=猫種別表示名)。
# GeneralDisplayName は「Any/一般表示で使う名前」= 内部名そのまま。
# -White / -White Van の合成は resolver 側の接尾辞 peel が担うため、ここでは基底名のみ列挙する。
# ---------------------------------------------------------------------------

# Abyssinian / Somali: ティックドタビーを猫種別呼称へ。
#   Brown/Black Ticked Tabby -> Ruddy、Blue -> Blue、Fawn -> Fawn。
#   Abyssinian/Somali の「Red」(Sorrel) はシナモン (bl/bl) のティックドタビーなので、
#   シナモン系ティックド (Cinnamon Ticked Tabby) を猫種呼称「Red」で表示する。
#   "* Silver Ticked Tabby" は " Ticked Tabby" を落として "* Silver" にする (現行の総称ストリップ相当)。
ABY_BREEDS: tuple[str, ...] = ("Abyssinian", "Somali")
ABY_RULES: tuple[tuple[str, str], ...] = (
    ("Brown Ticked Tabby", "Ruddy"),
    ("Black Ticked Tabby", "Ruddy"),
    ("Blue Ticked Tabby", "Blue"),
    ("Cinnamon Ticked Tabby", "Red"),
    ("Fawn Ticked Tabby", "Fawn"),
    # 一般オレンジの Red Ticked Tabby も Aby 文脈では「Red」表示にする (通常は出現しない冗長保険)。
    ("Red Ticked Tabby", "Red"),
    ("Silver Ticked Tabby", "Silver"),
    ("Blue Silver Ticked Tabby", "Blue Silver"),
    ("Chocolate Silver Ticked Tabby", "Chocolate Silver"),
    ("Lilac Silver Ticked Tabby", "Lilac Silver"),
    ("Cinnamon Silver Ticked Tabby", "Cinnamon Silver"),
    ("Fawn Silver Ticked Tabby", "Fawn Silver"),
)

# Oriental (Shorthair / Longhair): 基色の猫種別呼称復元。
#   Black 系 -> Ebony、Chocolate 系 -> Chestnut、Lilac 系 -> Lavender。
#   エンジンは黒アグーチのタビーを "Brown Tabby"、黒シルバータビーを "Silver Tabby" と出力する点に注意。
ORI_BREEDS: tuple[str, ...] = ("Oriental",)
ORI_RULES: tuple[tuple[str, str], ...] = (
    # Black -> Ebony
    ("Black", "Ebony"),
    ("Black Smoke", "Ebony Smoke"),
    ("Brown Tabby", "Ebony Tabby"),
    ("Silver Tabby", "Ebony Silver Tabby"),
    # Chocolate -> Chestnut
    ("Chocolate", "Chestnut"),
    ("Chocolate Smoke", "Chestnut Smoke"),
    ("Chocolate Tabby", "Chestnut Tabby"),
    ("Chocolate Silver Tabby", "Chestnut Silver Tabby"),
    # Lilac -> Lavender
    ("Lilac", "Lavender"),
    ("Lilac Smoke", "Lavender Smoke"),
    ("Lilac Tabby", "Lavender Tabby"),
    ("Lilac Silver Tabby", "Lavender Silver Tabby"),
    ("Brown Patched Tabby", "Ebony Patched Tabby"),
    ("Lilac Patched Tabby", "Lavender Patched Tabby"),
    ("Lilac Spotted Tabby", "Lavender Spotted Tabby"),
    ("Chocolate Patched Tabby", "Chestnut Patched Tabby"),
    ("Silver Ticked Tabby", "Ebony Silver Ticked Tabby"),
)

# Japanese Bobtail: 三毛系を日本猫文脈の呼称へ。
# Smoke Mike は白斑込みの別名なので、CanonicalPhenotype も -White 付きで登録する。
JBT_BREEDS: tuple[str, ...] = ("Japanese Bobtail",)
JBT_RULES: tuple[tuple[str, str], ...] = (
    ("Calico", "Mike"),
    ("Dilute Calico", "Dilute Mike"),
    ("Tortie Smoke-White", "Smoke Mike"),
    ("Blue Cream Smoke-White", "Dilute Smoke Mike"),
)

# Burmese: 内部の sepia dilute solid 名を登録表示へ復元する。
BUR_BREEDS: tuple[str, ...] = ("Burmese",)
BUR_RULES: tuple[tuple[str, str], ...] = (
    ("Blue Solid", "Blue"),
)

# Tonkinese: engine 内部の Sepia/Burmese 系名を Solid class 表示へ復元する。
TON_BREEDS: tuple[str, ...] = ("Tonkinese",)
TON_RULES: tuple[tuple[str, str], ...] = (
    ("Sable", "Natural Solid"),
    ("Champagne", "Champagne Solid"),
    ("Platinum", "Platinum Solid"),
)


def _rows() -> list[dict[str, str]]:
    """変換ルール表から CSV 行 (dict) を生成する。AliasId は決定的に採番する。"""

    rows: list[dict[str, str]] = []
    alias_id = 1

    def add(canonical: str, general: str, breed: str, breed_name: str, note: str) -> None:
        nonlocal alias_id
        rows.append(
            {
                "AliasId": str(alias_id),
                "CanonicalPhenotype": canonical,
                "GeneralDisplayName": general,
                "Breed": breed,
                "BreedSpecificDisplayName": breed_name,
                "Registry": "",
                "OfficialStatus": "official",
                "DisplayContext": "breed_specific",
                "Priority": "20",
                "Notes": note,
            }
        )
        alias_id += 1

    for breed in ABY_BREEDS:
        for canonical, breed_name in ABY_RULES:
            add(
                canonical,
                canonical,
                breed,
                breed_name,
                f"{breed} のティックドタビー呼称。一般表示は CanonicalPhenotype のまま。",
            )

    for breed in ORI_BREEDS:
        for canonical, breed_name in ORI_RULES:
            add(
                canonical,
                canonical,
                breed,
                breed_name,
                (
                    f"{breed} 固有呼称復元 (-White 接尾辞は解決層が再付与)。"
                    "一般表示は CanonicalPhenotype のまま。"
                    if canonical == "Silver Ticked Tabby"
                    else f"{breed} 固有呼称復元。一般表示は CanonicalPhenotype のまま。"
                ),
            )

    for breed in JBT_BREEDS:
        for canonical, breed_name in JBT_RULES:
            add(
                canonical,
                canonical,
                breed,
                breed_name,
                f"{breed} の三毛系呼称。一般表示は CanonicalPhenotype のまま。",
            )

    for breed in BUR_BREEDS:
        for canonical, breed_name in BUR_RULES:
            add(
                canonical,
                canonical,
                breed,
                breed_name,
                f"{breed} のセピア希釈呼称。一般表示は CanonicalPhenotype のまま。",
            )

    for breed in TON_BREEDS:
        for canonical, breed_name in TON_RULES:
            add(
                canonical,
                canonical,
                breed,
                breed_name,
                f"{breed} の Solid class 呼称。一般表示は CanonicalPhenotype のまま。",
            )

    return rows


def build() -> None:
    rows = _rows()
    with open(OUTPUT_CSV, mode="w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(COLUMNS))
        writer.writeheader()
        writer.writerows(rows)
    print(f"生成完了: {OUTPUT_CSV} ({len(rows)} 行)")


if __name__ == "__main__":
    build()
