"""子猫の遺伝子型 → 人間向けの毛色名 への命名/分類レイヤ。

engine.py から「遺伝計算」とは別ドメインである命名/表示名づけを切り出したもの。
入力: 子猫の遺伝子型 (KittenGenotype) と親カラー名。出力: canonical 表示色名。

依存は data 層 (master_data) と名前正規化 (color_master / display_alias_map) のみで、
engine には依存しない (循環 import を避けるため共有型は master_data に置く)。
"""

from __future__ import annotations

import re

from cat_breeding_simulator.master_data import (
    COLOR_DEFINITIONS,
    PHENOTYPE_GENOTYPES,
    KittenGenotype,
    expressed_genotype_key,
)
from cat_breeding_simulator.color_master import COLOR_MASTER
from cat_breeding_simulator.display_alias_map import DISPLAY_ALIAS_MAP


# CSV 上の正式カラー名集合 (定数。呼び出し毎の再構築を避け import 時に1回だけ構築)。
_VALID_COLOR_NAMES: frozenset[str] = frozenset(
    definition["CoatColor"] for definition in COLOR_DEFINITIONS
)


# 通常のXYオスには出してはいけない、本来メス限定のカラー名マーカー。
# CSV側の符号ミス (例: Blue Cream を O/O で登録) に対する安全弁も兼ねる。
_FEMALE_ONLY_MARKERS: tuple[str, ...] = (
    "tortie",
    "tortoiseshell",
    "calico",
    "patched",
    "blue cream",
    "lilac cream",
    "choco cream",
)


# 発現キー (sex, expressed_key) → 候補カラー名。PHENOTYPE_GENOTYPES の逆引き表。
GENOTYPE_TO_COLOR_MAP: dict[tuple[str, tuple], list[str]] = {}


def _build_genotype_to_color_map() -> None:
    GENOTYPE_TO_COLOR_MAP.clear()
    for color, sex_dict in PHENOTYPE_GENOTYPES.items():
        for sex in ("male", "female"):
            for genotype in sex_dict[sex]:
                key = expressed_genotype_key(genotype.loci, sex)
                map_key = (sex, key)
                if map_key not in GENOTYPE_TO_COLOR_MAP:
                    GENOTYPE_TO_COLOR_MAP[map_key] = []
                if color not in GENOTYPE_TO_COLOR_MAP[map_key]:
                    GENOTYPE_TO_COLOR_MAP[map_key].append(color)


_build_genotype_to_color_map()


