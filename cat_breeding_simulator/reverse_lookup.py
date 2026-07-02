"""目標カラーから交配候補を探す逆引きロジック。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from cat_breeding_simulator.color_master import COLOR_MASTER
from cat_breeding_simulator.engine import BreedingCalculationError, CoatColorCalculator, KittenResult

RegisteredSex = Literal["male", "female"]
ParentRole = Literal["sire", "dam"]


@dataclass(frozen=True, slots=True)
class RegisteredCat:
    """逆引き対象として登録された猫。"""

    id: str
    name: str
    sex: RegisteredSex
    color: str
    breed: str | None = None
    carriers: dict[str, str] | None = None


@dataclass(frozen=True, slots=True)
class RegisteredCatSummary:
    """交配候補表示用の登録猫概要。"""

    id: str
    name: str
    color: str
    breed: str | None


@dataclass(frozen=True, slots=True)
class LocusEvidence:
    """座位別に、目標カラー成立に必要な条件と親が渡せるアレルを示す。"""

    locus: str
    target: str
    sire: str
    dam: str
    status: str
    note: str


@dataclass(frozen=True, slots=True)
class ReverseLookupCandidate:
    """目標カラーが生まれる可能性のある交配候補。"""

    category: str
    sire: RegisteredCatSummary
    dam: RegisteredCatSummary
    target_color: str
    confirmed_probability_pct: float
    conditional_max_probability_pct: float
    establishment_conditions: list[str]
    confirmation_needed: list[str]
    recommended_tests: list[str]
    locus_evidence: list[LocusEvidence]
    target_possible_colors: list[KittenResult]
    other_possible_colors: list[KittenResult]


@dataclass(frozen=True, slots=True)
class HiddenCondition:
    """条件付き最大確率を計算するために仮定する未確認因子。"""

    parent: ParentRole
    cat_name: str
    cat_color: str
    locus: str
    genotype: str
    allele: str


@dataclass(frozen=True, slots=True)
class ReverseLookupReport:
    """逆引きAPIが返す候補と、候補が無い場合にも表示する分析。"""

    target_color: str
    target_sex: RegisteredSex | None
    response_category: str
    candidates: list[ReverseLookupCandidate]
    target_conditions: list[str]
    unchecked_conditions: list[str]
    recommended_checks: list[str]


@dataclass(frozen=True, slots=True)
class TargetResolution:
    """目標カラーを内部座位へ解決できた猫種文脈。"""

    breed: str | None
    loci: dict[str, tuple[str, str]]


_LOCUS_ORDER: tuple[str, ...] = ("B", "D", "A", "O", "C", "W", "I", "Wb", "S")
_PARENT_LABELS: dict[ParentRole, str] = {"sire": "父猫", "dam": "母猫"}
_CATEGORY_CONFIRMED = "確定で期待できる"
_CATEGORY_CONDITIONAL = "条件付きで期待できる"
_CATEGORY_DIFFICULT = "現在の情報では判定が難しい"
_CATEGORY_NOT_CONFIRMED = "現在の登録情報では確認できない"

_LOCUS_LABELS: dict[str, str] = {
    "A": "A座位",
    "B": "B座位",
    "C": "C座位",
    "D": "D座位",
    "I": "I座位",
    "O": "O座位",
    "S": "S座位",
    "W": "W座位",
    "Wb": "ゴールデン修飾",
}
_TEST_LABELS: dict[str, str] = {
    "A": "A座位（アグーティ/ソリッド）の確認",
    "B": "B座位（チョコレート/シナモン）の遺伝子検査",
    "C": "C座位（ポイント/セピア）の遺伝子検査",
    "D": "D座位（ダイリュート）の遺伝子検査",
    "I": "I座位（シルバー/スモーク）の確認",
    "W": "W座位（優性白）の確認",
    "Wb": "ゴールデン修飾・ワイドバンドの確認",
}
_ALLELE_FACTOR_LABELS: dict[str, dict[str, str]] = {
    "A": {"a": "ソリッド因子 a"},
    "B": {"b": "チョコレート因子 b", "bl": "シナモン因子 b^l"},
    "C": {"cs": "ポイント因子 cs", "cb": "セピア因子 cb"},
    "D": {"d": "ダイリュート因子 d"},
    "I": {"i": "非シルバー因子 i"},
    "Wb": {"wb": "非ワイドバンド因子 wb"},
}


class ReverseLookupService:
    """登録猫リストと目標カラーから交配候補を計算するサービス。"""

    def __init__(self, calculator: CoatColorCalculator | None = None) -> None:
        self._calculator = calculator or CoatColorCalculator()

    def find_candidates(
        self,
        target_color: str,
        cats: list[RegisteredCat],
        target_sex: RegisteredSex | None = None,
        limit: int = 20,
    ) -> ReverseLookupReport:
        """登録猫の父母候補を総当たりし、目標カラーに届く候補と分析を返す。"""

        self._validate_registered_cats(cats)
        target_resolution = self._target_resolution(target_color, cats, target_sex)
        display_target = self._display_target_color(
            target_color,
            target_resolution.breed if target_resolution else None,
        )
        if target_resolution is None:
            return ReverseLookupReport(
                target_color=display_target,
                target_sex=target_sex,
                response_category=_CATEGORY_DIFFICULT,
                candidates=[],
                target_conditions=["現在の対応範囲外、または猫種文脈が必要な目標カラーです。"],
                unchecked_conditions=["目標カラーを内部遺伝子条件へ解決できませんでした。"],
                recommended_checks=["対応済みカラー名、猫種固有名、または別名の表記を確認してください。"],
            )
        target_loci = target_resolution.loci

        sires = [cat for cat in cats if cat.sex == "male"]
        dams = [cat for cat in cats if cat.sex == "female"]
        if not sires or not dams:
            return ReverseLookupReport(
                target_color=display_target,
                target_sex=target_sex,
                response_category=_CATEGORY_DIFFICULT,
                candidates=[],
                target_conditions=self._target_conditions(
                    target_loci,
                    target_color,
                    target_resolution.breed,
                    target_sex,
                ),
                unchecked_conditions=["父猫・母猫の両方が登録されていないため、交配候補を評価できません。"],
                recommended_checks=["父猫として評価する登録猫と、母猫として評価する登録猫を追加してください。"],
            )

        candidates: list[ReverseLookupCandidate] = []
        for sire in sires:
            for dam in dams:
                candidate = self._evaluate_pair(target_color, target_sex, sire, dam)
                if candidate is not None:
                    candidates.append(candidate)
        candidates.sort(
            key=lambda candidate: (
                -candidate.confirmed_probability_pct,
                -candidate.conditional_max_probability_pct,
                candidate.sire.name,
                candidate.dam.name,
            )
        )
        limited = candidates[:limit]
        return ReverseLookupReport(
            target_color=display_target,
            target_sex=target_sex,
            response_category=self._response_category(limited),
            candidates=limited,
            target_conditions=self._target_conditions(
                target_loci,
                target_color,
                target_resolution.breed,
                target_sex,
            ),
            unchecked_conditions=[] if limited else self._unchecked_conditions(target_loci, sires, dams),
            recommended_checks=[] if limited else self._recommended_checks_for_loci(target_loci.keys()),
        )

    @staticmethod
    def _response_category(candidates: list[ReverseLookupCandidate]) -> str:
        if any(candidate.category == _CATEGORY_CONFIRMED for candidate in candidates):
            return _CATEGORY_CONFIRMED
        if any(candidate.category == _CATEGORY_CONDITIONAL for candidate in candidates):
            return _CATEGORY_CONDITIONAL
        return _CATEGORY_NOT_CONFIRMED

    def _validate_registered_cats(self, cats: list[RegisteredCat]) -> None:
        """保存済み・API直送の登録猫も通常シミュレーターと同じ親入力条件で検証する。"""

        for cat in cats:
            mode = "explicit_carrier" if cat.carriers else "normal"
            self._calculator.validate_parent_color(
                color=cat.color,
                sex=cat.sex,
                breed=cat.breed,
                mode=mode,
                carriers=cat.carriers,
            )

    def _evaluate_pair(
        self,
        target_color: str,
        target_sex: RegisteredSex | None,
        sire: RegisteredCat,
        dam: RegisteredCat,
    ) -> ReverseLookupCandidate | None:
        breed = self._pair_breed(sire, dam)
        mode = "explicit_carrier" if sire.carriers or dam.carriers else "normal"
        try:
            base_report = self._calculator.calculate_report(
                sire_color=sire.color,
                dam_color=dam.color,
                breed=breed,
                mode=mode,
                sire_carriers=sire.carriers,
                dam_carriers=dam.carriers,
            )
        except BreedingCalculationError:
            return None

        conditions = self._hidden_conditions_for_pair(target_color, target_sex, sire, dam, breed)
        confirmed_probability = (
            0.0
            if conditions
            else self._target_probability(base_report.results, target_color, breed, target_sex)
        )
        conditional_report = base_report
        conditional_probability = confirmed_probability
        if conditions:
            sire_carriers = self._merge_carriers(sire.carriers, conditions, "sire")
            dam_carriers = self._merge_carriers(dam.carriers, conditions, "dam")
            try:
                conditional_report = self._calculator.calculate_report(
                    sire.color,
                    dam.color,
                    breed,
                    mode="explicit_carrier",
                    sire_carriers=sire_carriers,
                    dam_carriers=dam_carriers,
                )
                conditional_probability = self._target_probability(
                    conditional_report.results, target_color, breed, target_sex
                )
            except BreedingCalculationError:
                conditional_probability = 0.0

        conditional_max = max(confirmed_probability, conditional_probability)
        if conditional_max <= 0:
            return None

        category = _CATEGORY_CONFIRMED if confirmed_probability > 0 else _CATEGORY_CONDITIONAL
        return ReverseLookupCandidate(
            category=category,
            sire=self._summary(sire),
            dam=self._summary(dam),
            target_color=self._display_target_color(target_color, breed),
            confirmed_probability_pct=round(confirmed_probability, 4),
            conditional_max_probability_pct=round(conditional_max, 4),
            establishment_conditions=self._establishment_conditions(
                confirmed_probability,
                conditional_probability,
                conditions,
            ),
            confirmation_needed=self._confirmation_needed(conditions),
            recommended_tests=self._recommended_tests(conditions),
            locus_evidence=self._locus_evidence(
                target_color,
                target_sex,
                sire,
                dam,
                breed,
                mode,
                conditions,
            ),
            target_possible_colors=self._target_possible_colors(
                conditional_report.results,
                target_color,
                breed,
                target_sex,
            ),
            other_possible_colors=self._other_possible_colors(
                conditional_report.results,
                target_color,
                breed,
                target_sex,
            ),
        )

    @staticmethod
    def _pair_breed(sire: RegisteredCat, dam: RegisteredCat) -> str | None:
        """父母の猫種が同一の場合だけ猫種制約を計算に使う。"""

        if sire.breed and dam.breed and sire.breed == dam.breed:
            return sire.breed
        return None

    @staticmethod
    def _summary(cat: RegisteredCat) -> RegisteredCatSummary:
        return RegisteredCatSummary(id=cat.id, name=cat.name, color=cat.color, breed=cat.breed)

    def _display_target_color(self, target_color: str, breed: str | None) -> str:
        try:
            return self._calculator.display_color_name(target_color, breed)
        except BreedingCalculationError:
            return COLOR_MASTER.canonical_name(target_color)

    def _target_loci(
        self,
        target_color: str,
        breed: str | None,
        target_sex: RegisteredSex | None = None,
    ) -> dict[str, tuple[str, str]] | None:
        try:
            if target_sex is not None:
                return self._calculator.resolved_color_loci(target_color, target_sex, breed)
            return (
                self._calculator.resolved_color_loci(target_color, "female", breed)
                or self._calculator.resolved_color_loci(target_color, "male", breed)
            )
        except BreedingCalculationError:
            return None

    def _target_resolution(
        self,
        target_color: str,
        cats: list[RegisteredCat],
        target_sex: RegisteredSex | None,
    ) -> TargetResolution | None:
        for breed in self._target_breed_candidates(cats):
            loci = self._target_loci(target_color, breed, target_sex)
            if loci is not None:
                return TargetResolution(breed=breed, loci=loci)
        return None

    @staticmethod
    def _target_breed_candidates(cats: list[RegisteredCat]) -> list[str | None]:
        breeds: list[str | None] = [None]
        seen: set[str] = set()
        for cat in cats:
            if cat.breed is None or cat.breed in seen:
                continue
            seen.add(cat.breed)
            breeds.append(cat.breed)
        return breeds

    def _target_names(self, target_color: str, breed: str | None) -> set[str]:
        names = {target_color, COLOR_MASTER.canonical_name(target_color)}
        try:
            display = self._calculator.display_color_name(target_color, breed)
            names.add(display)
            names.add(COLOR_MASTER.canonical_name(display))
        except BreedingCalculationError:
            pass
        return names

    def _target_probability(
        self,
        results: list[KittenResult],
        target_color: str,
        breed: str | None,
        target_sex: RegisteredSex | None,
    ) -> float:
        target_names = self._target_names(target_color, breed)
        total = 0.0
        for result in results:
            if not _matches_target_sex(result.sex, target_sex):
                continue
            result_names = {result.color, COLOR_MASTER.canonical_name(result.color)}
            if target_names & result_names:
                total += result.probability_pct
        return total

    def _target_possible_colors(
        self,
        results: list[KittenResult],
        target_color: str,
        breed: str | None,
        target_sex: RegisteredSex | None,
    ) -> list[KittenResult]:
        """目標色そのものとして生まれる性別別内訳を返す。"""

        target_names = self._target_names(target_color, breed)
        out: list[KittenResult] = []
        for result in results:
            if not _matches_target_sex(result.sex, target_sex):
                continue
            result_names = {result.color, COLOR_MASTER.canonical_name(result.color)}
            if target_names & result_names:
                out.append(result)
        return _sex_balanced_results(out)

    def _other_possible_colors(
        self,
        results: list[KittenResult],
        target_color: str,
        breed: str | None,
        target_sex: RegisteredSex | None,
    ) -> list[KittenResult]:
        target_names = self._target_names(target_color, breed)
        out: list[KittenResult] = []
        for result in results:
            result_names = {result.color, COLOR_MASTER.canonical_name(result.color)}
            if target_names & result_names and _matches_target_sex(result.sex, target_sex):
                continue
            out.append(result)
        return _sex_balanced_results(out)

    def _hidden_conditions_for_pair(
        self,
        target_color: str,
        target_sex: RegisteredSex | None,
        sire: RegisteredCat,
        dam: RegisteredCat,
        breed: str | None,
    ) -> list[HiddenCondition]:
        target_loci = self._target_loci(target_color, breed, target_sex)
        sire_loci = self._calculator.resolved_color_loci(sire.color, "male", breed)
        dam_loci = self._calculator.resolved_color_loci(dam.color, "female", breed)
        if target_loci is None or sire_loci is None or dam_loci is None:
            return []

        conditions: list[HiddenCondition] = []
        for locus in _LOCUS_ORDER:
            if locus == "O":
                continue
            target_pair = target_loci.get(locus)
            sire_pair = sire_loci.get(locus)
            dam_pair = dam_loci.get(locus)
            if target_pair is None or sire_pair is None or dam_pair is None:
                continue
            first, second = target_pair
            if self._pair_can_supply(first, second, sire_pair, dam_pair):
                continue
            sire_can_first = self._can_gain_hidden_allele(locus, sire_pair, first)
            sire_can_second = self._can_gain_hidden_allele(locus, sire_pair, second)
            dam_can_first = self._can_gain_hidden_allele(locus, dam_pair, first)
            dam_can_second = self._can_gain_hidden_allele(locus, dam_pair, second)

            if first in sire_pair and dam_can_second:
                conditions.append(self._condition("dam", dam, locus, dam_pair, second))
            elif second in sire_pair and dam_can_first:
                conditions.append(self._condition("dam", dam, locus, dam_pair, first))
            elif first in dam_pair and sire_can_second:
                conditions.append(self._condition("sire", sire, locus, sire_pair, second))
            elif second in dam_pair and sire_can_first:
                conditions.append(self._condition("sire", sire, locus, sire_pair, first))
            elif sire_can_first and dam_can_second:
                conditions.append(self._condition("sire", sire, locus, sire_pair, first))
                conditions.append(self._condition("dam", dam, locus, dam_pair, second))
            elif sire_can_second and dam_can_first:
                conditions.append(self._condition("sire", sire, locus, sire_pair, second))
                conditions.append(self._condition("dam", dam, locus, dam_pair, first))
        return self._dedupe_conditions(conditions)

    @staticmethod
    def _pair_can_supply(
        first: str,
        second: str,
        sire_pair: tuple[str, str],
        dam_pair: tuple[str, str],
    ) -> bool:
        return (first in sire_pair and second in dam_pair) or (
            second in sire_pair and first in dam_pair
        )

    @staticmethod
    def _condition(
        parent: ParentRole,
        cat: RegisteredCat,
        locus: str,
        current_pair: tuple[str, str],
        allele: str,
    ) -> HiddenCondition:
        visible = current_pair[0] if current_pair[0] == current_pair[1] else current_pair[0]
        genotype = f"{visible}/{allele}"
        return HiddenCondition(
            parent=parent,
            cat_name=cat.name,
            cat_color=cat.color,
            locus=locus,
            genotype=genotype,
            allele=allele,
        )

    @staticmethod
    def _dedupe_conditions(conditions: list[HiddenCondition]) -> list[HiddenCondition]:
        seen: set[tuple[str, str, str, str]] = set()
        out: list[HiddenCondition] = []
        for condition in conditions:
            key = (condition.parent, condition.cat_name, condition.locus, condition.genotype)
            if key in seen:
                continue
            seen.add(key)
            out.append(condition)
        return out

    @staticmethod
    def _can_gain_hidden_allele(
        locus: str,
        current_pair: tuple[str, str],
        allele: str,
    ) -> bool:
        if allele in current_pair:
            return True
        if locus == "B":
            if "B" in current_pair and allele in {"b", "bl"}:
                return True
            if current_pair == ("b", "b") and allele == "bl":
                return True
            return False
        if locus == "D":
            return "D" in current_pair and allele == "d"
        if locus == "A":
            return "A" in current_pair and allele == "a"
        if locus == "C":
            return "C" in current_pair and allele in {"cs", "cb"}
        if locus == "I":
            return "I" in current_pair and allele == "i"
        if locus == "Wb":
            return "Wb" in current_pair and allele == "wb"
        return False

    @staticmethod
    def _merge_carriers(
        existing: dict[str, str] | None,
        conditions: list[HiddenCondition],
        parent: ParentRole,
    ) -> dict[str, str] | None:
        merged: dict[str, str] = dict(existing or {})
        for condition in conditions:
            if condition.parent == parent:
                merged[condition.locus] = condition.genotype
        return merged or None

    @staticmethod
    def _establishment_conditions(
        confirmed_probability: float,
        conditional_probability: float,
        conditions: list[HiddenCondition],
    ) -> list[str]:
        if confirmed_probability > 0:
            return ["登録済みの毛色・確認済み因子だけで成立"]
        out = [
            f"{condition.cat_name}が{_factor_label(condition.locus, condition.allele)} を持つ"
            for condition in conditions
        ]
        if conditional_probability > 0:
            out.append(f"上記条件が成立する場合の最大確率: {conditional_probability:.1f}%")
        return out

    @staticmethod
    def _confirmation_needed(conditions: list[HiddenCondition]) -> list[str]:
        return [
            f"{condition.cat_name}の{_LOCUS_LABELS.get(condition.locus, condition.locus)}"
            for condition in conditions
        ]

    @staticmethod
    def _recommended_tests(conditions: list[HiddenCondition]) -> list[str]:
        tests: list[str] = []
        for condition in conditions:
            label = _TEST_LABELS.get(condition.locus)
            if label:
                tests.append(f"{condition.cat_name}: {label}")
        return list(dict.fromkeys(tests))

    def _locus_evidence(
        self,
        target_color: str,
        target_sex: RegisteredSex | None,
        sire: RegisteredCat,
        dam: RegisteredCat,
        breed: str | None,
        mode: str,
        conditions: list[HiddenCondition],
    ) -> list[LocusEvidence]:
        target_loci = self._target_loci(target_color, breed, target_sex)
        if target_loci is None:
            return []
        sire_alleles = self._calculator.contributable_alleles(
            sire.color, "male", breed, mode, sire.carriers
        )
        dam_alleles = self._calculator.contributable_alleles(
            dam.color, "female", breed, mode, dam.carriers
        )
        conditions_by_locus = {condition.locus for condition in conditions}

        evidence: list[LocusEvidence] = []
        for locus in _LOCUS_ORDER:
            target_pair = target_loci.get(locus)
            if target_pair is None:
                continue
            sire_set = set(sire_alleles.get(locus, set()))
            dam_set = set(dam_alleles.get(locus, set()))
            can_supply = self._can_supply_target_locus(
                locus,
                target_pair,
                sire_set,
                dam_set,
                target_color,
                breed,
                target_sex,
            )
            status = "confirmed" if can_supply and locus not in conditions_by_locus else "needs_confirmation"
            if status == "confirmed":
                note = "現在の登録条件で必要アレルを渡せます。"
            else:
                note = "未確認因子、または猫種・入力条件の追加確認が必要です。"
            evidence.append(
                LocusEvidence(
                    locus=locus,
                    target=self._target_pair_label(
                        locus,
                        target_pair,
                        target_color,
                        breed,
                        target_sex,
                    ),
                    sire=self._format_alleles(sire_set),
                    dam=self._format_alleles(dam_set),
                    status=status,
                    note=note,
                )
            )
        return evidence

    def _can_supply_target_locus(
        self,
        locus: str,
        target_pair: tuple[str, str],
        sire_alleles: set[str],
        dam_alleles: set[str],
        target_color: str,
        breed: str | None,
        target_sex: RegisteredSex | None,
    ) -> bool:
        if locus == "O":
            return any(
                self._can_supply_o_target_pair(sex, pair, sire_alleles, dam_alleles)
                for sex, pair in self._o_target_pairs(target_color, breed, target_sex)
            )
        return self._can_supply_target_pair(target_pair, sire_alleles, dam_alleles)

    @staticmethod
    def _can_supply_target_pair(
        target_pair: tuple[str, str],
        sire_alleles: set[str],
        dam_alleles: set[str],
    ) -> bool:
        first, second = target_pair
        return (first in sire_alleles and second in dam_alleles) or (
            second in sire_alleles and first in dam_alleles
        )

    @staticmethod
    def _can_supply_o_target_pair(
        sex: RegisteredSex,
        target_pair: tuple[str, str],
        sire_alleles: set[str],
        dam_alleles: set[str],
    ) -> bool:
        """O座位は父が娘へO/o、息子へYを渡すため常染色体と分けて判定する。"""

        if sex == "male":
            required = "O" if "O" in target_pair else "o"
            return "Y" in sire_alleles and required in dam_alleles
        first, second = target_pair
        return (first in sire_alleles and second in dam_alleles) or (
            second in sire_alleles and first in dam_alleles
        )

    @staticmethod
    def _format_alleles(alleles: set[str]) -> str:
        if not alleles:
            return "未確認"
        return ", ".join(_format_allele(allele) for allele in sorted(alleles))

    def _target_conditions(
        self,
        target_loci: dict[str, tuple[str, str]],
        target_color: str,
        breed: str | None,
        target_sex: RegisteredSex | None,
    ) -> list[str]:
        conditions: list[str] = []
        for locus in _LOCUS_ORDER:
            pair = target_loci.get(locus)
            if pair is None:
                continue
            label = _LOCUS_LABELS.get(locus, locus)
            target_label = self._target_pair_label(
                locus,
                pair,
                target_color,
                breed,
                target_sex,
            )
            conditions.append(f"{label}: {target_label}")
        return conditions

    def _target_pair_label(
        self,
        locus: str,
        target_pair: tuple[str, str],
        target_color: str,
        breed: str | None,
        target_sex: RegisteredSex | None,
    ) -> str:
        """性別未指定のO座位だけ、オス/メス双方の条件を見える化する。"""

        if locus != "O":
            return _format_pair(target_pair)
        pairs = self._o_target_pairs(target_color, breed, target_sex)
        if target_sex is None and len(pairs) > 1:
            return " / ".join(
                f"{_format_pair(pair)}（{_sex_label(sex)}）"
                for sex, pair in pairs
            )
        return _format_pair(target_pair)

    def _o_target_pairs(
        self,
        target_color: str,
        breed: str | None,
        target_sex: RegisteredSex | None,
    ) -> list[tuple[RegisteredSex, tuple[str, str]]]:
        """目標色のO座位条件を、対象性別ごとに解決する。"""

        sexes: tuple[RegisteredSex, ...] = (
            (target_sex,) if target_sex is not None else ("male", "female")
        )
        pairs: list[tuple[RegisteredSex, tuple[str, str]]] = []
        for sex in sexes:
            try:
                loci = self._calculator.resolved_color_loci(target_color, sex, breed)
            except BreedingCalculationError:
                continue
            if loci is None or "O" not in loci:
                continue
            item = (sex, loci["O"])
            if item not in pairs:
                pairs.append(item)
        return pairs

    def _unchecked_conditions(
        self,
        target_loci: dict[str, tuple[str, str]],
        sires: list[RegisteredCat],
        dams: list[RegisteredCat],
    ) -> list[str]:
        out: list[str] = []
        for locus in _LOCUS_ORDER:
            if locus == "O":
                continue
            pair = target_loci.get(locus)
            if pair is None:
                continue
            if self._any_pair_can_meet_locus(locus, pair, sires, dams):
                continue
            label = _LOCUS_LABELS.get(locus, locus)
            if locus == "Wb":
                out.append("ゴールデン修飾の継承条件を確認できる組み合わせがありません。")
            else:
                out.append(
                    f"{label}: 必要アレル {'/'.join(_format_allele(allele) for allele in pair)} "
                    "を両親側から受け継げる組み合わせを確認できません。"
                )
        return out or ["現在の登録情報では、目標カラーの成立条件を満たす交配候補を確認できません。"]

    def _any_pair_can_meet_locus(
        self,
        locus: str,
        target_pair: tuple[str, str],
        sires: list[RegisteredCat],
        dams: list[RegisteredCat],
    ) -> bool:
        for sire in sires:
            for dam in dams:
                breed = self._pair_breed(sire, dam)
                try:
                    sire_loci = self._calculator.resolved_color_loci(sire.color, "male", breed)
                    dam_loci = self._calculator.resolved_color_loci(dam.color, "female", breed)
                except BreedingCalculationError:
                    continue
                if sire_loci is None or locus not in sire_loci:
                    continue
                if dam_loci is None or locus not in dam_loci:
                    continue
                first, second = target_pair
                sire_pair = sire_loci[locus]
                dam_pair = dam_loci[locus]
                if self._pair_can_supply(first, second, sire_pair, dam_pair):
                    return True
                if self._can_gain_hidden_allele(locus, sire_pair, first) and self._can_gain_hidden_allele(locus, dam_pair, second):
                    return True
                if self._can_gain_hidden_allele(locus, sire_pair, second) and self._can_gain_hidden_allele(locus, dam_pair, first):
                    return True
        return False

    @staticmethod
    def _recommended_checks_for_loci(loci: object) -> list[str]:
        checks: list[str] = []
        for locus in loci:
            if not isinstance(locus, str):
                continue
            label = _TEST_LABELS.get(locus)
            if label:
                checks.append(label)
        return list(dict.fromkeys(checks))


def _format_allele(allele: str) -> str:
    """bl をUI向けに b^l と表示する。"""

    return "b^l" if allele == "bl" else allele


def _format_pair(pair: tuple[str, str]) -> str:
    """アレルペアをUI向けに A/a 形式で表示する。"""

    return "/".join(_format_allele(allele) for allele in pair)


def _sex_label(sex: RegisteredSex) -> str:
    """座位条件の補足に使う短い性別ラベル。"""

    return "オス" if sex == "male" else "メス"


def _matches_target_sex(result_sex: str, target_sex: RegisteredSex | None) -> bool:
    """性別指定がある場合だけ、子猫結果の性別を絞り込む。"""

    if target_sex is None:
        return True
    expected = "Male" if target_sex == "male" else "Female"
    return result_sex == expected


def _sex_balanced_results(results: list[KittenResult]) -> list[KittenResult]:
    """表示時に片方の性別だけが先に並ばないよう、オス→メスで交互に返す。"""

    male_rows = [result for result in results if result.sex == "Male"]
    female_rows = [result for result in results if result.sex == "Female"]
    other_rows = [result for result in results if result.sex not in {"Male", "Female"}]
    balanced: list[KittenResult] = []
    max_length = max(len(male_rows), len(female_rows))
    for index in range(max_length):
        if index < len(male_rows):
            balanced.append(male_rows[index])
        if index < len(female_rows):
            balanced.append(female_rows[index])
    balanced.extend(other_rows)
    return balanced


def _factor_label(locus: str, allele: str) -> str:
    return _ALLELE_FACTOR_LABELS.get(locus, {}).get(allele, f"{_format_allele(allele)} 因子")
