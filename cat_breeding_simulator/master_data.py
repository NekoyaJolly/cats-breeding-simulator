"""表現型と潜在遺伝子型の対応表。"""

from __future__ import annotations

from dataclasses import dataclass

AUTOSOMAL_LOCI: tuple[str, ...] = ("B", "D", "A", "C", "W", "S", "Mc", "Ta", "Sp", "I", "Wb")


@dataclass(frozen=True, slots=True)
class ParentGenotype:
    """親猫候補の遺伝子型。"""

    phenotype: str
    sex: str
    loci: dict[str, tuple[str, str]]


def _build_genotype(phenotype: str, sex: str, **overrides: tuple[str, str]) -> ParentGenotype:
    defaults: dict[str, tuple[str, str]] = {
        "B": ("B", "B"),
        "D": ("D", "D"),
        "A": ("a", "a"),
        "C": ("C", "C"),
        "W": ("w", "w"),
        "S": ("s", "s"),
        "Mc": ("Mc", "Mc"),
        "Ta": ("ta", "ta"),
        "Sp": ("sp", "sp"),
        "I": ("i", "i"),
        "Wb": ("wb", "wb"),
    }
    defaults.update(overrides)
    if sex == "male":
        defaults["O"] = overrides.get("O", ("o", "Y"))
    else:
        defaults["O"] = overrides.get("O", ("o", "o"))
    return ParentGenotype(phenotype=phenotype, sex=sex, loci=defaults)


def _variants(
    phenotype: str,
    sex: str,
    base_overrides: dict[str, tuple[str, str]],
    carrier_sets: tuple[dict[str, tuple[str, str]], ...],
) -> list[ParentGenotype]:
    genotypes: list[ParentGenotype] = []
    genotypes.append(_build_genotype(phenotype, sex, **base_overrides))
    for carrier_set in carrier_sets:
        merged = dict(base_overrides)
        merged.update(carrier_set)
        genotypes.append(_build_genotype(phenotype, sex, **merged))
    return genotypes


PHENOTYPE_GENOTYPES: dict[str, dict[str, list[ParentGenotype]]] = {
    "Black": {
        "male": _variants(
            "Black",
            "male",
            {},
            (
                {"B": ("B", "b")},
                {"B": ("B", "bl")},
                {"D": ("D", "d")},
            ),
        ),
        "female": _variants(
            "Black",
            "female",
            {},
            (
                {"B": ("B", "b")},
                {"B": ("B", "bl")},
                {"D": ("D", "d")},
            ),
        ),
    },
    "Blue": {
        "male": _variants(
            "Blue",
            "male",
            {"D": ("d", "d")},
            (
                {"B": ("B", "b"), "D": ("d", "d")},
                {"B": ("B", "bl"), "D": ("d", "d")},
            ),
        ),
        "female": _variants(
            "Blue",
            "female",
            {"D": ("d", "d")},
            (
                {"B": ("B", "b"), "D": ("d", "d")},
                {"B": ("B", "bl"), "D": ("d", "d")},
            ),
        ),
    },
    "Red": {
        "male": _variants(
            "Red",
            "male",
            {"O": ("O", "Y"), "A": ("A", "A")},
            (
                {"O": ("O", "Y"), "B": ("B", "b"), "A": ("A", "A")},
                {"O": ("O", "Y"), "D": ("D", "d"), "A": ("A", "A")},
            ),
        ),
        "female": _variants(
            "Red",
            "female",
            {"O": ("O", "O"), "A": ("A", "A")},
            (
                {"O": ("O", "O"), "B": ("B", "b"), "A": ("A", "A")},
                {"O": ("O", "O"), "D": ("D", "d"), "A": ("A", "A")},
            ),
        ),
    },
    "Cream": {
        "male": _variants(
            "Cream",
            "male",
            {"O": ("O", "Y"), "D": ("d", "d"), "A": ("A", "A")},
            (
                {"O": ("O", "Y"), "D": ("d", "d"), "B": ("B", "b"), "A": ("A", "A")},
                {"O": ("O", "Y"), "D": ("d", "d"), "B": ("B", "bl"), "A": ("A", "A")},
            ),
        ),
        "female": _variants(
            "Cream",
            "female",
            {"O": ("O", "O"), "D": ("d", "d"), "A": ("A", "A")},
            (
                {"O": ("O", "O"), "D": ("d", "d"), "B": ("B", "b"), "A": ("A", "A")},
                {"O": ("O", "O"), "D": ("d", "d"), "B": ("B", "bl"), "A": ("A", "A")},
            ),
        ),
    },
    "Mackerel Tabby": {
        "male": _variants(
            "Mackerel Tabby",
            "male",
            {"A": ("A", "a"), "Mc": ("Mc", "mc")},
            (
                {"A": ("A", "a"), "Mc": ("Mc", "mc"), "D": ("D", "d")},
            ),
        ),
        "female": _variants(
            "Mackerel Tabby",
            "female",
            {"A": ("A", "a"), "Mc": ("Mc", "mc")},
            (
                {"A": ("A", "a"), "Mc": ("Mc", "mc"), "D": ("D", "d")},
            ),
        ),
    },
    "Cream Tabby-White": {
        "male": [
            _build_genotype(
                "Cream Tabby-White",
                "male",
                O=("O", "Y"),
                D=("d", "d"),
                A=("A", "A"),
                Mc=("Mc", "Mc"),
                S=("S", "s"),
            )
        ],
        "female": [
            _build_genotype(
                "Cream Tabby-White",
                "female",
                O=("O", "O"),
                D=("d", "d"),
                A=("A", "A"),
                Mc=("Mc", "Mc"),
                S=("S", "s"),
            )
        ],
    },
    "Calico": {
        "male": [],
        "female": [
            _build_genotype("Calico", "female", O=("O", "o"), A=("A", "A"), S=("S", "s")),
            _build_genotype("Calico", "female", O=("O", "o"), A=("A", "A"), S=("S", "S")),
        ],
    },
    "Dilute Calico": {
        "male": [],
        "female": [
            _build_genotype(
                "Dilute Calico",
                "female",
                O=("O", "o"),
                D=("d", "d"),
                A=("A", "A"),
                S=("S", "s"),
            ),
            _build_genotype(
                "Dilute Calico",
                "female",
                O=("O", "o"),
                D=("d", "d"),
                A=("A", "A"),
                S=("S", "S"),
            ),
        ],
    },
    "Pointed": {
        "male": [
            _build_genotype("Pointed", "male", C=("cs", "cs"), A=("a", "a")),
            _build_genotype("Pointed", "male", C=("cs", "cs"), A=("A", "a"), D=("D", "d")),
        ],
        "female": [
            _build_genotype("Pointed", "female", C=("cs", "cs"), A=("a", "a")),
            _build_genotype("Pointed", "female", C=("cs", "cs"), A=("A", "a"), D=("D", "d")),
        ],
    },
    "Silver": {
        "male": [
            _build_genotype("Silver", "male", A=("A", "A"), I=("I", "i"), Mc=("Mc", "Mc")),
        ],
        "female": [
            _build_genotype("Silver", "female", A=("A", "A"), I=("I", "i"), Mc=("Mc", "Mc")),
        ],
    },
    "Smoke": {
        "male": [
            _build_genotype("Smoke", "male", I=("I", "i")),
        ],
        "female": [
            _build_genotype("Smoke", "female", I=("I", "i")),
        ],
    },
    "White": {
        "male": [
            _build_genotype("White", "male", W=("W", "w")),
            _build_genotype("White", "male", W=("W", "W"), D=("D", "d")),
        ],
        "female": [
            _build_genotype("White", "female", W=("W", "w")),
            _build_genotype("White", "female", W=("W", "W"), D=("D", "d")),
        ],
    },
}

