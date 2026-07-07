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
from cat_breeding_simulator.color_master import COLOR_MASTER, breed_context_matches
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

# 旧CSVには Cameo と同じ遺伝子型の冗長な Smoke 名が混在しているため、表示だけ統一する。
_CAMEO_DISPLAY_ALIASES: dict[str, str] = {
    "Cameo Smoke": "Cameo",
    "Cameo Red Smoke-White": "Cameo-White",
    "Cameo Red Smoke-White Van": "Cameo-White",
}


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
        self,
        kitten: KittenGenotype,
        sire_color: str = "",
        dam_color: str = "",
        breed: str | None = None,
    ) -> str | None:
        if sire_color and dam_color:
            matched = self.find_matching_color(kitten, sire_color, dam_color, breed)
            if matched:
                return matched
        # CSV逆引きに名前が無い遺伝子型は標準表現型から構築する (V9 §6.1 step1)。
        # 対応外の C 系 (Mink/Sepia) など、構築できないもののみ None = 未分類として検出する。
        return self.construct_fallback_name(kitten, sire_color, dam_color)

    def construct_fallback_name(
        self, kitten: KittenGenotype, sire_color: str = "", dam_color: str = ""
    ) -> str | None:
        """CSV逆引きに無い遺伝子型を、標準表現型から構築して命名する (V9 §6.1)。

        黒系だけでなく Chocolate/Cinnamon 系、親入力や猫種固定などで到達する Point 系も
        標準名へ落とし込む。Mink / Sepia は猫種・表示文脈の影響が強いため現段階では
        None を返し、未分類として検出させる。

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
        # Mink / Sepia は猫種・表示文脈の影響が強いため、現段階では未分類に回して検出する。
        if c_state not in ("full", "point"):
            return None

        is_dilute = dilute == "dilute"
        is_agouti = agouti == "agouti"
        is_silver = silver == "silver"

        # Point 表示では I/Wb/tipping 系の語を出さず、基底の Point 名へ寄せる。
        # 理由: Point は C座位の発色制限で体色差が隠れるため、Silver/Golden/Shaded 等を
        # 一般出力名に載せると実務上の色名として過剰分類になる。
        if c_state == "point":
            if orange == "tortie":
                name = self._tortie_name(base, is_dilute, is_agouti, False, c_state)
            elif orange == "orange":
                name = self._orange_name(is_dilute, is_agouti, False, c_state)
            else:
                name = self._non_orange_name(base, is_dilute, is_agouti, False, c_state)
            if spotting in ("white", "high_white"):
                name = f"{name}-White"
            return name

        # ワイドバンド (Wb/-): アグーチ前提で tipping として命名する。背景 (非オレンジ / 赤 /
        # トーティ) × シルバー(I) × 度合い(Chinchilla/Shell=1/8, Shaded=1/4) をマトリクスで命名する
        # (一次資料: CFA/TICA・Wikipedia)。a/a (非アグーチ) はここを通らず Smoke / ソリッドへ流す
        # (ゴールデン・スモークは存在しない = wideband + a/a はただのソリッド)。ゴールデンの赤は
        # 赤色素と同系で独立色にならないため helper が None を返し、通常命名 (赤) へフォールバックする。
        if wideband == "wide" and is_agouti:
            degree = self._tipping_degree(sire_color, dam_color)
            tipped = self._wideband_tipping_name(orange, base, is_dilute, is_silver, degree)
            if tipped is not None:
                if spotting in ("white", "high_white"):
                    tipped = f"{tipped}-White"
                return tipped

        if orange == "tortie":
            name = self._tortie_name(base, is_dilute, is_agouti, is_silver, c_state)
        else:
            is_orange = orange == "orange"
            if is_orange:
                name = self._orange_name(is_dilute, is_agouti, is_silver, c_state)
            else:
                name = self._non_orange_name(base, is_dilute, is_agouti, is_silver, c_state)

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
    def _base_color_name(base: str, is_dilute: bool) -> str:
        """B/D座位からフルカラーの基色名を返す。"""

        if base == "black":
            return "Blue" if is_dilute else "Black"
        if base == "chocolate":
            return "Lilac" if is_dilute else "Chocolate"
        if base == "cinnamon":
            return "Fawn" if is_dilute else "Cinnamon"
        return "Blue" if is_dilute else "Black"

    @staticmethod
    def _tabby_base_stem(base: str, is_dilute: bool) -> str:
        """タビー表示で使う基色名を返す (黒系は Brown 表記)。"""

        if base == "black":
            return "Blue" if is_dilute else "Brown"
        return PhenotypeNamer._base_color_name(base, is_dilute)

    @staticmethod
    def _silver_tabby_stem(base: str, is_dilute: bool) -> str:
        """Silver Tabby / Lynx Point 系の基色付き stem を返す。"""

        if base == "black":
            return "Blue Silver" if is_dilute else "Silver"
        return f"{PhenotypeNamer._base_color_name(base, is_dilute)} Silver"

    @staticmethod
    def _point_base_stem(base: str, is_dilute: bool) -> str:
        """Point 系で使う基色名を返す (黒系濃色は Seal)。"""

        if base == "black":
            return "Blue" if is_dilute else "Seal"
        return PhenotypeNamer._base_color_name(base, is_dilute)

    @staticmethod
    def _tortie_solid_stem(base: str, is_dilute: bool, is_silver: bool) -> str:
        """トーティ/スモーク系の solid stem を返す。"""

        if base == "black":
            if is_silver:
                return "Blue Cream Smoke" if is_dilute else "Tortie Smoke"
            return "Blue Cream" if is_dilute else "Tortoiseshell"
        stem = PhenotypeNamer._base_color_name(base, is_dilute)
        if is_silver:
            return f"{stem} Cream Smoke" if is_dilute else f"{stem} Tortie Smoke"
        return f"{stem} Cream" if is_dilute else f"{stem} Tortie"

    @staticmethod
    def _tortie_tabby_stem(base: str, is_dilute: bool, is_silver: bool) -> str:
        """Patched Tabby 系の stem を返す。"""

        if is_silver:
            return f"{PhenotypeNamer._silver_tabby_stem(base, is_dilute)} Patched"
        return f"{PhenotypeNamer._tabby_base_stem(base, is_dilute)} Patched"

    @staticmethod
    def _tortie_point_stem(base: str, is_dilute: bool, is_silver: bool) -> str:
        """Tortie Point 系の stem を返す。"""

        if base == "black":
            if is_silver:
                return "Blue Silver Cream" if is_dilute else "Silver Tortie"
            return "Blue Cream" if is_dilute else "Seal Tortie"
        stem = PhenotypeNamer._base_color_name(base, is_dilute)
        if is_silver:
            return f"{stem} Silver Cream" if is_dilute else f"{stem} Silver Tortie"
        return f"{stem} Cream" if is_dilute else f"{stem} Tortie"

    @staticmethod
    def _non_orange_name(
        base: str,
        is_dilute: bool,
        is_agouti: bool,
        is_silver: bool,
        c_state: str,
    ) -> str:
        """非オレンジ個体の標準名を構築する。"""

        if c_state == "point":
            stem = (
                PhenotypeNamer._silver_tabby_stem(base, is_dilute)
                if is_silver and is_agouti
                else PhenotypeNamer._point_base_stem(base, is_dilute)
            )
            return f"{stem} Lynx Point" if is_agouti else f"{stem} Point"

        if is_agouti:
            stem = (
                PhenotypeNamer._silver_tabby_stem(base, is_dilute)
                if is_silver
                else PhenotypeNamer._tabby_base_stem(base, is_dilute)
            )
            return f"{stem} Tabby"
        if is_silver:
            return f"{PhenotypeNamer._base_color_name(base, is_dilute)} Smoke"
        return PhenotypeNamer._base_color_name(base, is_dilute)

    @staticmethod
    def _orange_name(
        is_dilute: bool,
        is_agouti: bool,
        is_silver: bool,
        c_state: str,
    ) -> str:
        """オレンジ個体の標準名を構築する。B座位は赤系表現では表示名に出さない。"""

        stem = "Cream" if is_dilute else "Red"
        if c_state == "point":
            return f"{stem} Lynx Point" if is_agouti else f"{stem} Point"
        if is_agouti:
            if is_silver:
                stem = "Cream Cameo" if is_dilute else "Cameo"
            return f"{stem} Tabby"
        if is_silver:
            return "Cream Smoke" if is_dilute else "Cameo"
        return stem

    @staticmethod
    def _tortie_name(
        base: str,
        is_dilute: bool,
        is_agouti: bool,
        is_silver: bool,
        c_state: str,
    ) -> str:
        """トーティ個体の標準名を構築する。"""

        if c_state == "point":
            stem = PhenotypeNamer._tortie_point_stem(base, is_dilute, is_silver)
            return f"{stem} Lynx Point" if is_agouti else f"{stem} Point"
        if is_agouti:
            return f"{PhenotypeNamer._tortie_tabby_stem(base, is_dilute, is_silver)} Tabby"
        return PhenotypeNamer._tortie_solid_stem(base, is_dilute, is_silver)

    @staticmethod
    def _tipping_degree(sire_color: str, dam_color: str) -> str:
        """ワイドバンド tipping の度合いを親カラー名から 2 値で推論する ("chinchilla" | "shaded")。

        度合いは多遺伝子 (ポリジーン) で genotype に還元できないため親名から近似する。
        Chinchilla と Shell は同一度合い (先端 1/8) として "chinchilla" に正規化する。
        どちらの親も度合いを明示しなければ既定 "shaded" (見た目で判別しやすい方を既定とする方針)。
        表示語は背景で変える (非オレンジ=Chinchilla、赤/トーティ=Shell)。_degree_word が担う。

        判定は単語境界で行う ("Tortoiseshell" の部分文字列 "shell" を誤検出しないため)。
        """

        text = f"{sire_color} {dam_color}".lower()
        has_chinchilla = bool(re.search(r"\bchinchilla\b", text) or re.search(r"\bshell\b", text))
        has_shaded = bool(re.search(r"\bshaded\b", text))
        # 度合いが衝突 (Chinchilla と Shaded 両方) または不明のときは Shaded を既定にする。
        # 理由: 度合いはポリジーンで、チンチラ(先端1/8)は"最も強いワイドバンド量"の極。掛け合わせで
        # 量が中間へ均されると、実務上は到達しにくいチンチラより Shaded 側に落ちやすい。Chinchilla は
        # 親が Chinchilla/Shell のみを示し、かつ Shaded が無いときだけ採用する。
        if has_chinchilla and not has_shaded:
            return "chinchilla"
        return "shaded"

    @staticmethod
    def _degree_word(degree: str, orange: str) -> str:
        """度合いトークンを背景別の表示語へ。非オレンジ=Chinchilla、赤/トーティ=Shell (CFA準拠)。
        Shaded は共通。Chinchilla と Shell は同一度合い (1/8) の呼び分け。"""

        if degree == "shaded":
            return "Shaded"
        return "Chinchilla" if orange == "non_orange" else "Shell"

    def _wideband_tipping_name(
        self, orange: str, base: str, is_dilute: bool, is_silver: bool, degree: str
    ) -> str | None:
        """ワイドバンド (Wb/-) の tipping 命名。適用外なら None (通常命名へフォールバック)。

        呼び出し側でアグーチ (A/-) を保証する。命名ルール (Phase A マトリクス, CFA/TICA準拠):
          - 非オレンジ: 度合い(Chinchilla/Shaded) + Silver/Golden。base で Blue/Chocolate/Lilac 等を前置。
          - 赤(O): シルバーのみ Cameo 系 (Shell/Shaded Cameo)。ゴールデン赤は独立色にならないため None。
          - トーティ: シルバー=Shell/Shaded Tortoiseshell(濃)/Blue Cream(淡)、ゴールデンは末尾に "(Golden)"。
        """

        word = self._degree_word(degree, orange)
        if orange == "non_orange":
            tipped = "Silver" if is_silver else "Golden"
            base_prefix = self._wideband_base_prefix(base, is_dilute)
            return f"{base_prefix}{word} {tipped}"
        if orange == "orange":
            if not is_silver:
                return None  # ゴールデン赤 = 赤へ潰す (独立色にしない)
            return f"Cream {word} Cameo" if is_dilute else f"{word} Cameo"
        # tortie: 既存のトーティ solid 名 (Tortoiseshell / Blue Cream / Chocolate Tortie 等) を土台に
        # 度合い語を前置し、ゴールデン(非シルバー)は "(Golden)" を付す。
        base_tortie = self._tortie_solid_stem(base, is_dilute, is_silver=False)
        name = f"{word} {base_tortie}"
        if not is_silver:
            name = f"{name} (Golden)"
        return name

    def find_matching_color(
        self,
        kitten: KittenGenotype,
        sire_color: str,
        dam_color: str,
        breed: str | None = None,
    ) -> str | None:
        key = expressed_genotype_key(kitten.loci, kitten.sex)
        candidates = list(GENOTYPE_TO_COLOR_MAP.get((kitten.sex.lower(), key), []))
        if not candidates:
            return None

        # Ruddy 等の猫種固有名は、同じ遺伝子型の一般名より先にCSV逆引きへ入ることがある。
        # 猫種文脈が合わない場合は候補から外し、一般結果へ固有呼称を漏らさない。
        candidates = [
            candidate
            for candidate in candidates
            if self._candidate_allowed_in_breed_context(candidate, breed)
        ]
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

        # ティックド猫種 (Abyssinian/Somali) は全タビーがティックド固定。expressed_genotype_key が
        # Ta/Mc/Sp を落とすため、逆引き候補には "Blue Tabby"(汎用) と "Blue Ticked Tabby"(猫種呼称)
        # が同順で並び、親名スコアが引き分けると汎用名が選ばれ品種表示名 (Blue) へ変換されない。
        # そこでティックド猫種文脈でのみ猫種呼称に微小ボーナスを与え引き分けを解消する。
        # 優先度: breed_specific 直接名 (Ruddy) > ティックドタビー別名 (Blue Ticked Tabby) > 汎用。
        # ボーナスは親名一致 (20/語) より小さく保ち、親名駆動のパターン選択を阻害しない。
        is_ticked_breed = bool(breed) and (
            "abyssinian" in breed.lower() or "somali" in breed.lower()
        )

        def ticked_breed_rank(color_name: str) -> int:
            if not is_ticked_breed:
                return 0
            resolved = COLOR_MASTER.resolve(color_name)
            if (
                resolved is not None
                and resolved.status == "breed_specific"
                and breed_context_matches(breed, resolved.breed_context)
            ):
                return 2
            if "ticked" in color_name.lower().split():
                return 1
            return 0

        def breed_specific_rank(color_name: str) -> int:
            """猫種指定時、その猫種固有呼称 (breed_specific) の候補にタイブレーク用の微小
            ボーナスを与える。例: Tonkinese の希釈チョコポイントは一般 "Lilac Point" と
            固有 "Platinum Point" が同一遺伝子型 (b/b d/d cs/cs) で並ぶが、親名 "Champagne"
            とは一致しないため両者 0 点で引き分ける。固有呼称を優先し "Platinum Point" を出す。
            ボーナスは親名一致 (20/語) より小さく保ち、親名駆動のパターン選択を阻害しない。
            """

            if not breed:
                return 0
            resolved = COLOR_MASTER.resolve(color_name)
            if (
                resolved is not None
                and resolved.status == "breed_specific"
                and breed_context_matches(breed, resolved.breed_context)
            ):
                return 1
            return 0

        # ティッピング度合い (Chinchilla/Shell vs Shaded) は expressed_genotype_key に含まれないため、
        # Chinchilla Silver と Shaded Silver は同一遺伝子型で逆引き候補に並ぶ。親名ベースの度合い判定
        # (_tipping_degree。衝突/不明時は Shaded 既定) に一致する候補へ微小ボーナスを与えて選ぶ。
        target_degree = self._tipping_degree(sire_color, dam_color)

        def degree_rank(color_name: str) -> int:
            words = color_name.lower().split()
            has_chinchilla = ("chinchilla" in words) or ("shell" in words)
            has_shaded = "shaded" in words
            if not (has_chinchilla or has_shaded):
                return 0
            cand_degree = "chinchilla" if has_chinchilla else "shaded"
            return 5 if cand_degree == target_degree else 0

        def score(color_name: str) -> int:
            base_score = priority_map.get(color_name, 0)
            color_words = color_name.lower().split()
            match_count = sum(1 for w in color_words if w in parent_words)
            return (
                base_score
                + match_count * 20
                + ticked_breed_rank(color_name)
                + breed_specific_rank(color_name)
                + degree_rank(color_name)
            )

        candidates.sort(key=score, reverse=True)
        return candidates[0]

    @staticmethod
    def _candidate_allowed_in_breed_context(name: str, breed: str | None) -> bool:
        """CSV逆引き候補を、猫種固有呼称の表示文脈で絞り込む。"""

        resolved = COLOR_MASTER.resolve(name)
        if resolved is None or resolved.status != "breed_specific":
            return True
        if breed_context_matches(breed, resolved.breed_context):
            return True
        if breed and DISPLAY_ALIAS_MAP.resolve_display_name(name, breed) != name:
            return True
        return False

    def post_process_color_name(
        self, name: str, sire_color: str, dam_color: str, breed: str | None
    ) -> str:
        name = self.clean_phenotype_name(name)
        name = self.simplify_patterns(name, sire_color, dam_color, breed)
        # パターン簡略化後に "Black Silver Tabby" などの中間名が生じるため再度正規化する。
        name = self.clean_phenotype_name(name)
        # 出力色名を cat_color_master.csv の canonical PrimaryName へ正規化する
        # (alias 統合・略記展開)。集計はこの canonical 名で行われ自動的にマージされる。
        name = COLOR_MASTER.canonical_name(name)
        name = self.normalize_point_display_name(name)
        name = COLOR_MASTER.canonical_name(name)
        name = self.normalize_cameo_display_name(name)
        # 猫種別表示名 (Abyssinian の Ruddy、Oriental の Ebony 等) と一般 Van 正規化を
        # cat_color_display_alias_map.csv 駆動で適用する (データ正本 §4 / §1.1)。
        # canonical 正規化の「後」に置く: Ebony/Chestnut/Lavender は master では alias のため、
        # 先に canonical 化しないと猫種別呼称が一般名へ戻ってしまう。
        name = DISPLAY_ALIAS_MAP.resolve_display_name(name, breed)
        return name

    @staticmethod
    def normalize_cameo_display_name(name: str) -> str:
        """旧CSV由来の冗長な Cameo Smoke 名を一般表示へ寄せる。"""

        return _CAMEO_DISPLAY_ALIASES.get(name, name)

    @staticmethod
    def normalize_point_display_name(name: str) -> str:
        """Point 系の表示名から Silver/Golden/tipping 系の過剰分類を落とす。"""

        if "Point" not in name:
            return name

        suffix = ""
        core = name
        if core.endswith("-White"):
            core = core[: -len("-White")]
            suffix = "-White"

        core = re.sub(r"\b(?:Chinchilla|Shaded|Shell|Golden|Silver|Cameo|Smoke)\b\s*", "", core)
        core = " ".join(core.split())
        if core in ("Point", "Lynx Point") or core.startswith("Tortie "):
            core = f"Seal {core}"

        return f"{core}{suffix}"

    def clean_phenotype_name(self, name: str) -> str:
        # すでにCSVに存在する正式なカラー名である場合は、誤置換を防ぐためそのまま返す
        if name in _VALID_COLOR_NAMES:
            return name

        name = re.sub(r"\bSilver(?:\s+Silver)+\b", "Silver", name)

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
            elif name.startswith("Chocolate ") and not name.startswith("Chocolate Silver "):
                name = name.replace("Chocolate ", "Chocolate Silver ").replace(" Silver Tabby", " Tabby")
            elif name.startswith("Lilac ") and not name.startswith("Lilac Silver "):
                name = name.replace("Lilac ", "Lilac Silver ").replace(" Silver Tabby", " Tabby")
            elif name.startswith("Cinnamon ") and not name.startswith("Cinnamon Silver "):
                name = name.replace("Cinnamon ", "Cinnamon Silver ").replace(" Silver Tabby", " Tabby")
            elif name.startswith("Fawn ") and not name.startswith("Fawn Silver "):
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
        is_spotted_breed = False
        if breed:
            breed_lower = breed.lower()
            if "abyssinian" in breed_lower or "somali" in breed_lower:
                is_ticked_breed = True
            # Egyptian Mau / Ocicat は Sp/Sp 固定のスポテッド品種。全個体がスポテッドなので、
            # 逆引きがパターン語無しのタビー名を返しても必ず "Spotted" を補完する (下記)。
            if "egyptian mau" in breed_lower or "ocicat" in breed_lower:
                is_spotted_breed = True

        if not has_mackerel:
            name = name.replace("Mackerel ", "").replace("Mc ", "").replace(" Mackerel", "").replace(" Mc", "")
        if not has_classic:
            name = name.replace("Classic ", "").replace(" Classic", "")
        if not has_ticked and not is_ticked_breed:
            name = name.replace("Ticked ", "").replace("Tc ", "").replace(" Ticked", "").replace(" Tc", "")
        # スポテッド品種では Spotted を除去しない (品種固定パターンのため常に保持する)。
        if not has_spotted and not is_spotted_breed:
            name = name.replace("Spotted ", "").replace("Sp ", "").replace(" Spotted", "").replace(" Sp", "")

        name = " ".join(name.split())

        # スポテッド品種 (Egyptian Mau / Ocicat) は Sp/Sp 固定のため、逆引きがパターン語の無い
        # タビー名 (例 トーティの "Brown Patched Tabby"、シルバー希釈の "Blue Silver Tabby") を
        # 返しても "Spotted" を補完する。品種の全個体がスポテッドである性質を表示名に反映し、
        # 同一クロスの兄妹でパターン表記が食い違う (息子 Spotted / 娘 欠落) 不整合を防ぐ。
        if is_spotted_breed and "Tabby" in name:
            has_any_pattern = any(
                pattern in name for pattern in ("Spotted", "Mackerel", "Classic", "Ticked")
            )
            if not has_any_pattern:
                name = name.replace("Tabby", "Spotted Tabby", 1)
        name = name.replace(" -White", "-White").replace(" - White", "-White")
        # Tabby-White が Tabby-W の置換で Tabby-Whitehite に化けるのを防ぐ避難処理
        name = name.replace("Tabby-White", "__TABBY_WHITE__")
        name = name.replace("Tabby-W", "Tabby-White")
        name = name.replace("__TABBY_WHITE__", "Tabby-White")
        name = name.replace("T-W", "Tabby-White").replace("-W Van", "-White Van")
        return name
