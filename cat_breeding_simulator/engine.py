"""毛色確率計算エンジン本体。"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from cat_breeding_simulator.master_data import (
    AUTOSOMAL_LOCI,
    BREED_FILTERS,
    COLOR_BASE_LOCI,
    COLOR_DEFINITIONS,
    NORMAL_CLOSED_LOCI,
    NORMAL_OPENED_LOCI,
    PHENOTYPE_GENOTYPES,
    SUPPORTED_MODES,
    VALID_BREEDS,
    ParentGenotype,
    build_parent_genotypes,
)
from cat_breeding_simulator.color_master import COLOR_MASTER
from cat_breeding_simulator.display_alias_map import DISPLAY_ALIAS_MAP


ProbabilityMap = dict[tuple[str, str], float]


def _genotype_key(loci: dict[str, tuple[str, str]]) -> tuple:
    """遺伝子型をアレル単位でそのまま表すキー (デバッグ・未分類サンプル記録用)。"""

    parts = []
    for locus in sorted(loci.keys()):
        a1, a2 = loci[locus]
        parts.append((locus, tuple(sorted([a1, a2]))))
    return tuple(parts)


def _expressed_genotype_key(loci: dict[str, tuple[str, str]], sex: str) -> tuple:
    """遺伝子型を「実際に発現する表現型」レベルへ還元したキーを返す。

    完全一致辞書だけに頼ると、D/d のようなヘテロ接合の子猫が D/D の正規遺伝子型に
    一致せず分類不能になる (そして無言で捨てられ再正規化される)。優性・劣性を解決した
    発現状態でキー化することで、親 (CSV正規遺伝子型) と子猫 (ヘテロ接合を含む) を
    同じ土俵で突き合わせる。

    パターン座 (Mc / Ta / Sp) は CSV 上の符号付けが不安定なためキーから除外し、
    パターン名は親カラー名ベースの後処理 (_simplify_patterns) に委ねる。
    """

    o_alleles = loci["O"]
    if sex.lower() == "male":
        orange = "orange" if "O" in o_alleles else "non_orange"
    else:
        if "O" in o_alleles and "o" in o_alleles:
            orange = "tortie"
        elif "O" in o_alleles:
            orange = "orange"
        else:
            orange = "non_orange"

    # B locus 優性順: B > b > bl
    b_alleles = loci["B"]
    if "B" in b_alleles:
        base = "black"
    elif "b" in b_alleles:
        base = "chocolate"
    else:
        base = "cinnamon"

    dilute = "dilute" if loci["D"][0] == "d" and loci["D"][1] == "d" else "dense"
    agouti = "agouti" if "A" in loci["A"] else "solid"

    # C locus: C (フルカラー) が優性。点紋系は C が無いときのみ発現
    c_alleles = loci["C"]
    if "C" in c_alleles:
        c_state = "full"
    elif "cb" in c_alleles and "cs" in c_alleles:
        c_state = "mink"
    elif "cs" in c_alleles:
        c_state = "point"
    elif "cb" in c_alleles:
        c_state = "sepia"
    else:
        c_state = "full"

    dominant_white = "white" if "W" in loci["W"] else "colored"

    s_alleles = loci["S"]
    if s_alleles[0] == "S" and s_alleles[1] == "S":
        spotting = "high_white"
    elif "S" in s_alleles:
        spotting = "white"
    else:
        spotting = "none"

    silver = "silver" if "I" in loci["I"] else "non_silver"
    wideband = "wide" if "Wb" in loci["Wb"] else "narrow"

    return (
        orange,
        base,
        dilute,
        agouti,
        c_state,
        dominant_white,
        spotting,
        silver,
        wideband,
    )


def _carrier_options_for(
    locus: str, recessive_alleles: tuple[str, str], dominant_alleles: tuple[str, str]
) -> list[tuple[tuple[str, str], str]]:
    """carrier_exploration: 片親 (recessive) が劣性を完全発現し、相手 (dominant) が優性発現の場合に、
    相手に開ける (carrier 遺伝子型, ラベル) のリストを返す。該当しなければ []。

    両親とも優性発現 (= 両方が隠れキャリアかもしれない) のケースは生成しない (条件付き探索の対象外)。
    """

    if locus == "A":
        # 片親 a/a ソリッド → 相手が A/a なら子に a/a (ソリッド/トーティ/キャリコ) が出得る
        if recessive_alleles == ("a", "a") and "A" in dominant_alleles and dominant_alleles != ("a", "a"):
            return [(("A", "a"), "A/a (ソリッドキャリア)")]
    elif locus == "B":
        # 相手は黒系 (B/B) のときのみ。片親 b/b → 相手 B/b (チョコ)、片親 bl/bl → 相手 B/bl (シナモン)
        if dominant_alleles == ("B", "B"):
            if recessive_alleles == ("b", "b"):
                return [(("B", "b"), "B/b (チョコレートキャリア)")]
            if recessive_alleles == ("bl", "bl"):
                return [(("B", "bl"), "B/bl (シナモンキャリア)")]
    elif locus == "C":
        # 相手はフルカラー (C/C) のときのみ。片親 cs/cs→C/cs(ポイント)、cb/cb→C/cb(セピア)、
        # cb/cs(ミンク)→C/cs と C/cb の両方を提示。
        if dominant_alleles == ("C", "C"):
            if recessive_alleles == ("cs", "cs"):
                return [(("C", "cs"), "C/cs (ポイントキャリア)")]
            if recessive_alleles == ("cb", "cb"):
                return [(("C", "cb"), "C/cb (セピアキャリア)")]
            if set(recessive_alleles) == {"cb", "cs"}:
                return [
                    (("C", "cs"), "C/cs (ポイントキャリア)"),
                    (("C", "cb"), "C/cb (セピアキャリア)"),
                ]
    elif locus == "D":
        # 片親 d/d 希釈 → 相手が D/d なら子に d/d (希釈) が条件付きで増える
        if recessive_alleles == ("d", "d") and dominant_alleles != ("d", "d"):
            return [(("D", "d"), "D/d (希釈キャリア)")]
    return []


GENOTYPE_TO_COLOR_MAP: dict[tuple[str, tuple], list[str]] = {}


def _build_genotype_to_color_map() -> None:
    GENOTYPE_TO_COLOR_MAP.clear()
    for color, sex_dict in PHENOTYPE_GENOTYPES.items():
        for sex in ("male", "female"):
            for genotype in sex_dict[sex]:
                key = _expressed_genotype_key(genotype.loci, sex)
                map_key = (sex, key)
                if map_key not in GENOTYPE_TO_COLOR_MAP:
                    GENOTYPE_TO_COLOR_MAP[map_key] = []
                if color not in GENOTYPE_TO_COLOR_MAP[map_key]:
                    GENOTYPE_TO_COLOR_MAP[map_key].append(color)


_build_genotype_to_color_map()


@dataclass(frozen=True, slots=True)
class KittenResult:
    """API返却用の集計結果。"""

    sex: str
    color: str
    probability_pct: float


@dataclass(frozen=True, slots=True)
class CarrierScenario:
    """carrier_exploration の 1 シナリオ (片親の劣性発現に対し、相手がキャリアの場合の条件付き結果)。"""

    scenario: str                                  # 機械用ID 例: "C_cs_on_dam"
    label: str                                     # 人間可読の仮説説明
    assumed_carriers: dict[str, dict[str, str]]    # 例: {"dam": {"C": "C/cs"}}
    probability_basis: str                         # "conditional_on_other_parent_carrier"
    prior_probability_applied: bool                # 事前確率を掛けたか (常に False)
    results: list[KittenResult]                    # この仮説の条件付き結果 (合計100%)
    new_colors: list[str]                          # baseline (normal) に無く、この仮説で現れる色


@dataclass(frozen=True, slots=True)
class CalculationReport:
    """計算結果 + 内部診断値 + モード情報。

    既存フィールド (results 等) は後方互換のため維持し、モード情報は新規フィールドとして追加する。
    """

    results: list[KittenResult]
    matched_probability: float
    unmatched_probability: float
    unmatched_genotype_count: int
    unmatched_samples: list[dict[str, object]]
    mode: str = "normal"
    opened_loci: list[str] | None = None     # X/- 展開 or 明示キャリアで開けた座位
    closed_loci: list[str] | None = None     # キャリア非展開で閉じた座位
    assumptions: list[str] | None = None     # 計算前提の人間可読メモ
    # carrier_exploration_mode の条件付きシナリオ。normal results とは完全分離する。
    carrier_exploration_results: list[CarrierScenario] | None = None


@dataclass(frozen=True, slots=True)
class KittenGenotype:
    """子猫1個体の遺伝子型。"""

    sex: str
    loci: dict[str, tuple[str, str]]


class BreedingCalculationError(ValueError):
    """入力や計算前提の不整合。"""


class CoatColorCalculator:
    """Split -> Cross -> Evaluate -> Aggregate を実装する計算器。"""

    def calculate(
        self,
        sire_color: str,
        dam_color: str,
        breed: str | None = None,
        mode: str = "normal",
        sire_carriers: dict[str, str] | None = None,
        dam_carriers: dict[str, str] | None = None,
    ) -> list[KittenResult]:
        """既存API互換: 表示用結果リストのみを返す。"""

        return self.calculate_report(
            sire_color, dam_color, breed, mode, sire_carriers, dam_carriers
        ).results

    def calculate_report(
        self,
        sire_color: str,
        dam_color: str,
        breed: str | None = None,
        mode: str = "normal",
        sire_carriers: dict[str, str] | None = None,
        dam_carriers: dict[str, str] | None = None,
    ) -> CalculationReport:
        """結果に加えて未分類率などの内部診断値とモード情報を返す。

        計算モード:
          - normal: 未明示キャリアを閉じる (A/B/C/Wb 非展開、D/I/Mc/Ta のみ X/- 展開)。
          - explicit_carrier: 指定された座位のみ開ける (sire_carriers / dam_carriers)。
          - carrier_exploration: 未実装 (Phase 2)。指定時は明示エラー。

        分類不能 (どの正規カラーにも還元できない) 子猫を黙って捨てて 100% に
        再正規化することはしない。未分類は unmatched_probability として保持する。
        通常結果とキャリア仮定結果を 1 つの表に混ぜない (mode ごとに分離)。
        """

        if mode not in SUPPORTED_MODES:
            raise BreedingCalculationError(
                f"未知の計算モード '{mode}'。利用可能: {', '.join(SUPPORTED_MODES)}。"
            )
        # 猫種は任意だが、指定された場合は有効な猫種のみ受け付ける (黙って無視しない)。
        # VALID_BREEDS は /api/v1/breeds と同基準 (CSV 由来のゴミ行 "ｱｷ" 等を除外)。
        if breed and self._normalize_breed_key(breed) not in VALID_BREEDS:
            raise BreedingCalculationError(f"未対応の猫種です: '{breed}'")
        if mode == "carrier_exploration":
            return self._calculate_carrier_exploration(sire_color, dam_color, breed)

        sire_genotypes = self._resolve_parent_genotypes(
            sire_color, "male", breed, mode, sire_carriers
        )
        dam_genotypes = self._resolve_parent_genotypes(
            dam_color, "female", breed, mode, dam_carriers
        )

        if not sire_genotypes:
            raise BreedingCalculationError("No valid sire genotypes remain after filtering.")
        if not dam_genotypes:
            raise BreedingCalculationError("No valid dam genotypes remain after filtering.")

        aggregate: ProbabilityMap = defaultdict(float)
        matched_probability = 0.0
        unmatched_probability = 0.0
        unmatched_keys: set[tuple[str, tuple]] = set()
        unmatched_samples: list[dict[str, object]] = []
        pair_weight = 1.0 / (len(sire_genotypes) * len(dam_genotypes))

        for sire_genotype in sire_genotypes:
            sire_gametes = self._build_gametes(sire_genotype)
            for dam_genotype in dam_genotypes:
                dam_gametes = self._build_gametes(dam_genotype)
                for sire_gamete, sire_probability in sire_gametes.items():
                    for dam_gamete, dam_probability in dam_gametes.items():
                        kitten = self._combine_gametes(sire_gamete, dam_gamete)
                        weight = sire_probability * dam_probability * pair_weight
                        phenotype = self._classify_phenotype(kitten, sire_color, dam_color)
                        if phenotype is None:
                            # 分類不能を捨てて再正規化せず、未分類率として加算する
                            unmatched_probability += weight
                            expressed = _expressed_genotype_key(kitten.loci, kitten.sex)
                            sample_key = (kitten.sex, expressed)
                            if sample_key not in unmatched_keys:
                                unmatched_keys.add(sample_key)
                                if len(unmatched_samples) < 20:
                                    unmatched_samples.append(
                                        {
                                            "sex": kitten.sex,
                                            "expressed_key": expressed,
                                            "genotype": _genotype_key(kitten.loci),
                                        }
                                    )
                            continue
                        phenotype = self._post_process_color_name(
                            phenotype, sire_color, dam_color, breed
                        )
                        matched_probability += weight
                        aggregate[(kitten.sex, phenotype)] += weight

        results = self._to_results(aggregate, unmatched_probability)
        opened_loci, closed_loci, assumptions = self._build_mode_metadata(
            mode, sire_carriers, dam_carriers
        )
        return CalculationReport(
            results=results,
            matched_probability=round(matched_probability, 6),
            unmatched_probability=round(unmatched_probability, 6),
            unmatched_genotype_count=len(unmatched_keys),
            unmatched_samples=unmatched_samples,
            mode=mode,
            opened_loci=opened_loci,
            closed_loci=closed_loci,
            assumptions=assumptions,
        )

    @staticmethod
    def _build_mode_metadata(
        mode: str,
        sire_carriers: dict[str, str] | None,
        dam_carriers: dict[str, str] | None,
    ) -> tuple[list[str], list[str], list[str]]:
        """mode に応じた opened_loci / closed_loci / assumptions を構築する。"""

        assumptions = [
            "A (タビー): A/A 相当に固定 (A/a 非展開)",
            "B (黒/チョコ/シナモン): 表現型値に固定 (B/b・B/bl キャリア非展開)",
            "C (フルカラー/ポイント/セピア): 表現型値に固定 (C/cs・C/cb キャリア非展開)",
            "Wb (ワイドバンド): 非展開",
            "D/I/Mc/Ta: 優性ヘテロ未確定として X/- 展開 (50:50 中立)",
            "S (白斑): 入力レベルで確定 (非展開)",
        ]
        opened = list(NORMAL_OPENED_LOCI)
        closed = list(NORMAL_CLOSED_LOCI)

        if mode == "explicit_carrier":
            for parent, carriers in (("sire", sire_carriers), ("dam", dam_carriers)):
                for locus, genotype in (carriers or {}).items():
                    if locus not in opened:
                        opened.append(locus)
                    if locus in closed:
                        closed.remove(locus)
                    assumptions.append(f"{locus}: {parent} に {genotype} を明示指定 (開放)")

        return opened, closed, assumptions

    # --- carrier_exploration_mode (Phase 2) ---
    #
    # 「片親が劣性形質を完全発現している場合に、相手がそのキャリアだったらどうなるか」のみを
    # 条件付きシナリオとして提示する。両親とも通常表現型で両方が隠れキャリア、という仮定は
    # 自動生成しない。事前確率 (実集団のキャリア頻度) は一切掛けない。
    # normal の確定結果 (results) とは完全に分離する。

    def _calculate_carrier_exploration(
        self, sire_color: str, dam_color: str, breed: str | None
    ) -> CalculationReport:
        baseline = self.calculate_report(sire_color, dam_color, breed, mode="normal")
        scenarios = self._build_carrier_scenarios(sire_color, dam_color, breed, baseline)
        assumptions = list(baseline.assumptions or [])
        assumptions.append(
            "carrier_exploration: 各シナリオは『片親の劣性発現に対し相手がキャリア』の条件付き結果。"
            "事前確率 (キャリア頻度) は掛けない。normal results とは分離して提示する。"
        )
        return CalculationReport(
            results=baseline.results,
            matched_probability=baseline.matched_probability,
            unmatched_probability=baseline.unmatched_probability,
            unmatched_genotype_count=baseline.unmatched_genotype_count,
            unmatched_samples=baseline.unmatched_samples,
            mode="carrier_exploration",
            opened_loci=baseline.opened_loci,
            closed_loci=baseline.closed_loci,
            assumptions=assumptions,
            carrier_exploration_results=scenarios,
        )

    def _resolved_base_loci(
        self, color: str, sex: str, breed: str | None
    ) -> dict[str, tuple[str, str]] | None:
        """入力色名を解決し、その色の基準遺伝子型 (autosomal) を返す。未知なら None。"""

        name = self._resolve_input_color_name(color, breed)
        key = self._normalize_color_key(name)
        entries = COLOR_BASE_LOCI.get(key)
        if not entries:
            return None
        return dict(entries[0].autosomal)

    # carrier_exploration の各 locus の既定値 (CSV に欠落していた場合のフォールバック)。
    _CARRIER_LOCUS_DEFAULTS: dict[str, tuple[str, str]] = {
        "A": ("a", "a"),
        "B": ("B", "B"),
        "C": ("C", "C"),
        "D": ("D", "D"),
    }

    def _build_carrier_scenarios(
        self, sire_color: str, dam_color: str, breed: str | None, baseline: CalculationReport
    ) -> list[CarrierScenario]:
        sire_base = self._resolved_base_loci(sire_color, "male", breed)
        dam_base = self._resolved_base_loci(dam_color, "female", breed)
        if sire_base is None or dam_base is None:
            return []

        baseline_colors = {result.color for result in baseline.results}
        scenarios: list[CarrierScenario] = []
        for locus in ("A", "B", "C", "D"):
            default = self._CARRIER_LOCUS_DEFAULTS[locus]
            sire_alleles = sire_base.get(locus, default)
            dam_alleles = dam_base.get(locus, default)

            # 父が劣性発現 → 母 (相手) にキャリアを開ける
            for carrier, carrier_label in _carrier_options_for(locus, sire_alleles, dam_alleles):
                scenario = self._compute_carrier_scenario(
                    locus, "dam", carrier, carrier_label,
                    sire_color, dam_color, breed, baseline_colors, recessive_parent=sire_color,
                )
                if scenario is not None:
                    scenarios.append(scenario)

            # 母が劣性発現 → 父 (相手) にキャリアを開ける
            for carrier, carrier_label in _carrier_options_for(locus, dam_alleles, sire_alleles):
                scenario = self._compute_carrier_scenario(
                    locus, "sire", carrier, carrier_label,
                    sire_color, dam_color, breed, baseline_colors, recessive_parent=dam_color,
                )
                if scenario is not None:
                    scenarios.append(scenario)
        return scenarios

    def _compute_carrier_scenario(
        self,
        locus: str,
        open_parent: str,
        carrier: tuple[str, str],
        carrier_label: str,
        sire_color: str,
        dam_color: str,
        breed: str | None,
        baseline_colors: set[str],
        recessive_parent: str,
    ) -> CarrierScenario | None:
        genotype_str = f"{carrier[0]}/{carrier[1]}"
        sire_carriers = {locus: genotype_str} if open_parent == "sire" else None
        dam_carriers = {locus: genotype_str} if open_parent == "dam" else None
        try:
            report = self.calculate_report(
                sire_color, dam_color, breed, "explicit_carrier", sire_carriers, dam_carriers
            )
        except BreedingCalculationError:
            return None
        if not report.results:
            return None

        new_colors = sorted({result.color for result in report.results} - baseline_colors)
        opened_color = dam_color if open_parent == "dam" else sire_color
        label = f"{opened_color} が {carrier_label} と仮定 ({recessive_parent} は {locus} 劣性を発現)"
        return CarrierScenario(
            scenario=f"{locus}_{carrier[1]}_on_{open_parent}",
            label=label,
            assumed_carriers={open_parent: {locus: genotype_str}},
            probability_basis="conditional_on_other_parent_carrier",
            prior_probability_applied=False,
            results=report.results,
            new_colors=new_colors,
        )

    def _resolve_parent_genotypes(
        self,
        phenotype: str,
        sex: str,
        breed: str | None,
        mode: str = "normal",
        carriers: dict[str, str] | None = None,
    ) -> list[ParentGenotype]:
        if breed:
            breed_lower = breed.lower()
            if "abyssinian" in breed_lower or "somali" in breed_lower:
                phenotype_lower = phenotype.lower()
                if phenotype_lower == "blue":
                    phenotype = "Blue Ticked Tabby"
                elif phenotype_lower == "cinnamon":
                    phenotype = "Cinnamon Ticked Tabby"
                elif phenotype_lower == "fawn":
                    phenotype = "Fawn Ticked Tabby"
                elif phenotype_lower == "red":
                    phenotype = "Red Ticked Tabby"

        # cat_color_master.csv による入力名の解決 (alias 受理 + 通常モードでの制限)。
        phenotype = self._resolve_input_color_name(phenotype, breed)

        phenotype_key = self._normalize_color_key(phenotype)
        if phenotype_key not in PHENOTYPE_GENOTYPES:
            supported = ", ".join(sorted(PHENOTYPE_GENOTYPES))
            raise BreedingCalculationError(f"Unsupported color '{phenotype}'. Supported colors: {supported}")

        # mode に応じた親遺伝子型候補を生成する (normal: キャリア閉鎖 / explicit_carrier: 指定座位を開放)。
        genotypes = build_parent_genotypes(phenotype_key, sex, mode, carriers)
        if not genotypes:
            raise BreedingCalculationError(f"Color '{phenotype_key}' is not valid for a {sex}.")

        if not breed:
            return genotypes

        breed_key = self._normalize_breed_key(breed)
        breed_constraints = BREED_FILTERS.get(breed_key, {})
        filtered: list[ParentGenotype] = []
        for genotype in genotypes:
            if all(self._matches_exact(genotype.loci[locus], required) for locus, required in breed_constraints.items() if locus in genotype.loci):
                filtered.append(genotype)
        return filtered

    def _build_gametes(self, genotype: ParentGenotype) -> dict[tuple[tuple[str, str], ...], float]:
        gametes: dict[tuple[tuple[str, str], ...], float] = {(): 1.0}
        for locus in AUTOSOMAL_LOCI:
            next_gametes: dict[tuple[tuple[str, str], ...], float] = defaultdict(float)
            allele_probabilities = self._allele_probabilities(genotype.loci[locus])
            for gamete, current_probability in gametes.items():
                gamete_entries = dict(gamete)
                for allele, allele_probability in allele_probabilities.items():
                    gamete_entries[locus] = allele
                    next_key = tuple(sorted(gamete_entries.items()))
                    next_gametes[next_key] += current_probability * allele_probability
            gametes = next_gametes

        orange_probabilities = self._orange_gametes(genotype)
        next_gametes = defaultdict(float)
        for gamete, current_probability in gametes.items():
            gamete_entries = dict(gamete)
            for orange_allele, orange_probability in orange_probabilities.items():
                gamete_entries["O"] = orange_allele
                next_key = tuple(sorted(gamete_entries.items()))
                next_gametes[next_key] += current_probability * orange_probability
        return dict(next_gametes)

    def _combine_gametes(
        self,
        sire_gamete: tuple[tuple[str, str], ...],
        dam_gamete: tuple[tuple[str, str], ...],
    ) -> KittenGenotype:
        sire_map = dict(sire_gamete)
        dam_map = dict(dam_gamete)
        kitten_loci: dict[str, tuple[str, str]] = {}

        sire_orange = sire_map["O"]
        dam_orange = dam_map["O"]
        if sire_orange == "Y":
            sex = "Male"
            kitten_loci["O"] = (dam_orange, "Y")
        else:
            sex = "Female"
            kitten_loci["O"] = (sire_orange, dam_orange)

        for locus in AUTOSOMAL_LOCI:
            kitten_loci[locus] = (sire_map[locus], dam_map[locus])
        return KittenGenotype(sex=sex, loci=kitten_loci)

    def _classify_phenotype(self, kitten: KittenGenotype, sire_color: str = "", dam_color: str = "") -> str | None:
        if sire_color and dam_color:
            matched = self._find_matching_color(kitten, sire_color, dam_color)
            if matched:
                return matched
        # CSV逆引きに名前が無い遺伝子型は標準表現型から構築する (V9 §6.1 step1)。
        # 構築できないもの (点紋/チョコ等の想定外) のみ None = 未分類として検出する。
        return self._construct_fallback_name(kitten)

    def _construct_fallback_name(self, kitten: KittenGenotype) -> str | None:
        """CSV逆引きに無い遺伝子型を、標準表現型から構築して命名する (V9 §6.1)。

        通常モードでは B(チョコ系) と C(点紋系) を展開しないため、ここで扱うのは
        黒系(B/B)・フルカラー(C/C) の組み合わせに限られる。優性白以外で base/C/Wb が
        想定外 (点紋・チョコ・ワイドバンド等) の場合は None を返し、未分類として検出させる。
        """

        key = _expressed_genotype_key(kitten.loci, kitten.sex)
        orange, base, dilute, agouti, c_state, dom_white, spotting, silver, wideband = key

        if dom_white == "white":
            return "White"
        # 通常モードの構築対象外 (点紋/チョコ/シナモン/ワイドバンド) は未分類に回す
        if base != "black" or c_state != "full" or wideband != "narrow":
            return None

        is_dilute = dilute == "dilute"
        is_agouti = agouti == "agouti"
        is_silver = silver == "silver"

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

    def _apply_modifiers(self, phenotype: str, kitten: KittenGenotype, *, patterned: bool) -> str:
        if self._has_dominant(kitten.loci["I"], "I"):
            if patterned:
                phenotype = phenotype.replace(" Tabby", " Silver Tabby")
            else:
                phenotype = f"{phenotype} Smoke"
        elif patterned and self._has_dominant(kitten.loci["Wb"], "Wb"):
            phenotype = f"Golden {phenotype}"
        return phenotype

    def _apply_white_spotting(self, phenotype: str, white_spotting: tuple[str, str]) -> str:
        if not self._has_dominant(white_spotting, "S"):
            return phenotype
        if self._is_homozygous(white_spotting, "S"):
            return f"{phenotype}-White Van"
        return f"{phenotype}-White"

    def _black_series_color(self, alleles: tuple[str, str], dilute: bool) -> str:
        if "B" in alleles:
            return "Blue" if dilute else "Black"
        if "b" in alleles:
            return "Lilac" if dilute else "Chocolate"
        return "Fawn" if dilute else "Cinnamon"

    def _point_restriction(self, alleles: tuple[str, str]) -> str:
        normalized = frozenset(alleles)
        if normalized == frozenset({"cs"}):
            return "Point"
        if normalized == frozenset({"cb"}):
            return "Sepia"
        if normalized == frozenset({"cb", "cs"}):
            return "Mink"
        return ""

    def _tabby_pattern(self, kitten: KittenGenotype) -> str:
        if self._has_dominant(kitten.loci["Ta"], "Ta"):
            return "Ticked Tabby"
        if self._has_dominant(kitten.loci["Sp"], "Sp"):
            return "Spotted Tabby"
        mackerel = kitten.loci["Mc"]
        if self._has_dominant(mackerel, "Mc"):
            return "Mackerel Tabby"
        return "Classic Tabby"

    def _orange_state(self, kitten: KittenGenotype) -> str:
        orange = kitten.loci["O"]
        if kitten.sex == "Male":
            return "orange" if "O" in orange else "non_orange"
        if orange[0] == "O" and orange[1] == "O":
            return "orange"
        if "O" in orange and "o" in orange:
            return "tortoiseshell"
        return "non_orange"

    def _to_results(
        self, aggregate: ProbabilityMap, unmatched_probability: float = 0.0
    ) -> list[KittenResult]:
        # 全交配の重み合計は 1.0。matched 分を「再正規化せず」そのまま百分率化する。
        # こうすることで未分類があれば表示合計が 100% 未満になり、欠損を隠さない。
        sorted_results = sorted(aggregate.items(), key=lambda item: (-item[1], item[0][0], item[0][1]))
        results: list[KittenResult] = []
        for (sex, color), probability in sorted_results:
            pct = round(probability * 100, 4)
            # 丸めて 0.0% になる項目は通常出力に出さない (要件: 0.0% 禁止)
            if pct <= 0:
                continue
            results.append(KittenResult(sex=sex, color=color, probability_pct=pct))

        if not results:
            return results

        # 未分類が実質ゼロのときだけ、丸め誤差・閾値未満の切り捨て分を最上位へ寄せて
        # 合計を 100.0 に整える。未分類が残る場合は 100 に戻さず欠損を残す。
        if unmatched_probability < 0.00005:
            diff = round(100.0 - sum(entry.probability_pct for entry in results), 4)
            if diff:
                top = results[0]
                results[0] = KittenResult(
                    sex=top.sex,
                    color=top.color,
                    probability_pct=round(top.probability_pct + diff, 4),
                )
        return results

    @staticmethod
    def _matches_exact(actual: tuple[str, str], required: tuple[str, str]) -> bool:
        if "Y" in actual:
            non_y_allele = actual[0] if actual[1] == "Y" else actual[1]
            if required[0] == required[1]:
                return non_y_allele == required[0]
            return False
        return actual == required or actual == (required[1], required[0])

    @staticmethod
    def _allele_probabilities(alleles: tuple[str, str]) -> dict[str, float]:
        first, second = alleles
        if first == second:
            return {first: 1.0}
        return {first: 0.5, second: 0.5}

    @staticmethod
    def _orange_gametes(genotype: ParentGenotype) -> dict[str, float]:
        first, second = genotype.loci["O"]
        if genotype.sex == "male":
            return {first: 0.5, "Y": 0.5}
        if first == second:
            return {first: 1.0}
        return {first: 0.5, second: 0.5}

    @staticmethod
    def _has_dominant(alleles: tuple[str, str], dominant: str) -> bool:
        return dominant in alleles

    @staticmethod
    def _is_homozygous(alleles: tuple[str, str], allele: str) -> bool:
        return alleles[0] == allele and alleles[1] == allele

    def _resolve_input_color_name(self, name: str, breed: str | None) -> str:
        """cat_color_master.csv を用いて入力色名を解決する (名前正規化レイヤ)。

        - alias は canonical 概念へ寄せ、その概念を表す engine 認識名 (PHENOTYPE_GENOTYPES の
          キー) を返す (spec: canonical を engine に渡す)。
        - excluded / review は通常計算の入力色として使えないため拒否する。
        - breed_specific は猫種未指定の通常モードでは拒否する (猫種指定時は文脈ありとして許可)。
        - master 未登録、または canonical 概念に engine 認識名が無い場合は、元名が直接認識
          できればそれを使い、そうでなければ元名のまま返す (後段で Unsupported を送出)。
        """

        resolved = COLOR_MASTER.resolve(name)
        if resolved is not None:
            if resolved.status in ("excluded", "review"):
                raise BreedingCalculationError(
                    f"'{name}' は通常計算の入力色として使用できません (status={resolved.status})。"
                )
            if resolved.status == "breed_specific" and not breed:
                raise BreedingCalculationError(
                    f"'{name}' は猫種固有色 ({resolved.breed_context}) のため、"
                    "猫種を指定しない通常モードでは入力できません。"
                )
            # canonical 概念を優先して engine 認識名 (PHENOTYPE_GENOTYPES のキー) を探す
            for candidate in resolved.engine_candidate_names:
                if self._normalize_color_key(candidate) in PHENOTYPE_GENOTYPES:
                    return candidate
        # master 未登録 / 候補が engine 未知 → 元名が直接認識できればそれを使う
        if self._normalize_color_key(name) in PHENOTYPE_GENOTYPES:
            return name
        return name

    @staticmethod
    def _normalize_color_key(color: str) -> str:
        normalized = " ".join(color.replace("_", " ").replace("-", " - ").split()).replace(" - ", "-")
        for known_color in PHENOTYPE_GENOTYPES:
            if known_color.casefold() == normalized.casefold():
                return known_color
        return color

    @staticmethod
    def _normalize_breed_key(breed: str) -> str:
        normalized = " ".join(breed.split())
        for known_breed in BREED_FILTERS:
            if known_breed.casefold() == normalized.casefold():
                return known_breed
        return breed

    def _post_process_color_name(
        self, name: str, sire_color: str, dam_color: str, breed: str | None
    ) -> str:
        name = self._clean_phenotype_name(name)
        name = self._simplify_patterns(name, sire_color, dam_color, breed)
        # 出力色名を cat_color_master.csv の canonical PrimaryName へ正規化する
        # (alias 統合・略記展開)。集計はこの canonical 名で行われ自動的にマージされる。
        name = COLOR_MASTER.canonical_name(name)
        # 猫種別表示名 (Abyssinian の Ruddy、Oriental の Ebony 等) と一般 Van 正規化を
        # cat_color_display_alias_map.csv 駆動で適用する (データ正本 §4 / §1.1)。
        # canonical 正規化の「後」に置く: Ebony/Chestnut/Lavender は master では alias のため、
        # 先に canonical 化しないと猫種別呼称が一般名へ戻ってしまう。
        name = DISPLAY_ALIAS_MAP.resolve_display_name(name, breed)
        return name

    def _clean_phenotype_name(self, name: str) -> str:
        # すでにCSVに存在する正式なカラー名である場合は、誤置換を防ぐためそのまま返す
        valid_colors = {d["CoatColor"] for d in COLOR_DEFINITIONS}
        if name in valid_colors:
            return name

        is_silver = "Silver" in name and "Tabby" in name
        if is_silver:
            if name.startswith("Black Pt "):
                name = name.replace("Black Pt ", "Silver Pt ").replace(" Silver Tabby", " Tabby")
            elif name.startswith("Black "):
                name = name.replace("Black ", "Silver ").replace(" Silver Tabby", " Tabby")
            elif name.startswith("Blue Pt "):
                name = name.replace("Blue Pt ", "Blue Silver Pt ").replace(" Silver Tabby", " Tabby")
            elif name.startswith("Blue "):
                name = name.replace("Blue ", "Blue Silver ").replace(" Silver Tabby", " Tabby")
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

    def _simplify_patterns(self, name: str, sire_color: str, dam_color: str, breed: str | None) -> str:
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

    @classmethod
    def _is_female_only_color(cls, name: str) -> bool:
        lowered = name.lower()
        return any(marker in lowered for marker in cls._FEMALE_ONLY_MARKERS)

    def _find_matching_color(
        self, kitten: KittenGenotype, sire_color: str, dam_color: str
    ) -> str | None:
        key = _expressed_genotype_key(kitten.loci, kitten.sex)
        candidates = list(GENOTYPE_TO_COLOR_MAP.get((kitten.sex.lower(), key), []))
        if not candidates:
            return None

        # 通常のXYオスにトーティ・キャリコ・クリーム混合系を出さない (要件3)
        if kitten.sex.lower() == "male":
            candidates = [c for c in candidates if not self._is_female_only_color(c)]
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

    @staticmethod
    def _matches_locus_condition(
        kitten_alleles: tuple[str, str], condition: str, locus: str, sex: str
    ) -> bool:
        if not condition or not condition.strip():
            return True

        cond_alleles = condition.strip().split("/")
        if len(cond_alleles) != 2:
            return False

        c1, c2 = cond_alleles
        k1, k2 = kitten_alleles

        if locus == "O":
            if sex.lower() == "male":
                non_y_k = k1 if k2 == "Y" else k2
                if "O" in cond_alleles:
                    return non_y_k == "O"
                if "o" in cond_alleles:
                    return non_y_k == "o"
                return False
            else:
                if (c1 == "O" and c2 == "o") or (c1 == "o" and c2 == "O"):
                    return sorted(kitten_alleles) == ["O", "o"]
                return sorted(kitten_alleles) == sorted([c1, c2])

        if locus == "S":
            return sorted(kitten_alleles) == sorted([c1, c2])

        if c1 == c2 and c1.islower():
            return sorted(kitten_alleles) == sorted([c1, c2])

        if c1 != c2:
            return sorted(kitten_alleles) == sorted([c1, c2])

        dominant_allele = c1
        return dominant_allele in kitten_alleles
