"""毛色確率計算エンジン本体。"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from cat_breeding_simulator.master_data import (
    AUTOSOMAL_LOCI,
    BREED_FILTERS,
    COLOR_BASE_LOCI,
    NORMAL_CLOSED_LOCI,
    NORMAL_OPENED_LOCI,
    PHENOTYPE_GENOTYPES,
    SUPPORTED_MODES,
    VALID_BREEDS,
    KittenGenotype,
    ParentGenotype,
    build_parent_genotypes,
    expressed_genotype_key,
)
from cat_breeding_simulator.color_master import COLOR_MASTER
from cat_breeding_simulator.phenotype_naming import PhenotypeNamer


ProbabilityMap = dict[tuple[str, str], float]


def _genotype_key(loci: dict[str, tuple[str, str]]) -> tuple:
    """遺伝子型をアレル単位でそのまま表すキー (デバッグ・未分類サンプル記録用)。"""

    parts = []
    for locus in sorted(loci.keys()):
        a1, a2 = loci[locus]
        parts.append((locus, tuple(sorted([a1, a2]))))
    return tuple(parts)


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
class ParentColorNote:
    """入力した親の毛色が、この交配では子猫に出現しないことを示す注釈。

    blocked_factors は「子がその形質になれない原因の劣性因子」(相手親が持たない)。
    """

    parent: str                  # "sire" / "dam"
    color: str                   # canonical な親色
    blocked_factors: list[str]   # 例: ["チョコレート b", "非アグーチ（ソリッド） a"]


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
    # 入力した親色が子に出現しないときの注釈 (normal モードのみ)。
    parent_color_notes: list[ParentColorNote] | None = None


class BreedingCalculationError(ValueError):
    """入力や計算前提の不整合。"""


# 劣性アレル → 人間向けラベル。親がこのアレルでホモ接合かつ相手親がそのアレルを
# 持たないとき、その形質は子に出現しない (parent_color_notes の原因説明に使う)。
# 親が劣性ホモで発現し、相手親がそのアレルを (normal 展開後も) 渡せないと子に再現できない因子。
# 注意: D は normal_mode で必ず X/- 展開される (NORMAL_OPENED_LOCI) ため、濃色親 (D/-) も
# 常に d を渡せる = D が単独でブロッカーになることは normal_mode では原理的に起きない。
# それでも一覧として残すのは、判定が「相手親が実際に渡せるアレル集合」に基づくため害がなく、
# 仮に展開規則が変わっても正しく動くようにするため。
_BLOCKING_RECESSIVE_LABELS: dict[str, dict[str, str]] = {
    "A": {"a": "非アグーチ（ソリッド） a"},
    "B": {"b": "チョコレート b", "bl": "シナモン bl"},
    "C": {"cs": "ポイント cs", "cb": "セピア cb"},
    "D": {"d": "希釈（ブルー/クリーム） d"},
}

# O 座位 (X 連鎖): 親が非オレンジ (O を持たない) のに、相手親が o を渡せない場合のブロッカー。
# 相手が赤ホモ (O/O メス or O/Y オス) だと全ての子に O が渡り、非オレンジの子は出ない。
_O_NON_ORANGE_LABEL = "非オレンジ（赤以外） o"


class CoatColorCalculator:
    """Split -> Cross -> Evaluate -> Aggregate を実装する計算器。"""

    def __init__(self) -> None:
        # 遺伝子型 → 表示色名 の命名/分類は PhenotypeNamer へ委譲する。
        self._namer = PhenotypeNamer()

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
                        phenotype = self._namer.classify_phenotype(kitten, sire_color, dam_color)
                        if phenotype is None:
                            # 分類不能を捨てて再正規化せず、未分類率として加算する
                            unmatched_probability += weight
                            expressed = expressed_genotype_key(kitten.loci, kitten.sex)
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
                        phenotype = self._namer.post_process_color_name(
                            phenotype, sire_color, dam_color, breed
                        )
                        matched_probability += weight
                        aggregate[(kitten.sex, phenotype)] += weight

        results = self._to_results(aggregate, unmatched_probability)
        opened_loci, closed_loci, assumptions = self._build_mode_metadata(
            mode, sire_carriers, dam_carriers
        )
        # 入力した親色が子に出ないときの注釈 (劣性形質の理解補助)。normal モードのみ。
        offspring_colors = {phenotype for (_sex, phenotype) in aggregate}
        parent_color_notes = (
            self._build_parent_color_notes(sire_color, dam_color, breed, offspring_colors)
            if mode == "normal"
            else None
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
            parent_color_notes=parent_color_notes or None,
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

    def _build_parent_color_notes(
        self,
        sire_color: str,
        dam_color: str,
        breed: str | None,
        offspring_colors: set[str],
    ) -> list[ParentColorNote]:
        """入力した親色が子に出現しないケースの注釈を作る (出現する親は注釈なし)。"""

        notes: list[ParentColorNote] = []
        parents = (
            ("sire", sire_color, "male", dam_color, "female"),
            ("dam", dam_color, "female", sire_color, "male"),
        )
        for parent, color, sex, other_color, other_sex in parents:
            name = self._resolve_input_color_name(color, breed)
            # 子の出現色 (offspring_colors) は表示名なので、親色も同じ表示パイプラインに
            # 通してから比較する (display_alias / Van 正規化等での誤検知を防ぐ)。
            display = self._namer.post_process_color_name(name, sire_color, dam_color, breed)
            if display in offspring_colors:
                continue  # 親色が子に出るなら注釈不要
            blocked = self._blocking_recessive_factors(color, sex, other_color, other_sex, breed)
            notes.append(
                ParentColorNote(parent=parent, color=display, blocked_factors=blocked)
            )
        return notes

    def _contributable_alleles(
        self, color: str, sex: str, breed: str | None
    ) -> dict[str, set[str]]:
        """親が normal_mode の交配で実際に子へ渡しうるアレル集合を座位別に返す。

        CSV ベース遺伝子型ではなく X/- 展開後の全候補から集めるのが要点。例: 濃色 (D/-)
        親は normal_mode で {D/D, D/d} に展開されるため d も渡せる (= 希釈の子が出る)。
        ベースだけを見ると「d を持たない」と誤判定するため、ここで展開を反映する。
        """

        try:
            genotypes = self._resolve_parent_genotypes(color, sex, breed, "normal", None)
        except BreedingCalculationError:
            return {}
        alleles: dict[str, set[str]] = {}
        for genotype in genotypes:
            for locus, pair in genotype.loci.items():
                alleles.setdefault(locus, set()).update(pair)
        return alleles

    def _blocking_recessive_factors(
        self,
        color: str,
        sex: str,
        other_color: str,
        other_sex: str,
        breed: str | None,
    ) -> list[str]:
        """親色が子に再現できない原因の因子を返す。

        相手親が「normal_mode 展開後に渡せるアレル集合」を基準に判定する (CSV ベースだけを
        見ると D 等の X/- 展開座位を誤ってブロッカー扱いしてしまう)。
        """

        base = self._resolved_base_loci(color, sex, breed)
        if base is None:
            return []
        other_alleles = self._contributable_alleles(other_color, other_sex, breed)
        self_alleles = self._contributable_alleles(color, sex, breed)
        if not other_alleles or not self_alleles:
            return []

        factors: list[str] = []
        # 常染色体劣性 (A/B/C/D): 親が劣性ホモ かつ 相手が展開後もそのアレルを渡せない。
        for locus, allele_labels in _BLOCKING_RECESSIVE_LABELS.items():
            pair = base.get(locus)
            if pair is None or pair[0] != pair[1]:
                continue  # 親がこの座位でホモ接合でない
            label = allele_labels.get(pair[0])
            if label is None:
                continue  # 追跡対象の劣性アレルでない
            if pair[0] not in other_alleles.get(locus, set()):
                factors.append(label)  # 相手が渡せない → 子に再現不可

        # O 座位 (X 連鎖): 親が非オレンジ (O を持たない) のに相手が o を渡せない場合。
        # 相手が赤ホモ (O/O / O/Y) だと全ての子に O が渡り、非オレンジの親色は出ない。
        self_o = self_alleles.get("O", set())
        if self_o and "O" not in self_o and "o" not in other_alleles.get("O", set()):
            factors.append(_O_NON_ORANGE_LABEL)

        return factors

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


