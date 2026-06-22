"""毛色確率計算エンジン本体。"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from cat_breeding_simulator.master_data import AUTOSOMAL_LOCI, BREED_FILTERS, PHENOTYPE_GENOTYPES, ParentGenotype


ProbabilityMap = dict[tuple[str, str], float]


@dataclass(frozen=True, slots=True)
class KittenResult:
    """API返却用の集計結果。"""

    sex: str
    color: str
    probability_pct: float


@dataclass(frozen=True, slots=True)
class KittenGenotype:
    """子猫1個体の遺伝子型。"""

    sex: str
    loci: dict[str, tuple[str, str]]


class BreedingCalculationError(ValueError):
    """入力や計算前提の不整合。"""


class CoatColorCalculator:
    """Split -> Cross -> Evaluate -> Aggregate を実装する計算器。"""

    def calculate(self, sire_color: str, dam_color: str, breed: str | None = None) -> list[KittenResult]:
        sire_genotypes = self._resolve_parent_genotypes(sire_color, "male", breed)
        dam_genotypes = self._resolve_parent_genotypes(dam_color, "female", breed)

        if not sire_genotypes:
            raise BreedingCalculationError("No valid sire genotypes remain after filtering.")
        if not dam_genotypes:
            raise BreedingCalculationError("No valid dam genotypes remain after filtering.")

        aggregate: ProbabilityMap = defaultdict(float)
        pair_weight = 1.0 / (len(sire_genotypes) * len(dam_genotypes))

        for sire_genotype in sire_genotypes:
            sire_gametes = self._build_gametes(sire_genotype)
            for dam_genotype in dam_genotypes:
                dam_gametes = self._build_gametes(dam_genotype)
                for sire_gamete, sire_probability in sire_gametes.items():
                    for dam_gamete, dam_probability in dam_gametes.items():
                        kitten = self._combine_gametes(sire_gamete, dam_gamete)
                        phenotype = self._classify_phenotype(kitten)
                        aggregate[(kitten.sex, phenotype)] += sire_probability * dam_probability * pair_weight

        return self._to_results(aggregate)

    def _resolve_parent_genotypes(self, phenotype: str, sex: str, breed: str | None) -> list[ParentGenotype]:
        phenotype_key = self._normalize_color_key(phenotype)
        phenotype_options = PHENOTYPE_GENOTYPES.get(phenotype_key)
        if phenotype_options is None:
            supported = ", ".join(sorted(PHENOTYPE_GENOTYPES))
            raise BreedingCalculationError(f"Unsupported color '{phenotype}'. Supported colors: {supported}")

        genotypes = list(phenotype_options[sex])
        if not genotypes:
            raise BreedingCalculationError(f"Color '{phenotype_key}' is not valid for a {sex}.")

        if not breed:
            return genotypes

        breed_key = self._normalize_breed_key(breed)
        breed_constraints = BREED_FILTERS.get(breed_key, {})
        filtered: list[ParentGenotype] = []
        for genotype in genotypes:
            if all(self._matches_exact(genotype.loci[locus], required) for locus, required in breed_constraints.items()):
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

    def _classify_phenotype(self, kitten: KittenGenotype) -> str:
        if self._has_dominant(kitten.loci["W"], "W"):
            return "White"

        if self._is_homozygous(kitten.loci["C"], "c"):
            return "Albino"

        orange_state = self._orange_state(kitten)
        restriction = self._point_restriction(kitten.loci["C"])
        white_spotting = kitten.loci["S"]
        dilute = self._is_homozygous(kitten.loci["D"], "d")
        patterned = self._has_dominant(kitten.loci["A"], "A") or orange_state in {"orange", "tortoiseshell"}
        pattern = self._tabby_pattern(kitten) if patterned and orange_state != "tortoiseshell" else ""

        if orange_state == "tortoiseshell":
            if self._has_dominant(white_spotting, "S"):
                if dilute:
                    return "Dilute Calico"
                return "Calico"
            phenotype = "Dilute Tortoiseshell" if dilute else "Tortoiseshell"
            if restriction:
                phenotype = f"{phenotype} {restriction}"
            return phenotype

        if orange_state == "orange":
            base_color = "Cream" if dilute else "Red"
        else:
            base_color = self._black_series_color(kitten.loci["B"], dilute)

        phenotype = base_color
        if pattern:
            phenotype = f"{phenotype} {pattern}"
        if restriction:
            phenotype = f"{phenotype} {restriction}"

        phenotype = self._apply_modifiers(phenotype, kitten, patterned=bool(pattern))
        phenotype = self._apply_white_spotting(phenotype, white_spotting)
        return phenotype

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
            return f"{phenotype} Van"
        if "Tabby" in phenotype or "Point" in phenotype:
            return f"{phenotype}-White"
        return f"{phenotype} Bi-Color"

    def _black_series_color(self, alleles: tuple[str, str], dilute: bool) -> str:
        if "B" in alleles:
            return "Blue" if dilute else "Black"
        if "b" in alleles:
            return "Lilac" if dilute else "Chocolate"
        return "Fawn" if dilute else "Cinnamon"

    def _point_restriction(self, alleles: tuple[str, str]) -> str:
        normalized = frozenset(alleles)
        if normalized == frozenset({"cs"}):
            return "Siamese Point"
        if normalized == frozenset({"cb"}):
            return "Burmese Sepia"
        if normalized == frozenset({"cb", "cs"}):
            return "Tonkinese Mink"
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

    def _to_results(self, aggregate: ProbabilityMap) -> list[KittenResult]:
        total = sum(aggregate.values())
        sorted_results = sorted(aggregate.items(), key=lambda item: (-item[1], item[0][0], item[0][1]))
        return [
            KittenResult(sex=sex, color=color, probability_pct=round(probability / total * 100, 4))
            for (sex, color), probability in sorted_results
        ]

    @staticmethod
    def _matches_exact(actual: tuple[str, str], required: tuple[str, str]) -> bool:
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