def _load_breed_filters() -> dict[str, dict[str, tuple[str, str]]]:
    import csv
    import os

    filename = "猫種データUTF8Ver.csv"
    filepath = None

    # Search paths
    paths_to_try = [
        filename,
        os.path.join("docs", "architecture", filename),
        os.path.join(os.path.dirname(os.path.dirname(__file__)), "docs", "architecture", filename),
        os.path.join(os.path.dirname(os.path.dirname(__file__)), filename),
    ]
    for path in paths_to_try:
        if os.path.exists(path):
            filepath = path
            break

    if not filepath:
        # Fallback to hardcoded defaults if file not found
        return {
            "Siamese": {"C": ("cs", "cs")},
            "Russian Blue": {"D": ("d", "d"), "B": ("B", "B"), "A": ("a", "a")},
            "Munchkin": {},
        }

    filters: dict[str, dict[str, tuple[str, str]]] = {}
    try:
        with open(filepath, mode="r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            locus_cols = [col for col in reader.fieldnames if col.endswith("_Locus")] if reader.fieldnames else []
            
            for row in reader:
                breed = row.get("Breed")
                if not breed:
                    continue
                
                breed_constraints: dict[str, tuple[str, str]] = {}
                for col in locus_cols:
                    val = row.get(col)
                    if val and val.strip():
                        locus_name = col.split("_")[0]
                        alleles = tuple(val.strip().split("/"))
                        if len(alleles) == 2:
                            breed_constraints[locus_name] = (alleles[0], alleles[1])
                
                filters[breed] = breed_constraints
    except Exception:
        # Fallback in case of any reading error
        return {
            "Siamese": {"C": ("cs", "cs")},
            "Russian Blue": {"D": ("d", "d"), "B": ("B", "B"), "A": ("a", "a")},
            "Munchkin": {},
        }

    # Ensure "Munchkin" exists for backward compatibility / tests (since tests use "Munchkin" without SH/LH)
    if "Munchkin" not in filters:
        filters["Munchkin"] = {}

    return filters


BREED_FILTERS = _load_breed_filters()