class PhenotypeNamer:
    """子猫の遺伝子型から表示色名を決める (CSV 逆引き → フォールバック構築 → 後処理)。"""

    def classify_phenotype(
        self, kitten: KittenGenotype, sire_color: str = "", dam_color: str = ""
    ) -> str | None:
        if sire_color and dam_color:
            matched = self.find_matching_color(kitten, sire_color, dam_color)
            if matched:
                return matched
        # CSV逆引きに名前が無い遺伝子型は標準表現型から構築する (V9 §6.1 step1)。
        # 構築できないもの (点紋/チョコ等の想定外) のみ None = 未分類として検出する。
        return self.construct_fallback_name(kitten, sire_color, dam_color)

    def construct_fallback_name(
        self, kitten: KittenGenotype, sire_color: str = "", dam_color: str = ""
    ) -> str | None:
        """CSV逆引きに無い遺伝子型を、標準表現型から構築して命名する (V9 §6.1)。

        通常モードでは B(チョコ系) と C(点紋系) を展開しないため、ここで扱うのは
        黒系(B/B)・フルカラー(C/C) の組み合わせに限られる。点紋・チョコ・シナモン等の
        想定外は None を返し、未分類として検出させる。

        ワイドバンド (Wb/-) は「非オレンジ・アグーチ」背景でのみ tipping (Shell/Shaded/
        Chinchilla/Golden) として発現する。その場合はここで命名し、未分類にしない。
        オレンジ/トーティ/ソリッドの wide は wideband が別名を持たないため通常命名へ流す
        (ソリッドでは tipping 非発現、赤系は Cameo/Cream 等の既存名で扱う)。
        tipping の濃淡 (Chinchilla/Shaded) は多遺伝子で1座位に還元できないため、親カラー名
        から推論する (タビー柄を親名から推論するのと同じ方針)。
        """

        key = expressed_genotype_key(kitten.loci, kitten.sex)
        orange, base, dilute, agouti, c_state, dom_white, spotting, silver, wideband = key

        if dom_white == "white":
            return "White"
        # 通常モードの構築対象外 (点紋系) は未分類に回す
        if c_state != "full":
            return None

        is_dilute = dilute == "dilute"
        is_agouti = agouti == "agouti"
        is_silver = silver == "silver"

        # ワイドバンド: 非オレンジ・アグーチでのみ tipping として命名する (それ以外は通常命名)。
        if wideband == "wide" and is_agouti and orange == "non_orange":
            degree = self._tipping_degree(sire_color, dam_color)
            tipped = "Silver" if is_silver else "Golden"
            base_prefix = self._wideband_base_prefix(base, is_dilute)
            name = f"{base_prefix}{degree}{tipped}"
            if spotting in ("white", "high_white"):
                name = f"{name}-White"
            return name

        # 通常モードの構築対象外 (チョコ/シナモン) は、Wb の命名を済ませた後に未分類へ回す。
        if base != "black":
            return None

        if orange == "tortie":
            if is_agouti:
                if is_silver:
                    stem = "Blue Silver" if is_dilute else "Silver"
                else:
                    stem = "Blue" if is_dilute else "Brown"
                name = f"{stem} Patched Tabby"
            else:
                if is_silver:
                    name = "Blue Cream Smoke" if is_dilute else "Tortie Smoke"
                else:
                    name = "Blue Cream" if is_dilute else "Tortoiseshell"
        else:
            is_orange = orange == "orange"
            if is_agouti:
                if is_orange:
                    if is_silver:
                        stem = "Cream Cameo" if is_dilute else "Cameo"
                    else:
                        stem = "Cream" if is_dilute else "Red"
                else:
                    if is_silver:
                        stem = "Blue Silver" if is_dilute else "Silver"
                    else:
                        stem = "Blue" if is_dilute else "Brown"
                name = f"{stem} Tabby"
            else:
                if is_orange:
                    if is_silver:
                        name = "Cream Smoke" if is_dilute else "Cameo"
                    else:
                        name = "Cream" if is_dilute else "Red"
                else:
                    if is_silver:
                        name = "Blue Smoke" if is_dilute else "Black Smoke"
                    else:
                        name = "Blue" if is_dilute else "Black"

        if spotting in ("white", "high_white"):
            # 通常モードでは Van を出さず -White に正規化 (データ正本 §5.2)
            name = f"{name}-White"
        return name

    @staticmethod
    def is_female_only_color(name: str) -> bool:
        lowered = name.lower()
        return any(marker in lowered for marker in _FEMALE_ONLY_MARKERS)

    @staticmethod
    def _wideband_base_prefix(base: str, is_dilute: bool) -> str:
        """Wb系の表示でB/D座位の基底カラーを残す接頭辞を返す。"""

        if base == "black":
            return "Blue " if is_dilute else ""
        if base == "chocolate":
            return "Lilac " if is_dilute else "Chocolate "
        if base == "cinnamon":
            return "Fawn " if is_dilute else "Cinnamon "
        return ""

    @staticmethod
    def _tipping_degree(sire_color: str, dam_color: str) -> str:
        """ワイドバンド tipping の濃淡語を親カラー名から推論する (末尾スペース込み)。

        濃淡 (Shell < Shaded < Chinchilla) は多遺伝子で genotype に還元できないため、
        親が明示している語を継承する。どちらの親も明示しなければ濃淡なし (汎用 Golden/Silver)。

        判定は単語境界で行う ("Tortoiseshell" の部分文字列 "shell" を誤検出しないため)。
        """

        text = f"{sire_color} {dam_color}".lower()
        for word, label in (("chinchilla", "Chinchilla "), ("shaded", "Shaded "), ("shell", "Shell ")):
            if re.search(rf"\b{word}\b", text):
                return label
        return ""

    def find_matching_color(
        self, kitten: KittenGenotype, sire_color: str, dam_color: str
    ) -> str | None:
        key = expressed_genotype_key(kitten.loci, kitten.sex)
        candidates = list(GENOTYPE_TO_COLOR_MAP.get((kitten.sex.lower(), key), []))
        if not candidates:
            return None

        # 通常のXYオスにトーティ・キャリコ・クリーム混合系を出さない (要件3)
        if kitten.sex.lower() == "male":
            candidates = [c for c in candidates if not self.is_female_only_color(c)]
            if not candidates:
                return None

        # 親に "Bronze" が指定されていなければ、"Bronze" を除外する
        if "Bronze" in candidates:
            if "bronze" not in sire_color.lower() and "bronze" not in dam_color.lower():
                candidates.remove("Bronze")

        if not candidates:
            return None

        if len(candidates) == 1:
            return candidates[0]

        # 同一遺伝子型に対する複数表現型名の競合解決
        priority_map = {
            "Dilute Calico": 10,
            "Calico": 10,
            "Blue Tortie-White": 5,
            "Tortoiseshell-White": 5,
        }

        sire_words = set(sire_color.lower().split())
        dam_words = set(dam_color.lower().split())
        parent_words = sire_words.union(dam_words)

        def score(color_name: str) -> int:
            base_score = priority_map.get(color_name, 0)
            color_words = color_name.lower().split()
            match_count = sum(1 for w in color_words if w in parent_words)
            return base_score + match_count * 20

        candidates.sort(key=score, reverse=True)
        return candidates[0]

    def post_process_color_name(
        self, name: str, sire_color: str, dam_color: str, breed: str | None
    ) -> str:
        name = self.clean_phenotype_name(name)
        name = self.simplify_patterns(name, sire_color, dam_color, breed)
        # 出力色名を cat_color_master.csv の canonical PrimaryName へ正規化する
        # (alias 統合・略記展開)。集計はこの canonical 名で行われ自動的にマージされる。
        name = COLOR_MASTER.canonical_name(name)
        # 猫種別表示名 (Abyssinian の Ruddy、Oriental の Ebony 等) と一般 Van 正規化を
        # cat_color_display_alias_map.csv 駆動で適用する (データ正本 §4 / §1.1)。
        # canonical 正規化の「後」に置く: Ebony/Chestnut/Lavender は master では alias のため、
        # 先に canonical 化しないと猫種別呼称が一般名へ戻ってしまう。
        name = DISPLAY_ALIAS_MAP.resolve_display_name(name, breed)
        return name

    def clean_phenotype_name(self, name: str) -> str:
        # すでにCSVに存在する正式なカラー名である場合は、誤置換を防ぐためそのまま返す
        if name in _VALID_COLOR_NAMES:
            return name

        is_silver = "Silver" in name and "Tabby" in name
        if is_silver:
            if name.startswith("Black Pt "):
                name = name.replace("Black Pt ", "Silver Pt ").replace(" Silver Tabby", " Tabby")
            elif name.startswith("Black "):
                name = name.replace("Black ", "Silver ").replace(" Silver Tabby", " Tabby")
            elif name.startswith("Blue Pt ") and not name.startswith("Blue Silver Pt "):
                name = name.replace("Blue Pt ", "Blue Silver Pt ").replace(" Silver Tabby", " Tabby")
            elif name.startswith("Blue ") and not name.startswith("Blue Silver "):
                name = name.replace("Blue ", "Blue Silver ", 1).replace(" Silver Tabby", " Tabby")
            elif name.startswith("Red "):
                name = name.replace("Red ", "Cameo ").replace(" Silver Tabby", " Tabby")
            elif name.startswith("Cream "):
                name = name.replace("Cream ", "Cream Cameo ").replace(" Silver Tabby", " Tabby")
            elif name.startswith("Chocolate "):
                name = name.replace("Chocolate ", "Chocolate Silver ").replace(" Silver Tabby", " Tabby")
            elif name.startswith("Lilac "):
                name = name.replace("Lilac ", "Lilac Silver ").replace(" Silver Tabby", " Tabby")
            elif name.startswith("Cinnamon "):
                name = name.replace("Cinnamon ", "Cinnamon Silver ").replace(" Silver Tabby", " Tabby")
            elif name.startswith("Fawn "):
                name = name.replace("Fawn ", "Fawn Silver ").replace(" Silver Tabby", " Tabby")
        else:
            if "Tabby" in name:
                if name.startswith("Black Pt "):
                    name = name.replace("Black Pt ", "Brown Pt ")
                elif name.startswith("Black "):
                    name = name.replace("Black ", "Brown ")
        return name

    def simplify_patterns(
        self, name: str, sire_color: str, dam_color: str, breed: str | None
    ) -> str:
        def _has_pattern(c_name: str, pat: str) -> bool:
            name_lower = c_name.lower()
            if pat == "mackerel":
                return "mackerel" in name_lower or "mc" in name_lower.split()
            if pat == "classic":
                return "classic" in name_lower
            if pat == "ticked":
                return "ticked" in name_lower or "tc" in name_lower.split()
            if pat == "spotted":
                return "spotted" in name_lower or "sp" in name_lower.split()
            return False

        has_mackerel = _has_pattern(sire_color, "mackerel") or _has_pattern(dam_color, "mackerel")
        has_classic = _has_pattern(sire_color, "classic") or _has_pattern(dam_color, "classic")
        has_ticked = _has_pattern(sire_color, "ticked") or _has_pattern(dam_color, "ticked")
        has_spotted = _has_pattern(sire_color, "spotted") or _has_pattern(dam_color, "spotted")

        is_ticked_breed = False
        if breed:
            breed_lower = breed.lower()
            if "abyssinian" in breed_lower or "somali" in breed_lower:
                is_ticked_breed = True

        if not has_mackerel:
            name = name.replace("Mackerel ", "").replace("Mc ", "").replace(" Mackerel", "").replace(" Mc", "")
        if not has_classic:
            name = name.replace("Classic ", "").replace(" Classic", "")
        if not has_ticked and not is_ticked_breed:
            name = name.replace("Ticked ", "").replace("Tc ", "").replace(" Ticked", "").replace(" Tc", "")
        if not has_spotted:
            name = name.replace("Spotted ", "").replace("Sp ", "").replace(" Spotted", "").replace(" Sp", "")

        name = " ".join(name.split())
        name = name.replace(" -White", "-White").replace(" - White", "-White")
        # Tabby-White が Tabby-W の置換で Tabby-Whitehite に化けるのを防ぐ避難処理
        name = name.replace("Tabby-White", "__TABBY_WHITE__")
        name = name.replace("Tabby-W", "Tabby-White")
        name = name.replace("__TABBY_WHITE__", "Tabby-White")
        name = name.replace("T-W", "Tabby-White").replace("-W Van", "-White Van")
        return name
