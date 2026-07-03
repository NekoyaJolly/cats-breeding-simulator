"""リター実績から両親の隠れ因子を推定するMVPロジック。"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Literal

from cat_breeding_simulator.engine import BreedingCalculationError, CoatColorCalculator
from cat_breeding_simulator.master_data import (
    BREED_FILTERS,
    ParentGenotype,
    _breed_allele_matches,
    white_underlying_locus_options,
)


ObservedSex = Literal["male", "female"]
ParentRole = Literal["sire", "dam"]

# 観察子猫1候補のプロファイル: (性別, {座位: ソート済みアレル対})。無視座位は含めない。
ObservedProfile = tuple[str, dict[str, tuple[str, str]]]


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
class _LocusAnalysis:
    """White 親を含むリターの、1座位ぶんの座位別逆算結果。

    proj は「観察子猫を全頭説明できる」親側の値の射影、full はその親の全取り得る値、
    representative は全頭に整合する代表 (父値, 母値)、pair_count はこの座位の生存ペア数。
    """

    sire_proj: list[tuple[str, str]]
    dam_proj: list[tuple[str, str]]
    sire_full: list[tuple[str, str]]
    dam_full: list[tuple[str, str]]
    representative: tuple[tuple[str, str], tuple[str, str]]
    pair_count: int


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


# W (優性白) を含める。White 親から色付きの子が出た実績は「親が w を渡せる＝W/w」を確定でき、
# これが White 親逆算の要 (§3 R2a/R2b)。W は B より前に置き、白か有色かの土台を先に示す。
_LOCUS_ORDER: tuple[str, ...] = ("W", "B", "D", "A", "O", "C", "I", "S", "Wb")
_PARENT_LABELS: dict[ParentRole, str] = {"sire": "父猫", "dam": "母猫"}
_TEST_LABELS: dict[str, str] = {
    "A": "A座位（アグーティ/ソリッド）の表現確認または産子履歴確認",
    "B": "B座位（チョコレート/シナモン）の遺伝子検査",
    "C": "C座位（ポイント/セピア）の遺伝子検査",
    "D": "D座位（ダイリュート）の遺伝子検査",
    "I": "I座位（シルバー/スモーク）の確認",
    "S": "S座位（白斑）の確認",
    "W": "W座位（優性白）の確認",
    "Wb": "ゴールデン修飾・ワイドバンドの確認",
}
_ALLELE_ORDER: dict[str, dict[str, int]] = {
    "B": {"B": 0, "b": 1, "bl": 2},
    "D": {"D": 0, "d": 1},
    "A": {"A": 0, "a": 1},
    "C": {"C": 0, "cb": 1, "cs": 2},
    "I": {"I": 0, "i": 1},
    "S": {"S": 0, "s": 1},
    "W": {"W": 0, "w": 1},
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
        observed_kittens = [
            self._observed_kitten_profiles(kitten, breed) for kitten in kittens
        ]

        # White (優性白) 親は下の色が表現型で見えないため、下地を全列挙してフィルタする代わりに、
        # 観察子猫が拘束する座位だけを座位別に逆算する (§3 / Nekoさん指摘: 見えない色は推定不要)。
        sire_white = self._calculator._is_white_phenotype(sire.color, breed)
        dam_white = self._calculator._is_white_phenotype(dam.color, breed)
        if sire_white or dam_white:
            return self._infer_with_white_parent(
                sire, dam, breed, kittens, observed_kittens, sire_white, dam_white
            )

        sire_candidates = self._parent_candidates(sire.color, "male", breed)
        dam_candidates = self._parent_candidates(dam.color, "female", breed)

        surviving_pairs = self._surviving_pairs(
            sire_candidates, dam_candidates, observed_kittens
        )

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

    def _parent_candidates(
        self, color: str, sex: str, breed: str | None
    ) -> list[ParentGenotype]:
        """非 White 親の遺伝子型候補を返す (resolver + 未確認キャリア展開)。

        White 親は下地が表現型で見えないため本経路では扱わない。White を含むリターは
        `_infer_with_white_parent` が座位別に逆算する (全下地の列挙を避ける)。
        """

        return self._calculator.parent_genotype_candidates(
            color,
            sex,
            breed,
            include_unconfirmed_carriers=True,
        )

    # --- White (優性白) 親を含むリターの座位別逆算 (§3 / 全下地列挙を避ける) ---
    #
    # 優性白は下の色を表現型で隠すため、下地の各座位は原理的に不定。観察子猫の色が拘束する
    # 座位だけを座位ごとに逆算し、拘束されない下地は「下不明」と明示するだけにする
    # (見えていない色は推定しない)。メンデル分離は座位独立なので、親ペアを全列挙せず
    # 座位別に (父値, 母値) の生存ペアを求め、その射影から親ごとの推定を出す。

    def _infer_with_white_parent(
        self,
        sire: LitterParent,
        dam: LitterParent,
        breed: str | None,
        kittens: list[ObservedKitten],
        observed_kittens: list[list[ObservedProfile]],
        sire_white: bool,
        dam_white: bool,
    ) -> LitterInferenceReport:
        warnings = self._warnings(kittens)
        # 観察できない子猫が1頭でもあれば、どの親ペアも全頭説明できない。
        if any(not profiles for profiles in observed_kittens):
            return self._white_contradiction_report(warnings)

        analysis = self._white_locus_analysis(
            sire, dam, breed, sire_white, dam_white, observed_kittens
        )
        if analysis is None:
            return self._white_contradiction_report(warnings)

        confirmed, conditional, inferred, unconfirmed, white_unknown = self._white_findings(
            analysis, sire_white, dam_white
        )
        for role in ("sire", "dam"):
            loci = white_unknown[role]
            if loci:
                names = "・".join(f"{locus}座位" for locus in loci)
                warnings.append(
                    f"{_PARENT_LABELS[role]}は優性白のため、観察された子猫からは下の色（下地）を"
                    f"推定できません（下不明）: {names}"
                )
        recommended_tests = self._recommended_tests(conditional, unconfirmed, warnings)
        pair_count = 1
        for info in analysis.values():
            pair_count *= info.pair_count
        return LitterInferenceReport(
            response_category="推定可能",
            candidate_pair_count=pair_count,
            confirmed=confirmed,
            conditional=conditional,
            inferred=inferred,
            unconfirmed=unconfirmed,
            contradictions=[],
            warnings=warnings,
            recommended_tests=recommended_tests,
        )

    @staticmethod
    def _white_contradiction_report(warnings: list[str]) -> LitterInferenceReport:
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

    def _white_locus_analysis(
        self,
        sire: LitterParent,
        dam: LitterParent,
        breed: str | None,
        sire_white: bool,
        dam_white: bool,
        observed_kittens: list[list[ObservedProfile]],
    ) -> dict[str, _LocusAnalysis] | None:
        """座位ごとに (父値, 母値) の生存ペアを求め、親別の射影・代表・件数を返す。

        いずれかの座位で観察子猫を説明できる (父値, 母値) が無ければ矛盾として None を返す。
        """

        sire_options = self._locus_options_for_parent(sire.color, "male", breed, sire_white)
        dam_options = self._locus_options_for_parent(dam.color, "female", breed, dam_white)

        analysis: dict[str, _LocusAnalysis] = {}
        for locus in _LOCUS_ORDER:
            if locus not in sire_options or locus not in dam_options:
                continue
            sire_opts = sire_options[locus]
            dam_opts = dam_options[locus]
            # この座位を拘束する子猫の要求 (性別, 許容アレル対集合) を集める。
            kitten_reqs: list[tuple[str, set[tuple[str, str]]]] = []
            for profiles in observed_kittens:
                sex = profiles[0][0]
                acceptable = {
                    profile[1][locus] for profile in profiles if locus in profile[1]
                }
                if acceptable:
                    kitten_reqs.append((sex, acceptable))

            if not kitten_reqs:
                # どの子猫もこの座位を拘束しない → 全ペアが生存 (下不明)。
                sire_proj = list(sire_opts)
                dam_proj = list(dam_opts)
                representative = (sire_opts[0], dam_opts[0])
                pair_count = len(sire_opts) * len(dam_opts)
            else:
                pairs = [
                    (sire_value, dam_value)
                    for sire_value in sire_opts
                    for dam_value in dam_opts
                    if all(
                        any(
                            _pair_produces_locus(locus, sire_value, dam_value, sex, target)
                            for target in acceptable
                        )
                        for sex, acceptable in kitten_reqs
                    )
                ]
                if not pairs:
                    return None  # この座位で全頭を説明できる親値が無い = 矛盾
                sire_proj = list(dict.fromkeys(sire_value for sire_value, _ in pairs))
                dam_proj = list(dict.fromkeys(dam_value for _, dam_value in pairs))
                representative = pairs[0]
                pair_count = len(pairs)

            analysis[locus] = _LocusAnalysis(
                sire_proj=sire_proj,
                dam_proj=dam_proj,
                sire_full=list(sire_opts),
                dam_full=list(dam_opts),
                representative=representative,
                pair_count=pair_count,
            )
        return analysis

    def _white_findings(
        self,
        analysis: dict[str, _LocusAnalysis],
        sire_white: bool,
        dam_white: bool,
    ) -> tuple[
        list[InferenceFinding],
        list[InferenceFinding],
        list[InferenceFinding],
        list[InferenceFinding],
        dict[str, list[str]],
    ]:
        confirmed: list[InferenceFinding] = []
        conditional: list[InferenceFinding] = []
        inferred: list[InferenceFinding] = []
        unconfirmed: list[InferenceFinding] = []
        white_unknown: dict[str, list[str]] = {"sire": [], "dam": []}

        for role in ("sire", "dam"):
            is_white = sire_white if role == "sire" else dam_white
            label = _PARENT_LABELS[role]
            for locus in _LOCUS_ORDER:
                info = analysis.get(locus)
                if info is None:
                    continue
                projection = info.sire_proj if role == "sire" else info.dam_proj
                full = info.sire_full if role == "sire" else info.dam_full

                if len(projection) == 1:
                    genotype = self._format_genotype(projection[0], locus)
                    confirmed.append(
                        InferenceFinding(
                            category="確定",
                            parent=label,
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
                                parent=label,
                                locus="O座位",
                                genotype=genotype,
                                note="非レッド父との子猫実績から、母猫が全子にOを渡す説明が強く支持されます。",
                                support_pct=100.0,
                            )
                        )
                    continue

                # White 親の座位が全対立のまま残る = このリターから拘束できない下地 → 下不明。
                if is_white and set(projection) == set(full):
                    white_unknown[role].append(locus)
                    continue

                if locus == "A" and all("A" in pair for pair in projection):
                    conditional.append(
                        InferenceFinding(
                            category="条件付き確定",
                            parent=label,
                            locus="A座位",
                            genotype="A/-",
                            note="タビー系子猫を説明するにはAを渡せる必要があります。Red/Cream系では見た目だけの判定に注意してください。",
                            support_pct=100.0,
                        )
                    )
                    continue

                genotypes = " / ".join(
                    sorted(self._format_genotype(pair, locus) for pair in projection)
                )
                note = "候補が複数残るため、追加確認なしでは絞り込めません。"
                if locus == "B":
                    note = "チョコレート/シナモンの隠れキャリア有無は、このリター実績だけでは未確認です。"
                unconfirmed.append(
                    InferenceFinding(
                        category="未確認",
                        parent=label,
                        locus=f"{locus}座位",
                        genotype=genotypes,
                        note=note,
                        support_pct=round(100.0 / len(projection), 2),
                    )
                )
        return confirmed, conditional, inferred, unconfirmed, white_unknown

    def _locus_options_for_parent(
        self, color: str, sex: str, breed: str | None, is_white: bool
    ) -> dict[str, list[tuple[str, str]]]:
        """親の座位別・取り得るアレル対集合を返す。White は下地全対立、非 White は候補から射影。"""

        if is_white:
            options = {
                locus: [_norm_locus_pair(locus, pair) for pair in values]
                for locus, values in white_underlying_locus_options(sex).items()
            }
            if breed:
                constraints = BREED_FILTERS.get(
                    CoatColorCalculator._normalize_breed_key(breed), {}
                )
                for locus, required in constraints.items():
                    if locus not in options:
                        continue
                    filtered = [
                        pair for pair in options[locus] if _breed_allele_matches(pair, required)
                    ]
                    if filtered:
                        options[locus] = filtered
            return options

        candidates = self._parent_candidates(color, sex, breed)
        options: dict[str, list[tuple[str, str]]] = {}
        for candidate in candidates:
            for locus, pair in candidate.loci.items():
                normalized = _norm_locus_pair(locus, pair)
                bucket = options.setdefault(locus, [])
                if normalized not in bucket:
                    bucket.append(normalized)
        return options

    def representative_parents(
        self, sire: LitterParent, dam: LitterParent, kittens: list[ObservedKitten]
    ) -> tuple[ParentGenotype, ParentGenotype] | None:
        """観察子猫を全頭説明できる代表的な父母遺伝子型ペアを返す (往復検証用)。無ければ None。

        White 親は座位別逆算の代表値から組み立てる (全下地列挙をしない)。非 White は
        従来の surviving_pairs から先頭を返す。
        """

        breed = self._shared_breed(sire, dam)
        self._calculator.validate_parent_color(sire.color, "male", breed)
        self._calculator.validate_parent_color(dam.color, "female", breed)
        observed = [self._observed_kitten_profiles(kitten, breed) for kitten in kittens]
        sire_white = self._calculator._is_white_phenotype(sire.color, breed)
        dam_white = self._calculator._is_white_phenotype(dam.color, breed)

        if sire_white or dam_white:
            if any(not profiles for profiles in observed):
                return None
            analysis = self._white_locus_analysis(
                sire, dam, breed, sire_white, dam_white, observed
            )
            if analysis is None:
                return None
            return self._representative_from_analysis(analysis)

        sire_candidates = self._parent_candidates(sire.color, "male", breed)
        dam_candidates = self._parent_candidates(dam.color, "female", breed)
        pairs = self._surviving_pairs(sire_candidates, dam_candidates, observed)
        return pairs[0] if pairs else None

    @staticmethod
    def _representative_from_analysis(
        analysis: dict[str, _LocusAnalysis],
    ) -> tuple[ParentGenotype, ParentGenotype]:
        """座位別逆算の代表値 (各座位で全頭に整合する (父値, 母値)) から親ペアを組み立てる。"""

        sire_loci: dict[str, tuple[str, str]] = {}
        dam_loci: dict[str, tuple[str, str]] = {}
        for locus, info in analysis.items():
            sire_value, dam_value = info.representative
            sire_loci[locus] = sire_value
            dam_loci[locus] = dam_value
        # 照合対象外のパターン座 (Mc/Ta/Sp) は既定値で補う (配偶子生成に全座位が要る)。
        for locus, default in (("Mc", ("Mc", "Mc")), ("Ta", ("ta", "ta")), ("Sp", ("sp", "sp"))):
            sire_loci.setdefault(locus, default)
            dam_loci.setdefault(locus, default)
        return (
            ParentGenotype(phenotype="sire", sex="male", loci=sire_loci),
            ParentGenotype(phenotype="dam", sex="female", loci=dam_loci),
        )

    @staticmethod
    def _shared_breed(sire: LitterParent, dam: LitterParent) -> str | None:
        if sire.breed and dam.breed and sire.breed != dam.breed:
            raise BreedingCalculationError(
                "父猫と母猫で異なる猫種が指定されています。MVPでは同一猫種または猫種未指定で推定してください。"
            )
        return sire.breed or dam.breed

    def _observed_kitten_profiles(
        self,
        kitten: ObservedKitten,
        breed: str | None,
    ) -> list[ObservedProfile]:
        """観察子猫1頭の候補遺伝子型を、無視座位を除いた座位別アレル対へ展開する。

        各候補は (性別, {座位: ソート済みアレル対}) で表す。後段の座位独立判定で、
        親ペアが各座位にこの対を渡せるかを座位ごとに突き合わせる。
        """

        try:
            candidates = self._calculator.parent_genotype_candidates(
                kitten.color,
                kitten.sex,
                breed,
                include_unconfirmed_carriers=True,
            )
        except BreedingCalculationError as error:
            raise BreedingCalculationError(_kitten_error_message(kitten, error)) from error
        ignore_loci = self._ignored_loci_for_observed(kitten.color)
        profiles: list[ObservedProfile] = []
        for candidate in candidates:
            sex = "Male" if candidate.sex == "male" else "Female"
            loci = {
                locus: tuple(sorted(alleles))
                for locus, alleles in candidate.loci.items()
                if locus not in ignore_loci
            }
            profiles.append((sex, loci))
        return profiles

    def _surviving_pairs(
        self,
        sire_candidates: list[ParentGenotype],
        dam_candidates: list[ParentGenotype],
        observed_kittens: list[list[ObservedProfile]],
    ) -> list[tuple[ParentGenotype, ParentGenotype]]:
        """観察された全子猫を同時に説明できる父母候補ペアを残す (座位独立分解)。

        メンデル分離は座位ごとに独立 → 「観察署名 ∈ 親ペアから生成される子猫署名集合」は
        「各座位で観察アレル対が親ペアから生成可能」かつ「性別×O座位が到達可能」へ厳密に分解できる。
        結合 (joint) の子猫遺伝子型集合を物質化する従来実装 (O(候補² × 配偶子直積)) を、
        ビットマスクの座位別照合 (O(候補² × 子猫数 × 座位数)) へ置き換える。出力は同一。
        """

        # 観察できない子猫が1頭でもあれば、どの親ペアも全頭説明できない。
        if any(not profiles for profiles in observed_kittens):
            return []

        # 子猫ごとに「座位集合」「候補数 (=ビット幅)」「(親座位対)→満たす候補ビットマスク」のメモを持つ。
        kitten_tables: list[tuple[list[ObservedProfile], list[str], dict[str, dict[tuple, int]]]] = []
        for profiles in observed_kittens:
            loci_keys = list(profiles[0][1].keys())
            kitten_tables.append((profiles, loci_keys, {locus: {} for locus in loci_keys}))

        surviving: list[tuple[ParentGenotype, ParentGenotype]] = []
        for sire_candidate in sire_candidates:
            sire_loci = sire_candidate.loci
            for dam_candidate in dam_candidates:
                dam_loci = dam_candidate.loci
                if self._pair_explains_all(sire_loci, dam_loci, kitten_tables):
                    surviving.append((sire_candidate, dam_candidate))
        return surviving

    def _pair_explains_all(
        self,
        sire_loci: dict[str, tuple[str, str]],
        dam_loci: dict[str, tuple[str, str]],
        kitten_tables: list[tuple[list[ObservedProfile], list[str], dict[str, dict[tuple, int]]]],
    ) -> bool:
        """この父母ペアが全観察子猫を説明できるか。

        子猫ごとに、全座位で「対を渡せる候補」のビットマスクを AND し、
        1つでも候補が全座位を満たせば (mask != 0) その子猫は説明可能。
        """

        for profiles, loci_keys, table in kitten_tables:
            mask = (1 << len(profiles)) - 1
            for locus in loci_keys:
                key = (sire_loci[locus], dam_loci[locus])
                locus_masks = table[locus]
                locus_mask = locus_masks.get(key)
                if locus_mask is None:
                    locus_mask = _locus_satisfaction_mask(
                        locus, sire_loci[locus], dam_loci[locus], profiles
                    )
                    locus_masks[key] = locus_mask
                mask &= locus_mask
                if mask == 0:
                    break
            if mask == 0:
                return False
        return True

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
                # 生存ペアが多い (White 親は下不明で候補が数万に及ぶ) ため、整形は座位ごとの
                # 「異なるアレル対」だけに絞る。順序非依存キーで数え、代表のみ表示名へ整形する。
                raw_counts: Counter[tuple[str, str]] = Counter(
                    tuple(sorted(pair[parent_index].loci[locus])) for pair in surviving_pairs
                )
                counts: Counter[str] = Counter()
                for raw_pair, raw_count in raw_counts.items():
                    counts[self._format_genotype(raw_pair, locus)] += raw_count
                if len(counts) == 1:
                    genotype = next(iter(counts))
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
        if any(_needs_tortie_white_spotting_warning(kitten.color) for kitten in kittens):
            warnings.append(
                "Calico / Tortie 系は白斑を含む呼称として扱われる場合があります。S座位と白斑有無を写真・登録名で確認してください。"
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


def _autosomal_can_produce(
    sire_pair: tuple[str, str],
    dam_pair: tuple[str, str],
    target_pair: tuple[str, str],
) -> bool:
    """常染色体1座位で、親ペアが子の (ソート済み) アレル対を生成できるか。

    子は片方を父配偶子、もう片方を母配偶子から受け取る。配偶子に出るアレルは
    その座位の対の集合 (ホモなら1種、ヘテロなら2種)。
    """

    first, second = target_pair
    sire_alleles = {sire_pair[0], sire_pair[1]}
    dam_alleles = {dam_pair[0], dam_pair[1]}
    return (first in sire_alleles and second in dam_alleles) or (
        second in sire_alleles and first in dam_alleles
    )


def _o_can_produce(
    sire_o: tuple[str, str],
    dam_o: tuple[str, str],
    target_sex: str,
    target_pair: tuple[str, str],
) -> bool:
    """O座位 (X連鎖) で、性別込みの子 (性別, ソート済みO対) を生成できるか。

    父 (オス) の配偶子は {O または o, Y}、母 (メス) の配偶子は対の非Yアレル。
    Y を受けると子はオス (O対 = (母アレル, Y))、それ以外はメス (O対 = (父アレル, 母アレル))。
    """

    orange = "O" if "O" in sire_o else "o"
    sire_gametes = {orange, "Y"}
    dam_gametes = {dam_o[0], dam_o[1]}
    for sire_gamete in sire_gametes:
        for dam_gamete in dam_gametes:
            if sire_gamete == "Y":
                if target_sex == "Male" and tuple(sorted((dam_gamete, "Y"))) == target_pair:
                    return True
            elif target_sex == "Female" and tuple(sorted((sire_gamete, dam_gamete))) == target_pair:
                return True
    return False


# O 座位のアレル表示順 (O 優性 > o > Y)。順序非依存キー化と全対立比較に使う。
_O_ALLELE_ORDER: dict[str, int] = {"O": 0, "o": 1, "Y": 2}


def _norm_locus_pair(locus: str, pair: tuple[str, str]) -> tuple[str, str]:
    """座位別に正準化したアレル対を返す (集合比較・表示のブレを防ぐ)。

    O 座位は O>o>Y の優性順、他座位はアルファベット順で固定する。
    """

    if locus == "O":
        ordered = sorted(pair, key=lambda allele: _O_ALLELE_ORDER.get(allele, 99))
    else:
        ordered = sorted(pair)
    return (ordered[0], ordered[1])


def _pair_produces_locus(
    locus: str,
    sire_pair: tuple[str, str],
    dam_pair: tuple[str, str],
    target_sex: str,
    target_pair: tuple[str, str],
) -> bool:
    """1座位で、(父値, 母値) が観察子猫の (性別, アレル対) を生成できるか。"""

    if locus == "O":
        return _o_can_produce(sire_pair, dam_pair, target_sex, target_pair)
    return _autosomal_can_produce(sire_pair, dam_pair, target_pair)


def _locus_satisfaction_mask(
    locus: str,
    sire_pair: tuple[str, str],
    dam_pair: tuple[str, str],
    profiles: list[ObservedProfile],
) -> int:
    """この座位で、各候補プロファイルの要求対を親ペアが渡せるかをビットマスクで返す。"""

    mask = 0
    for index, (sex, loci) in enumerate(profiles):
        target_pair = loci[locus]
        if locus == "O":
            satisfied = _o_can_produce(sire_pair, dam_pair, sex, target_pair)
        else:
            satisfied = _autosomal_can_produce(sire_pair, dam_pair, target_pair)
        if satisfied:
            mask |= 1 << index
    return mask


def _format_allele(allele: str) -> str:
    if allele == "bl":
        return "b^l"
    return allele


def _is_red_or_cream(color: str) -> bool:
    color_lower = color.lower()
    return "red" in color_lower or "cream" in color_lower


def _needs_tortie_white_spotting_warning(color: str) -> bool:
    color_lower = color.lower()
    return (
        "calico" in color_lower
        or "tortie" in color_lower
        or "tortoiseshell" in color_lower
    )


def _kitten_error_message(kitten: ObservedKitten, error: BreedingCalculationError) -> str:
    message = str(error)
    message = message.replace("父猫（オス）には指定できません", "オスの子猫には指定できません")
    message = message.replace("母猫（メス）には指定できません", "メスの子猫には指定できません")
    sex_label = "オス" if kitten.sex == "male" else "メス"
    display_name = kitten.name or kitten.id
    return (
        f"子猫「{display_name}」（ID: {kitten.id}、{sex_label}）の観察カラーを確認してください。"
        f"{message}"
    )
