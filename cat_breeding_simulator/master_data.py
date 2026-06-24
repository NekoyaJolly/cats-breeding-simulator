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


def _build_normal_parent_genotypes(phenotype: str, sex: str, base_loci: dict[str, tuple[str, str]]) -> list[ParentGenotype]:
    """通常モード用の親遺伝子型候補を構築する。

    「優性表現型のヘテロ未確定ルール (Dominant Expressed Unknown Rule)」に従う。
    優性形質が表現されている座は、表現型だけからホモ接合と断定できないため
    X/- = {X/X, X/x} の両方を計算対象に含める。

    - カテゴリA (表現型確定・優性ヘテロ不確定 / 通常モードでも展開する):
        D 濃色 -> D/-, I シルバー -> I/-, Mc マッカレル -> Mc/-, Ta ティックド -> Ta/-。
    - カテゴリA' (タビーの A-locus / 通常モードでは展開しない):
        A タビーは normal_mode では A/A 相当として扱い A/a を展開しない。
        理由: A/a を展開すると a/a×a/a が成立し、タビー親から Solid / Tortie /
        Calico / Smoke (いずれも a/a 前提) が出てしまう。これは表現型から要求されない
        潜在キャリアの自動展開であり通常モードでは禁止する。A/a は明示キャリア
        (explicit_carrier_mode) または全キャリア探索 (carrier_exploration_mode) でのみ使う。
    - カテゴリB (表現型確定・劣性固定 / 固定する):
        d/d, a/a, cs/cs, cb/cb, cb/cs, i/i, s/s など。CSVの劣性ホモはそのまま固定。
    - カテゴリC (表現型から要求されない潜在キャリア / 通常モードでは展開しない):
        B/b チョコ, B/bl シナモン, C/cs ポイント, C/cb セピア。
        明示キャリア情報または血統・産子履歴がある場合のみ explicit_carrier で扱う。

    シミュレーター正本 V9 §2.4 に準拠 (A の非展開は本ルールの改訂)。
    """

    import itertools

    defaults = {
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
    full_loci = dict(defaults)
    full_loci.update(base_loci)

    # カテゴリA: 優性ホモで記載されている座に、ヘテロ (優性/劣性) の可能性を加える。
    #
    # A (タビー) は除外する。normal_mode では A を A/A 相当に固定し A/a を展開しない。
    #   A/a を展開すると a/a×a/a が成立し、タビー親から Solid / Tortie / Calico / Smoke
    #   (a/a 前提) が出てしまうため。A/a は explicit_carrier / carrier_exploration でのみ扱う。
    # S (白斑) は除外する。白斑は不完全優性で S/S(Van) と S/s(バイカラー/-White) は
    # 表現型で区別でき、入力の白斑レベルから接合性が確定する (= ヘテロ不可視ではない)。
    # さらに S/S の Van 色を S/s へ展開すると逆引きMAPが汚染され、S/s の子が Van 名へ
    # 誤マッチするため、S は CSV 記載値のまま固定する。
    dominant_expandable: dict[str, tuple[str, str]] = {
        "D": ("D", "d"),
        "I": ("I", "i"),
        "Mc": ("Mc", "mc"),
        "Ta": ("Ta", "ta"),
        "Wb": ("Wb", "wb"),
    }

    loci_options: dict[str, list[tuple[str, str]]] = {}
    for locus, val in full_loci.items():
        options = [val]
        hetero = dominant_expandable.get(locus)
        # 優性形質が「優性ホモ」で表現されている場合のみ X/- としてヘテロを追加する。
        # 劣性ホモ (カテゴリB) や B/C (カテゴリC) はここで展開しない。
        if hetero is not None and val == (hetero[0], hetero[0]):
            options.append(hetero)
        loci_options[locus] = options

    keys = list(loci_options.keys())
    values_list = [loci_options[key] for key in keys]

    genotypes: list[ParentGenotype] = []
    for combination in itertools.product(*values_list):
        loci = dict(zip(keys, combination))
        genotypes.append(ParentGenotype(phenotype=phenotype, sex=sex, loci=loci))
    return genotypes


def _load_phenotype_genotypes() -> dict[str, dict[str, list[ParentGenotype]]]:
    import csv
    import os

    results = {
        "Black": {
            "male": _variants("Black", "male", {}, ({"B": ("B", "b")}, {"B": ("B", "bl")}, {"D": ("D", "d")})),
            "female": _variants("Black", "female", {}, ({"B": ("B", "b")}, {"B": ("B", "bl")}, {"D": ("D", "d")})),
        },
        "Blue": {
            "male": _variants("Blue", "male", {"D": ("d", "d")}, ({"B": ("B", "b"), "D": ("d", "d")}, {"B": ("B", "bl"), "D": ("d", "d")})),
            "female": _variants("Blue", "female", {"D": ("d", "d")}, ({"B": ("B", "b"), "D": ("d", "d")}, {"B": ("B", "bl"), "D": ("d", "d")})),
        },
        "Red": {
            "male": _variants("Red", "male", {"O": ("O", "Y"), "A": ("A", "A")}, ({"O": ("O", "Y"), "B": ("B", "b"), "A": ("A", "A")}, {"O": ("O", "Y"), "D": ("D", "d"), "A": ("A", "A")})),
            "female": _variants("Red", "female", {"O": ("O", "O"), "A": ("A", "A")}, ({"O": ("O", "O"), "B": ("B", "b"), "A": ("A", "A")}, {"O": ("O", "O"), "D": ("D", "d"), "A": ("A", "A")})),
        },
        "Cream": {
            "male": _variants("Cream", "male", {"O": ("O", "Y"), "D": ("d", "d"), "A": ("A", "A")}, ({"O": ("O", "Y"), "D": ("d", "d"), "B": ("B", "b"), "A": ("A", "A")}, {"O": ("O", "Y"), "D": ("d", "d"), "B": ("B", "bl"), "A": ("A", "A")})),
            "female": _variants("Cream", "female", {"O": ("O", "O"), "D": ("d", "d"), "A": ("A", "A")}, ({"O": ("O", "O"), "D": ("d", "d"), "B": ("B", "b"), "A": ("A", "A")}, {"O": ("O", "O"), "D": ("d", "d"), "B": ("B", "bl"), "A": ("A", "A")})),
        },
        "Mackerel Tabby": {
            "male": _variants("Mackerel Tabby", "male", {"A": ("A", "a"), "Mc": ("Mc", "mc")}, ({"A": ("A", "a"), "Mc": ("Mc", "mc"), "D": ("D", "d")},)),
            "female": _variants("Mackerel Tabby", "female", {"A": ("A", "a"), "Mc": ("Mc", "mc")}, ({"A": ("A", "a"), "Mc": ("Mc", "mc"), "D": ("D", "d")},)),
        },
        "Cream Tabby-White": {
            "male": [_build_genotype("Cream Tabby-White", "male", O=("O", "Y"), D=("d", "d"), A=("A", "A"), Mc=("Mc", "Mc"), S=("S", "s"))],
            "female": [_build_genotype("Cream Tabby-White", "female", O=("O", "O"), D=("d", "d"), A=("A", "A"), Mc=("Mc", "Mc"), S=("S", "s"))],
        },
        "Calico": {
            "male": [],
            "female": [_build_genotype("Calico", "female", O=("O", "o"), A=("A", "A"), S=("S", "s")), _build_genotype("Calico", "female", O=("O", "o"), A=("A", "A"), S=("S", "S"))],
        },
        "Dilute Calico": {
            "male": [],
            "female": [_build_genotype("Dilute Calico", "female", O=("O", "o"), D=("d", "d"), A=("A", "A"), S=("S", "s")), _build_genotype("Dilute Calico", "female", O=("O", "o"), D=("d", "d"), A=("A", "A"), S=("S", "S"))],
        },
        "Pointed": {
            "male": [_build_genotype("Pointed", "male", C=("cs", "cs"), A=("a", "a")), _build_genotype("Pointed", "male", C=("cs", "cs"), A=("A", "a"), D=("D", "d"))],
            "female": [_build_genotype("Pointed", "female", C=("cs", "cs"), A=("a", "a")), _build_genotype("Pointed", "female", C=("cs", "cs"), A=("A", "a"), D=("D", "d"))],
        },
        "Silver": {
            "male": [_build_genotype("Silver", "male", A=("A", "A"), I=("I", "i"), Mc=("Mc", "Mc"))],
            "female": [_build_genotype("Silver", "female", A=("A", "A"), I=("I", "i"), Mc=("Mc", "Mc"))],
        },
        "Smoke": {
            "male": [_build_genotype("Smoke", "male", I=("I", "i"))],
            "female": [_build_genotype("Smoke", "female", I=("I", "i"))],
        },
        "White": {
            "male": [_build_genotype("White", "male", W=("W", "w")), _build_genotype("White", "male", W=("W", "W"), D=("D", "d"))],
            "female": [_build_genotype("White", "female", W=("W", "w")), _build_genotype("White", "female", W=("W", "W"), D=("D", "d"))],
        },
    }

    filename = "cat_color_genetic_map.csv"
    filepath = None

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
        return results

    results = {}
    try:
        with open(filepath, mode="r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            locus_cols = [col for col in reader.fieldnames if col.endswith("_Locus")] if reader.fieldnames else []
            
            for row in reader:
                color = row.get("CoatColor")
                if not color:
                    continue
                
                # Determine B locus from name
                color_lower = color.lower()
                if "chocolate" in color_lower or "lilac" in color_lower or "choco" in color_lower:
                    b_allele = ("b", "b")
                elif "cinnamon" in color_lower or "fawn" in color_lower:
                    b_allele = ("bl", "bl")
                else:
                    b_allele = ("B", "B")
                
                base_loci = {"B": b_allele}
                
                for col in locus_cols:
                    val = row.get(col)
                    if val and val.strip():
                        locus_name = col.split("_")[0]
                        if locus_name == "O":
                            continue
                        alleles = tuple(val.strip().split("/"))
                        if len(alleles) == 2:
                            base_loci[locus_name] = (alleles[0], alleles[1])
                
                # O Locus parsing
                o_val = row.get("O_Locus", "o/o")
                o_alleles = tuple(o_val.strip().split("/")) if o_val else ("o", "o")
                if len(o_alleles) != 2:
                    o_alleles = ("o", "o")
                
                # Build Male Genotypes
                male_loci = dict(base_loci)
                if o_alleles == ("O", "o"):
                    male_variants = []
                else:
                    male_o_allele = "O" if "O" in o_alleles else "o"
                    male_loci["O"] = (male_o_allele, "Y")
                    male_variants = _build_normal_parent_genotypes(color, "male", male_loci)
                    
                # Build Female Genotypes
                female_loci = dict(base_loci)
                female_loci["O"] = o_alleles
                female_variants = _build_normal_parent_genotypes(color, "female", female_loci)
                
                if color not in results:
                    results[color] = {"male": [], "female": []}
                
                results[color]["male"].extend(male_variants)
                results[color]["female"].extend(female_variants)
                
    except Exception:
        pass
        
    return results


PHENOTYPE_GENOTYPES = _load_phenotype_genotypes()


def _load_color_definitions() -> list[dict[str, str]]:
    import csv
    import os

    filename = "cat_color_genetic_map.csv"
    filepath = None

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
        return []

    definitions = []
    try:
        with open(filepath, mode="r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get("CoatColor"):
                    definitions.append(dict(row))
    except Exception:
        pass
    return definitions


COLOR_DEFINITIONS = _load_color_definitions()


def _load_breed_filters() -> dict[str, dict[str, tuple[str, str]]]:
    import csv
    import os

    filename = "cat_breed_genetic_map.csv"
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


