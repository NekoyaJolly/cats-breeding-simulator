"""リター実績から両親の隠れ因子を推定するMVPロジック。"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Literal

from cat_breeding_simulator.engine import BreedingCalculationError, CoatColorCalculator
from cat_breeding_simulator.master_data import KittenGenotype, ParentGenotype


ObservedSex = Literal["male", "female"]
ParentRole = Literal["sire", "dam"]


@dataclass(frozen=True, slots=True)
class LitterParent:
    """リター推定に使う親猫入力。"""

    color: str
    breed: str | None = None


@dataclass(frozen=True, slots=True)
class ObservedKitten:
    """観察された子猫1頭の入力。"""

    id: str
    sex: ObservedSex
    color: str
    name: str | None = None


@dataclass(frozen=True, slots=True)
class InferenceFinding:
    """座位ごとの推定結果。"""

    category: str
    parent: str
    locus: str
    genotype: str
    note: str
    support_pct: float


@dataclass(frozen=True, slots=True)
class LitterInferenceReport:
    """リター推定APIの返却用レポート。"""

    response_category: str
    candidate_pair_count: int
    confirmed: list[InferenceFinding]
    conditional: list[InferenceFinding]
    inferred: list[InferenceFinding]
    unconfirmed: list[InferenceFinding]
    contradictions: list[str]
    warnings: list[str]
    recommended_tests: list[str]


_LOCUS_ORDER: tuple[str, ...] = ("B", "D", "A", "O", "C", "I", "S", "Wb")
_PARENT_LABELS: dict[ParentRole, str] = {"sire": "父猫", "dam": "母猫"}
_TEST_LABELS: dict[str, str] = {
    "A": "A座位（アグーティ/ソリッド）の表現確認または産子履歴確認",
    "B": "B座位（チョコレート/シナモン）の遺伝子検査",
    "C": "C座位（ポイント/セピア）の遺伝子検査",
    "D": "D座位（ダイリュート）の遺伝子検査",
    "I": "I座位（シルバー/スモーク）の確認",
    "S": "S座位（白斑）の確認",
    "Wb": "ゴールデン修飾・ワイドバンドの確認",
}
_ALLELE_ORDER: dict[str, dict[str, int]] = {
    "B": {"B": 0, "b": 1, "bl": 2},
    "D": {"D": 0, "d": 1},
    "A": {"A": 0, "a": 1},
    "C": {"C": 0, "cb": 1, "cs": 2},
    "I": {"I": 0, "i": 1},
    "S": {"S": 0, "s": 1},
    "Wb": {"Wb": 0, "wb": 1},
}


class LitterInferenceService:
    """親表現型と観察子猫群から、両親候補を絞り込むサービス。"""

    def __init__(self, calculator: CoatColorCalculator | None = None) -> None:
        self._calculator = calculator or CoatColorCalculator()

    def infer(
        self,
        sire: LitterParent,
        dam: LitterParent,
        kittens: list[ObservedKitten],
    ) -> LitterInferenceReport:
        """観察された全子猫を説明できる父母遺伝子型候補を残し、座位別に分類する。"""

        breed = self._shared_breed(sire, dam)
        self._calculator.validate_parent_color(sire.color, "male", breed)
        self._calculator.validate_parent_color(dam.color, "female", breed)
        sire_candidates = self._calculator.parent_genotype_candidates(
            sire.color,
            "male",
            breed,
            include_unconfirmed_carriers=True,
        )
        dam_candidates = self._calculator.parent_genotype_candidates(
            dam.color,
            "female",
            breed,
            include_unconfirmed_carriers=True,
        )
        observed_candidates = [
            self._observed_candidate_signatures(kitten, breed) for kitten in kittens
        ]

        surviving_pairs: list[tuple[ParentGenotype, ParentGenotype]] = []
        for sire_candidate in sire_candidates:
            for dam_candidate in dam_candidates:
                generated = self._calculator.possible_kitten_genotypes(
                    sire_candidate,
                    dam_candidate,
                )
                if all(
                    self._can_explain_observed(generated, candidate)
                    for candidate in observed_candidates
                ):
                    surviving_pairs.append((sire_candidate, dam_candidate))

        warnings = self._warnings(kittens)
        if not surviving_pairs:
            return LitterInferenceReport(
                response_category="矛盾",
                candidate_pair_count=0,
                confirmed=[],
                conditional=[],
                inferred=[],
                unconfirmed=[],
                contradictions=[
                    "現在の親カラー候補では、観察された全子猫カラー・性別を同時に説明できません。"
                ],
                warnings=warnings,
                recommended_tests=["親猫・子猫のカラー名、性別、白斑有無を再確認してください。"],
            )

        confirmed, conditional, inferred, unconfirmed = self._findings(surviving_pairs)
        recommended_tests = self._recommended_tests(conditional, unconfirmed, warnings)
        return LitterInferenceReport(
            response_category="推定可能",
            candidate_pair_count=len(surviving_pairs),
            confirmed=confirmed,
            conditional=conditional,
            inferred=inferred,
            unconfirmed=unconfirmed,
            contradictions=[],
            warnings=warnings,
            recommended_tests=recommended_tests,
        )

    @staticmethod
    def _shared_breed(sire: LitterParent, dam: LitterParent) -> str | None:
        if sire.breed and dam.breed and sire.breed != dam.breed:
            raise BreedingCalculationError(
                "父猫と母猫で異なる猫種が指定されています。MVPでは同一猫種または猫種未指定で推定してください。"
            )
        return sire.breed or dam.breed

    def _observed_candidate_signatures(
        self,
        kitten: ObservedKitten,
        breed: str | None,
    ) -> list[tuple[frozenset[str], tuple[str, tuple[tuple[str, tuple[str, str]], ...]]]]:
        candidates = self._calculator.parent_genotype_candidates(
            kitten.color,
            kitten.sex,
            breed,
            include_unconfirmed_carriers=True,
        )
        ignore_loci = self._ignored_loci_for_observed(kitten.color)
        return [
            (
                frozenset(ignore_loci),
                self._signature(
                    KittenGenotype(
                        sex="Male" if candidate.sex == "male" else "Female",
                        loci=candidate.loci,
                    ),
                    ignore_loci,
                ),
            )
            for candidate in candidates
        ]

    @staticmethod
    def _can_explain_observed(
        generated: list[KittenGenotype],
        observed_signatures: list[
            tuple[frozenset[str], tuple[str, tuple[tuple[str, tuple[str, str]], ...]]]
        ],
    ) -> bool:
        generated_signatures_by_ignored_loci: dict[
            frozenset[str],
            set[tuple[str, tuple[tuple[str, tuple[str, str]], ...]]],
        ] = {}
        for ignored_loci, observed_signature in observed_signatures:
            if ignored_loci not in generated_signatures_by_ignored_loci:
                generated_signatures_by_ignored_loci[ignored_loci] = {
                    LitterInferenceService._signature(kitten, set(ignored_loci))
                    for kitten in generated
                }
            if observed_signature in generated_signatures_by_ignored_loci[ignored_loci]:
                return True
        return False

    @staticmethod
    def _signature(
        kitten: KittenGenotype,
        ignore_loci: set[str],
    ) -> tuple[str, tuple[tuple[str, tuple[str, str]], ...]]:
        return (
            kitten.sex,
            tuple(
                sorted(
                    (
                        locus,
                        tuple(sorted(alleles)),
                    )
                    for locus, alleles in kitten.loci.items()
                    if locus not in ignore_loci
                )
            ),
        )

    @staticmethod
    def _ignored_loci_for_observed(color: str) -> set[str]:
        ignored = {"Mc", "Ta", "Sp"}
        color_lower = color.lower()
        if "calico" in color_lower:
            ignored.add("S")
        return ignored

    def _findings(
        self,
        surviving_pairs: list[tuple[ParentGenotype, ParentGenotype]],
    ) -> tuple[
        list[InferenceFinding],
        list[InferenceFinding],
        list[InferenceFinding],
        list[InferenceFinding],
    ]:
        confirmed: list[InferenceFinding] = []
        conditional: list[InferenceFinding] = []
        inferred: list[InferenceFinding] = []
        unconfirmed: list[InferenceFinding] = []
        total = len(surviving_pairs)

        for role in ("sire", "dam"):
            parent_index = 0 if role == "sire" else 1
            parent_label = _PARENT_LABELS[role]
            for locus in _LOCUS_ORDER:
                genotypes = [
                    self._format_genotype(pair[parent_index].loci[locus], locus)
                    for pair in surviving_pairs
                ]
                counts = Counter(genotypes)
                if len(counts) == 1:
                    genotype = genotypes[0]
                    confirmed.append(
                        InferenceFinding(
                            category="確定",
                            parent=parent_label,
                            locus=f"{locus}座位",
                            genotype=genotype,
                            note="観察された全子猫を説明できる親候補で共通しています。",
                            support_pct=100.0,
                        )
                    )
                    if locus == "O" and role == "dam" and genotype == "XO/XO":
                        inferred.append(
                            InferenceFinding(
                                category="推定",
                                parent=parent_label,
                                locus="O座位",
                                genotype=genotype,
                                note="非レッド父との子猫実績から、母猫が全子にOを渡す説明が強く支持されます。",
                                support_pct=100.0,
                            )
                        )
                    continue

                conditional_finding = self._conditional_finding(
                    surviving_pairs,
                    role,
                    locus,
                    parent_label,
                    total,
                )
                if conditional_finding is not None:
                    conditional.append(conditional_finding)
                    continue

                most_common = counts.most_common(1)[0]
                support = round(most_common[1] / total * 100, 2)
                note = "候補が複数残るため、追加確認なしでは絞り込めません。"
                if locus == "B":
                    note = "チョコレート/シナモンの隠れキャリア有無は、このリター実績だけでは未確認です。"
                unconfirmed.append(
                    InferenceFinding(
                        category="未確認",
                        parent=parent_label,
                        locus=f"{locus}座位",
                        genotype=" / ".join(sorted(counts.keys())),
                        note=note,
                        support_pct=support,
                    )
                )
        return confirmed, conditional, inferred, unconfirmed

    @staticmethod
    def _conditional_finding(
        surviving_pairs: list[tuple[ParentGenotype, ParentGenotype]],
        role: ParentRole,
        locus: str,
        parent_label: str,
        total: int,
    ) -> InferenceFinding | None:
        parent_index = 0 if role == "sire" else 1
        if locus == "A" and all("A" in pair[parent_index].loci["A"] for pair in surviving_pairs):
            return InferenceFinding(
                category="条件付き確定",
                parent=parent_label,
                locus="A座位",
                genotype="A/-",
                note="タビー系子猫を説明するにはAを渡せる必要があります。Red/Cream系では見た目だけの判定に注意してください。",
                support_pct=round(100.0 if total else 0.0, 2),
            )
        return None

    @staticmethod
    def _warnings(kittens: list[ObservedKitten]) -> list[str]:
        warnings: list[str] = []
        if any(_is_red_or_cream(kitten.color) for kitten in kittens):
            warnings.append(
                "Red / Cream 系はA座位の見た目判定が難しいため、タビー/ソリッド判定は参考扱いです。"
            )
        if any("calico" in kitten.color.lower() for kitten in kittens):
            warnings.append(
                "Calico / Dilute Calico は白斑を含む呼称として扱われる場合があります。S座位と白斑有無を写真・登録名で確認してください。"
            )
        return warnings

    @staticmethod
    def _recommended_tests(
        conditional: list[InferenceFinding],
        unconfirmed: list[InferenceFinding],
        warnings: list[str],
    ) -> list[str]:
        loci = {finding.locus.replace("座位", "") for finding in [*conditional, *unconfirmed]}
        tests = [_TEST_LABELS[locus] for locus in _LOCUS_ORDER if locus in loci and locus in _TEST_LABELS]
        if any("白斑" in warning for warning in warnings):
            tests.append(_TEST_LABELS["S"])
        return list(dict.fromkeys(tests))

    @staticmethod
    def _format_genotype(alleles: tuple[str, str], locus: str) -> str:
        if locus == "O":
            if "Y" in alleles:
                allele = "O" if "O" in alleles else "o"
                return f"X{allele}/Y"
            ordered_o = sorted(alleles, key=lambda allele: 0 if allele == "O" else 1)
            return "/".join(f"X{allele}" for allele in ordered_o)
        order = _ALLELE_ORDER.get(locus, {})
        ordered = sorted(alleles, key=lambda allele: order.get(allele, 99))
        return "/".join(_format_allele(allele) for allele in ordered)


def _format_allele(allele: str) -> str:
    if allele == "bl":
        return "b^l"
    return allele


def _is_red_or_cream(color: str) -> bool:
    color_lower = color.lower()
    return "red" in color_lower or "cream" in color_lower
