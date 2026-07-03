"""毛色確率計算エンジン本体。"""

from __future__ import annotations

from collections import OrderedDict, defaultdict
from dataclasses import dataclass, replace
import itertools
from typing import TypeVar

from cat_breeding_simulator.mendelian import (
    allele_distribution,
    o_locus_gamete_distribution,
)
from cat_breeding_simulator.master_data import (
    AUTOSOMAL_LOCI,
    BREED_FILTERS,
    COLOR_BASE_LOCI,
    breed_color_group_label,
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
from cat_breeding_simulator.color_master import COLOR_MASTER, breed_context_matches
from cat_breeding_simulator.phenotype_naming import PhenotypeNamer


ProbabilityMap = dict[tuple[str, str], float]

# AOC (Any Other Color): White 親の「下の色」が未確定なため、生後の毛色で判明する集約カテゴリ。
# 実在の毛色ではないため canonical 正規化・表示名解決 (display_alias_map) の対象に含めない
# (V9 §2.4 / 指示書 §2.3・§7)。順方向の色行とは別扱いで最後段に付与する。
_AOC_COLOR = "AOC"

_TONKINESE_BREED_KEY = "Tonkinese"
_TONKINESE_POINT_CLASS_COLORS: frozenset[str] = frozenset(
    {"Natural Point", "Blue Point", "Champagne Point", "Platinum Point"}
)
_TONKINESE_SOLID_CLASS_COLORS: frozenset[str] = frozenset(
    {"Natural Solid", "Blue Solid", "Champagne Solid", "Platinum Solid"}
)


def _genotype_key(loci: dict[str, tuple[str, str]]) -> tuple:
    """遺伝子型をアレル単位でそのまま表すキー (デバッグ・未分類サンプル記録用)。"""

    parts = []
    for locus in sorted(loci.keys()):
        a1, a2 = loci[locus]
        parts.append((locus, tuple(sorted([a1, a2]))))
    return tuple(parts)


def _tonkinese_c_locus_for_color(color: str) -> tuple[str, str] | None:
    """Tonkinese の Point/Mink/Solid class から C座位を返す。"""

    if color in _TONKINESE_POINT_CLASS_COLORS:
        return ("cs", "cs")
    if "Mink" in color:
        return ("cb", "cs")
    if color in _TONKINESE_SOLID_CLASS_COLORS:
        return ("cb", "cb")
    return None


def _apply_tonkinese_c_class(
    color: str,
    genotypes: list[ParentGenotype],
) -> list[ParentGenotype]:
    """Tonkinese 文脈では色名クラスを C座位の正本として親候補へ反映する。"""

    required = _tonkinese_c_locus_for_color(color)
    if required is None:
        return []

    adjusted: list[ParentGenotype] = []
    seen: set[tuple] = set()
    for genotype in genotypes:
        loci = dict(genotype.loci)
        loci["C"] = required
        signature = _genotype_key(loci)
        if signature in seen:
            continue
        seen.add(signature)
        adjusted.append(replace(genotype, loci=loci))
    return adjusted


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

# O 座位 (X 連鎖): 親が非オレンジ (O を持たない) のに、相手親が「全ての子に O を渡す」場合の
# ブロッカー。全子に O が渡るのは相手が O/O メス (赤メス) のときだけ。赤オス (O/Y) は息子に Y を
# 渡すため、非オレンジ親 (o) との間に非オレンジの息子 (o/Y) が出るのでブロッカーにならない。
_O_NON_ORANGE_LABEL = "非オレンジ（赤以外） o"

# O 座位 (X 連鎖) の対称ケース: 親が純オレンジ (O を持ち o を持たない = Red/Cream) なのに、相手親が
# 「全ての子に o を渡す」場合のブロッカー。全子に o が渡るのは相手が o/o メス (非オレンジメス) のとき
# だけ。このとき息子は o/Y (非オレンジ)、娘は O/o (トーティ) になり純オレンジは子に出ない。非オレンジ
# オス (o/Y) は息子に Y を渡すため息子 O/Y (オレンジ) が出る → ブロッカーにならない (other_sex で限定)。
_O_ORANGE_LABEL = "オレンジ（赤/クリーム） O"


# プロセス内キャッシュの上限 (常駐 singleton のメモリ無制限増加を防ぐ)。
# 入力上限 (猫50 / 子猫12) に加え、(色 × 猫種 × mode × carrier) の組み合わせ爆発に対しても
# 常駐メモリを有界にする。超過時は最も使われていないエントリ (LRU) から退避する。
_REPORT_CACHE_MAX = 2048
_GENOTYPE_CACHE_MAX = 2048
_GAMETE_CACHE_MAX = 4096

_CacheValue = TypeVar("_CacheValue")


def _lru_get(
    cache: "OrderedDict[tuple, _CacheValue]", key: tuple
) -> _CacheValue | None:
    """LRUキャッシュから取得し、ヒットしたキーを最近使用へ更新する。"""

    if key not in cache:
        return None
    cache.move_to_end(key)
    return cache[key]


def _lru_put(
    cache: "OrderedDict[tuple, _CacheValue]", key: tuple, value: _CacheValue, maxsize: int
) -> None:
    """LRUキャッシュへ格納し、上限超過時は最古エントリを退避する。"""

    cache[key] = value
    cache.move_to_end(key)
    if len(cache) > maxsize:
        cache.popitem(last=False)


def _freeze_carriers(carriers: dict[str, str] | None) -> tuple[tuple[str, str], ...] | None:
    """キャリア指定 (dict) をキャッシュキー用にハッシュ可能なタプルへ正規化する。"""

    if not carriers:
        return None
    return tuple(sorted(carriers.items()))


def _gamete_cache_key(genotype: ParentGenotype) -> tuple:
    """配偶子生成は座位アレル対の順序に依存しない (分離は集合的) ため、
    順序非依存のキーで同一遺伝子型をまとめる。"""

    return (
        genotype.sex,
        tuple(sorted((locus, tuple(sorted(pair))) for locus, pair in genotype.loci.items())),
    )


class CoatColorCalculator:
    """Split -> Cross -> Evaluate -> Aggregate を実装する計算器。"""

    def __init__(self) -> None:
        # 遺伝子型 → 表示色名 の命名/分類は PhenotypeNamer へ委譲する。
        self._namer = PhenotypeNamer()
        # 純粋計算のプロセス内メモ化 (入力 + import時定数のみに依存)。
        # 逆引き/リター推定は同一 (色, 性別, 猫種) の解決やレポートを多数回要求するため、
        # ここでキャッシュすると O(N^2) 経路の定数項が大きく下がる。
        # 上限付き LRU で常駐メモリを有界化する (_lru_get / _lru_put)。
        # calculate_report は外部に露出するため、キャッシュ汚染防止に「返却時コピー」する
        # (_copy_report)。内部専用の genotype / gamete キャッシュは読み取り専用契約とする。
        self._report_cache: "OrderedDict[tuple, CalculationReport]" = OrderedDict()
        self._genotype_cache: "OrderedDict[tuple, list[ParentGenotype]]" = OrderedDict()
        self._gamete_cache: "OrderedDict[tuple, dict[tuple[tuple[str, str], ...], float]]" = OrderedDict()

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
        """純粋関数 `_calculate_report_impl` の結果をプロセス内メモ化して返す。

        逆引き (オス×メス総当たり) や carrier_exploration / リター推定が同一の親色組を
        繰り返し計算するため、(色, 猫種, モード, キャリア) をキーにキャッシュする。
        例外 (BreedingCalculationError) はキャッシュせずそのまま送出する。
        """

        key = (
            sire_color,
            dam_color,
            breed,
            mode,
            _freeze_carriers(sire_carriers),
            _freeze_carriers(dam_carriers),
        )
        cached = _lru_get(self._report_cache, key)
        if cached is not None:
            # 同一 singleton が横断的に共有するため、キャッシュ実体を直接渡さずコピーを返す
            # (呼び出し側の偶発的な破壊的変更でキャッシュが汚染されるのを防ぐ)。
            return self._copy_report(cached)
        report = self._calculate_report_impl(
            sire_color, dam_color, breed, mode, sire_carriers, dam_carriers
        )
        _lru_put(self._report_cache, key, report, _REPORT_CACHE_MAX)
        return self._copy_report(report)

    @staticmethod
    def _copy_report(report: CalculationReport) -> CalculationReport:
        """キャッシュ実体を保護するため、可変コレクションを浅くコピーした新レポートを返す。

        要素 (KittenResult / CarrierScenario / ParentColorNote) は frozen dataclass のため、
        リスト/辞書を作り直せば呼び出し側の append/pop/要素差し替えからキャッシュを守れる。
        """

        return replace(
            report,
            results=list(report.results),
            unmatched_samples=[dict(sample) for sample in report.unmatched_samples],
            opened_loci=list(report.opened_loci) if report.opened_loci is not None else None,
            closed_loci=list(report.closed_loci) if report.closed_loci is not None else None,
            assumptions=list(report.assumptions) if report.assumptions is not None else None,
            carrier_exploration_results=(
                list(report.carrier_exploration_results)
                if report.carrier_exploration_results is not None
                else None
            ),
            parent_color_notes=(
                list(report.parent_color_notes) if report.parent_color_notes is not None else None
            ),
        )

    def _calculate_report_impl(
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

        # White (優性白・下不明) が親に含まれる通常モードは、下の色が不定なため
        # 遺伝子型総当たりでは「White 100%」や誤った色になる。W/w を仮定した専用集計で
        # 白の割合・母由来で確定できる色を出し、確定できない残りは AOC に集約する (§2.1/§2.2)。
        # 明示キャリア (explicit_carrier) は「下の色が入力された」ケースなので従来の正確計算に回す。
        if mode == "normal" and not sire_carriers and not dam_carriers:
            sire_white = self._is_white_phenotype(sire_color, breed)
            dam_white = self._is_white_phenotype(dam_color, breed)
            if sire_white or dam_white:
                return self._calculate_white_report(
                    sire_color, dam_color, breed, sire_white, dam_white
                )

        sire_genotypes = self._resolve_parent_genotypes(
            sire_color, "male", breed, mode, sire_carriers
        )
        dam_genotypes = self._resolve_parent_genotypes(
            dam_color, "female", breed, mode, dam_carriers
        )

        if not sire_genotypes:
            raise BreedingCalculationError(
                "この交配では父猫の有効な遺伝子型が残りませんでした。毛色と猫種の組み合わせをご確認ください。"
            )
        if not dam_genotypes:
            raise BreedingCalculationError(
                "この交配では母猫の有効な遺伝子型が残りませんでした。毛色と猫種の組み合わせをご確認ください。"
            )

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
                        phenotype = self._namer.classify_phenotype(
                            kitten, sire_color, dam_color, breed
                        )
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

    # --- White (優性白・下不明) 順方向の専用集計 (§2.1 / §2.2) ---
    #
    # W/W か W/w かは表現型から区別できないが、順方向表示では「有色の子が出得る」ことを
    # 見せるため White 親を W/w と仮定する (§2.1/§2.2 の割合はこの仮定に基づく)。
    # 白の割合・母由来で確定できる色を出し、確定できない残り (父の X が O=赤だった場合や、
    # White 母の下の色が全不明の場合) は AOC (Any Other Color) に集約する。

    def _is_white_phenotype(self, color: str, breed: str | None) -> bool:
        """入力色が優性白 (White) に解決されるか。解決不能・例外時は False。"""

        try:
            resolved = self._resolve_input_color_name(color, breed)
        except BreedingCalculationError:
            return False
        return self._normalize_color_key(resolved) == "White"

    def _calculate_white_report(
        self,
        sire_color: str,
        dam_color: str,
        breed: str | None,
        sire_white: bool,
        dam_white: bool,
    ) -> CalculationReport:
        """White 親を含む通常モードの結果を、W/w 仮定 + AOC 集約で構築する。"""

        # 両親を通常経路で検証する (無効な毛色・性別制約・猫種非認定はここで送出)。
        self._resolve_parent_genotypes(sire_color, "male", breed, "normal")
        self._resolve_parent_genotypes(dam_color, "female", breed, "normal")

        if sire_white and dam_white:
            # 両親 White (W/w × W/w): 白 3/4 (M/F 各 37.5%)、有色 1/4 は両親とも下不明 → AOC。
            results = [
                KittenResult(sex="Male", color="White", probability_pct=37.5),
                KittenResult(sex="Female", color="White", probability_pct=37.5),
                KittenResult(sex="Male", color=_AOC_COLOR, probability_pct=12.5),
                KittenResult(sex="Female", color=_AOC_COLOR, probability_pct=12.5),
            ]
            assumption = (
                "両親とも White (優性白) のため W/w × W/w を仮定。白 75%、有色 25% は"
                "両親の下の色が不明なため AOC (Any Other Color) に集約。"
            )
        elif sire_white:
            results = self._white_parent_results("sire", dam_color, breed)
            assumption = (
                "父が White (優性白) のため W/w を仮定。オスは母由来で色が確定、"
                "メスは White(下不明)父の X を受け継ぐため色が定まらず AOC に集約 (§2.1)。"
            )
        else:
            results = self._white_parent_results("dam", sire_color, breed)
            assumption = (
                "母が White (優性白) のため W/w を仮定。母の下の色が全不明のため、"
                "有色の子はオス・メスとも AOC (Any Other Color) に集約 (§2.2)。"
            )

        assumptions = [
            "W (優性白): 表現型からは W/W・W/w を区別できないため W/w を仮定 (X/- 展開)",
            assumption,
            "AOC: 白親の下の色が未確定な有色カテゴリ。生後の毛色で判明する集約表示",
        ]
        return CalculationReport(
            results=results,
            matched_probability=1.0,
            unmatched_probability=0.0,
            unmatched_genotype_count=0,
            unmatched_samples=[],
            mode="normal",
            opened_loci=["W", *NORMAL_OPENED_LOCI],
            closed_loci=list(NORMAL_CLOSED_LOCI),
            assumptions=assumptions,
            parent_color_notes=None,
        )

    def _white_parent_results(
        self, white_side: str, other_color: str, breed: str | None
    ) -> list[KittenResult]:
        """片親のみ White のときの結果行を構築する (§2.1 父White / §2.2 母White)。"""

        other_display = self.display_color_name(other_color, breed)
        # W/w 由来: 白 50% (オス/メス各 25%)。残り 50% が有色。
        results = [
            KittenResult(sex="Male", color="White", probability_pct=25.0),
            KittenResult(sex="Female", color="White", probability_pct=25.0),
        ]
        if white_side == "sire":
            # 父 White (§2.1): オスは母由来で色が確定 → 母の色 (25%)。オスは母の X(O座位) と
            # 母の優性形質で色が決まり、父 (White) の下地は乗らない扱い。
            # メスは父 (White・下不明) の X を受け継ぐため、その下地アレル (O=赤の可能性や、
            # 母が劣性ホモの座位で父の優性が乗るか等) が定まらず、色を確定できない → AOC (25%)。
            # 母の色が♀限定 (トーティ等) の場合はオスに出せないため、オス有色も AOC に落とす。
            male_colored = _AOC_COLOR if self._namer.is_female_only_color(other_display) else other_display
            results.append(KittenResult(sex="Male", color=male_colored, probability_pct=25.0))
            results.append(KittenResult(sex="Female", color=_AOC_COLOR, probability_pct=25.0))
        else:
            # 母 White (§2.2): 母の下 (O座位・常染色体とも) が不明 → 有色はオス・メスとも AOC。
            results.append(KittenResult(sex="Male", color=_AOC_COLOR, probability_pct=25.0))
            results.append(KittenResult(sex="Female", color=_AOC_COLOR, probability_pct=25.0))
        return results

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

        return self.contributable_alleles(color, sex, breed, "normal", None)

    def contributable_alleles(
        self,
        color: str,
        sex: str,
        breed: str | None,
        mode: str = "normal",
        carriers: dict[str, str] | None = None,
    ) -> dict[str, set[str]]:
        """指定条件の親が子へ渡し得るアレル集合を座位別に返す。

        逆引きでは「確定で渡せる」「未確認条件が必要」を座位別に説明するため、
        CSV代表値ではなく mode 展開後の親候補を基準に集計する。
        """

        try:
            genotypes = self._resolve_parent_genotypes(color, sex, breed, mode, carriers)
        except BreedingCalculationError:
            return {}
        alleles: dict[str, set[str]] = {}
        for genotype in genotypes:
            for locus, pair in genotype.loci.items():
                alleles.setdefault(locus, set()).update(pair)
        return alleles

    def resolved_base_loci(
        self, color: str, sex: str, breed: str | None
    ) -> dict[str, tuple[str, str]] | None:
        """入力色の基準遺伝子型を返す。逆引きの座位別根拠表示に使う。"""

        return self._resolved_base_loci(color, sex, breed)

    def resolved_color_loci(
        self, color: str, sex: str, breed: str | None
    ) -> dict[str, tuple[str, str]] | None:
        """入力色をO座位込みの基準遺伝子型へ解決する。"""

        name = self._resolve_input_color_name(color, breed)
        key = self._normalize_color_key(name)
        entries = COLOR_BASE_LOCI.get(key)
        if not entries:
            return None
        loci = dict(entries[0].autosomal)
        if sex == "male":
            if "O" in entries[0].o and "o" in entries[0].o:
                return None
            loci["O"] = ("O", "Y") if "O" in entries[0].o else ("o", "Y")
        else:
            loci["O"] = entries[0].o
        return loci

    def display_color_name(self, color: str, breed: str | None) -> str:
        """入力色を計算結果と同じ表示名正規化へ通す。"""

        resolved = self._resolve_input_color_name(color, breed)
        return self._namer.post_process_color_name(resolved, color, color, breed)

    @staticmethod
    def _validate_resolved_sex_restriction(color: str, sex: str) -> None:
        resolved = COLOR_MASTER.resolve(color)
        if resolved is None:
            return
        if sex == "male" and resolved.sex_restriction == "female_only":
            raise BreedingCalculationError(
                f"「{resolved.primary_name}」はメス限定の毛色のため、父猫（オス）には指定できません。"
            )
        if sex == "female" and resolved.sex_restriction == "male_only":
            raise BreedingCalculationError(
                f"「{resolved.primary_name}」はオス限定の毛色のため、母猫（メス）には指定できません。"
            )

    def validate_parent_color(
        self,
        color: str,
        sex: str,
        breed: str | None,
        mode: str = "normal",
        carriers: dict[str, str] | None = None,
    ) -> None:
        """親猫入力として有効かを、通常計算と同じ名前解決・性別制約で検証する。"""

        self._validate_resolved_sex_restriction(color, sex)
        self._resolve_parent_genotypes(color, sex, breed, mode, carriers)

    def parent_genotype_candidates(
        self,
        color: str,
        sex: str,
        breed: str | None,
        mode: str = "normal",
        carriers: dict[str, str] | None = None,
        include_unconfirmed_carriers: bool = False,
    ) -> list[ParentGenotype]:
        """親または観察子猫の表現型から整合し得る遺伝子型候補を返す。

        通常シミュレーターと同じ resolver / alias 解決を先に通し、リター推定だけが必要とする
        未確認キャリア候補は追加展開として重ねる。色名解決経路を別系統にしないための公開面。
        """

        self._validate_resolved_sex_restriction(color, sex)
        genotypes = self._resolve_parent_genotypes(color, sex, breed, mode, carriers)
        if not include_unconfirmed_carriers:
            return genotypes
        return self._expand_unconfirmed_loci(genotypes)

    def possible_kitten_genotypes(
        self,
        sire_genotype: ParentGenotype,
        dam_genotype: ParentGenotype,
    ) -> list[KittenGenotype]:
        """指定した父母遺伝子型候補から生まれ得る子猫遺伝子型を重複なく返す。"""

        kittens: list[KittenGenotype] = []
        seen: set[tuple] = set()
        sire_gametes = self._build_gametes(sire_genotype)
        dam_gametes = self._build_gametes(dam_genotype)
        for sire_gamete in sire_gametes:
            for dam_gamete in dam_gametes:
                kitten = self._combine_gametes(sire_gamete, dam_gamete)
                signature = (
                    kitten.sex,
                    tuple(
                        sorted(
                            (locus, tuple(sorted(alleles)))
                            for locus, alleles in kitten.loci.items()
                        )
                    ),
                )
                if signature in seen:
                    continue
                seen.add(signature)
                kittens.append(kitten)
        return kittens

    @staticmethod
    def _expand_unconfirmed_loci(genotypes: list[ParentGenotype]) -> list[ParentGenotype]:
        """産子実績から推定するため、表現型だけでは閉じていた主要キャリア座位を候補化する。"""

        expanded: list[ParentGenotype] = []
        seen: set[tuple] = set()
        for genotype in genotypes:
            locus_options: dict[str, list[tuple[str, str]]] = {}
            for locus, alleles in genotype.loci.items():
                locus_options[locus] = [alleles]

            b_alleles = genotype.loci["B"]
            if b_alleles == ("B", "B"):
                locus_options["B"] = [("B", "B"), ("B", "b"), ("B", "bl")]
            elif b_alleles == ("b", "b"):
                locus_options["B"] = [("b", "b"), ("b", "bl")]

            a_alleles = genotype.loci["A"]
            if a_alleles == ("A", "A"):
                locus_options["A"] = [("A", "A"), ("A", "a")]

            c_alleles = genotype.loci["C"]
            if c_alleles == ("C", "C"):
                locus_options["C"] = [("C", "C"), ("C", "cs"), ("C", "cb")]

            loci = list(locus_options.keys())
            options = [locus_options[locus] for locus in loci]
            for combination in itertools.product(*options):
                next_loci = dict(zip(loci, combination))
                signature = (
                    genotype.sex,
                    tuple(
                        sorted(
                            (locus, tuple(sorted(next_loci[locus])))
                            for locus in next_loci
                        )
                    ),
                )
                if signature in seen:
                    continue
                seen.add(signature)
                expanded.append(
                    ParentGenotype(
                        phenotype=genotype.phenotype,
                        sex=genotype.sex,
                        loci=next_loci,
                    )
                )
        return expanded

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

        # O 座位 (X 連鎖): 親が非オレンジ (O を持たない) のに、相手が「全ての子に O を渡す」
        # = 相手が O/O メス (赤メス) で o を渡せない場合のみブロッカー。赤オス (O/Y) は息子に
        # Y を渡すため非オレンジの息子 (o/Y) が出る → ブロックしない (other_sex で限定する)。
        self_o = self_alleles.get("O", set())
        if (
            self_o
            and "O" not in self_o
            and other_sex == "female"
            and "o" not in other_alleles.get("O", set())
        ):
            factors.append(_O_NON_ORANGE_LABEL)

        # O 座位 (X 連鎖) の対称ケース: 親が純オレンジ (O を持ち o を持たない) のに、相手が
        # 「全ての子に o を渡す」= 相手が o/o メス (非オレンジメス) で O を渡せない場合のみ
        # ブロッカー。息子 o/Y (非オレンジ) / 娘 O/o (トーティ) になり純オレンジは子に出ない。
        # 非オレンジオス (o/Y) は息子に Y を渡すため息子 O/Y (オレンジ) が出る → ブロックしない。
        # トーティ親 (O も o も持つ) は "o" not in self_o で自然に除外される。
        if (
            self_o
            and "O" in self_o
            and "o" not in self_o
            and other_sex == "female"
            and "O" not in other_alleles.get("O", set())
        ):
            factors.append(_O_ORANGE_LABEL)

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
        """親遺伝子型候補の解決をメモ化して返す (返り値は読み取り専用扱い)。"""

        key = (phenotype, sex, breed, mode, _freeze_carriers(carriers))
        cached = _lru_get(self._genotype_cache, key)
        if cached is not None:
            return cached
        result = self._resolve_parent_genotypes_impl(phenotype, sex, breed, mode, carriers)
        _lru_put(self._genotype_cache, key, result, _GENOTYPE_CACHE_MAX)
        return result

    def _resolve_parent_genotypes_impl(
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
            raise BreedingCalculationError(
                f"「{phenotype}」は対応していない毛色です。候補から選んでください。"
            )

        # mode に応じた親遺伝子型候補を生成する (normal: キャリア閉鎖 / explicit_carrier: 指定座位を開放)。
        genotypes = build_parent_genotypes(phenotype_key, sex, mode, carriers)
        if not genotypes:
            if sex == "male":
                raise BreedingCalculationError(
                    f"「{phenotype_key}」はメス限定の毛色のため、父猫（オス）には指定できません。"
                )
            raise BreedingCalculationError(
                f"「{phenotype_key}」はオス限定の毛色のため、母猫（メス）には指定できません。"
            )

        if not breed:
            return genotypes

        breed_key = self._normalize_breed_key(breed)
        if breed_key == _TONKINESE_BREED_KEY:
            genotypes = _apply_tonkinese_c_class(phenotype_key, genotypes)
            if not genotypes:
                raise BreedingCalculationError(
                    f"「{phenotype_key}」は「{breed}」の認定カラー"
                    "（Point/Mink/Solid class）にありません。"
                    f"{breed} の認定カラーを選ぶか、猫種の指定を外してください。"
                )
        breed_constraints = BREED_FILTERS.get(breed_key, {})
        filtered: list[ParentGenotype] = []
        for genotype in genotypes:
            if all(self._matches_exact(genotype.loci[locus], required) for locus, required in breed_constraints.items() if locus in genotype.loci):
                filtered.append(genotype)
        # 猫種制約で候補が全滅した = その毛色は猫種の認定カラーに無い。曖昧な「遺伝子型が残らない」
        # ではなく、矛盾相手 (毛色) と猫種を名指しして案内する。
        if not filtered and breed_constraints:
            group = breed_color_group_label(breed_key)
            group_part = f"（{group}）" if group else ""
            raise BreedingCalculationError(
                f"「{phenotype_key}」は「{breed}」の認定カラー{group_part}にありません。"
                f"{breed} の認定カラーを選ぶか、猫種の指定を外してください。"
            )
        return filtered

    def _build_gametes(self, genotype: ParentGenotype) -> dict[tuple[tuple[str, str], ...], float]:
        """配偶子分布をメモ化して返す (同一遺伝子型が交配の各所で何度も使われる)。"""

        key = _gamete_cache_key(genotype)
        cached = _lru_get(self._gamete_cache, key)
        if cached is not None:
            return cached
        result = self._build_gametes_impl(genotype)
        _lru_put(self._gamete_cache, key, result, _GAMETE_CACHE_MAX)
        return result

    def _build_gametes_impl(self, genotype: ParentGenotype) -> dict[tuple[tuple[str, str], ...], float]:
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
        return {allele: float(probability) for allele, probability in allele_distribution(alleles).items()}

    @staticmethod
    def _orange_gametes(genotype: ParentGenotype) -> dict[str, float]:
        sex = "male" if genotype.sex == "male" else "female"
        return {
            allele: float(probability)
            for allele, probability in o_locus_gamete_distribution(sex, genotype.loci["O"]).items()
        }


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
                    f"「{name}」は通常の計算では入力できない色区分です。別の毛色を選んでください。"
                )
            if resolved.status == "breed_specific":
                if not breed:
                    raise BreedingCalculationError(
                        f"「{name}」は「{resolved.breed_context}」固有の毛色です。"
                        f"この毛色を使うには猫種に「{resolved.breed_context}」を指定してください"
                        "（猫種の指定は任意ですが、固有色を使う場合は必要です）。"
                    )
                if not breed_context_matches(breed, resolved.breed_context):
                    raise BreedingCalculationError(
                        f"「{name}」は「{resolved.breed_context}」固有の毛色です。"
                        f"「{breed}」の毛色としては指定できません。"
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
