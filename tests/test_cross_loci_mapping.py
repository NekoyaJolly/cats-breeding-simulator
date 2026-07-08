"""特定交配における「遺伝子座→命名出力」の対応正当性テスト (通常モード)。

## 位置づけ (既存テストとの差分)

- `test_mendelian_loci.py`: 座位**単体**のメンデル分離 (`cross_autosomal_locus` 等) を
  分数で検証する低レベルテスト。
- `test_golden_crosses.py`: `/api/v1/calculate` 出力を丸ごと凍結するスナップショット回帰。
- **本ファイル**: 上記2つの中間。実務で多い**複雑な組み合わせ (タビー・白斑・ポイント混合)**
  を厳選し、「確定色 (`confirmed_results`) と推定色 (`conditional_color_groups`) が
  遺伝子座通りに正しく振り分けられているか」「不可逆ルール・カテゴリC非展開に反した色が
  漏れていないか」を oracle として検証する。確率の完全一致 (丸め依存) より、
  座位由来の出力構造の正しさを保証することを主眼とする。

## 各ケースが狙う座位エッジ

| # | 交配 | 検証する座位エッジ |
|---|------|-------------------|
| 1 | Brown Tabby-White × Cream Tabby | A(タビー)+S(白斑)+O連鎖 / D保因=推定Blue系 / A/a=推定ソリッド |
| 2 | Blue Tabby × Cream Tabby-White | ★D座位 d/d×d/d 不可逆: 濃色 (Black/Brown/Red) が一切出ない |
| 3 | Silver Tabby-White × Brown Tabby | I保因=推定 非シルバーBrown / A/a=推定Smoke / D保因=推定Blue Silver |
| 4 | Red Tabby-White × Silver Tabby-White | O(赤父)+I保因+D保因+Tortie Smoke(♀限定)。最も複雑 |
| 5 | Seal Point-White × Red Tabby | ★C座位: ポイントは確定に出ず C_cs 保因時のみ推定(Lynx Point) |
| 6 | Seal Point × Blue Point | C座位 cs/cs 固定: 全個体ポイント / D保因=推定Blue Point |
| 7 | Chocolate Tabby × Brown Tabby | ★B座位 カテゴリC: チョコは確定に出ず B_b 保因時のみ推定 |
| 8 | Black Smoke × Red Tabby | I(スモーク→Cameo)+O連鎖+A/a=推定Tortie Smoke(♀限定) |
| 9 | White × Brown Tabby-White | ★W座位 優性白 epistasis: 有色♀=AOC / 有色♂=母色 (§2.1) |
| 10| Brown Tabby × Calico | O(トーティ母)+S(白斑)+A/a=推定ソリッド / D保因=推定Blue |
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

import pytest

from cat_breeding_simulator.engine import CoatColorCalculator

# オス (XY) には出せないメス限定カラーの語 (X連鎖O座位のヘテロが要るため)。
# 注: "Tortie" は "Tortie Smoke" も巻き込む (いずれもメス限定)。"Tortoiseshell" は
#     "Tortie" を部分文字列に含まないため別途列挙する。"Blue Cream"/"Lilac Cream" は
#     トーティの希釈。素の "Cream" (赤の希釈=オスにも出る) は対象にしない。
FEMALE_ONLY_SUBSTRINGS: frozenset[str] = frozenset(
    {"Tortie", "Tortoiseshell", "Calico", "Blue Cream", "Lilac Cream"}
)

# conditional シナリオ ID の書式。座位_保因型_on_{親} で「どの親がどの潜在保因を持つ想定か」を表す。
SCENARIO_PATTERN = re.compile(r"^[A-Za-z]+_[A-Za-z]+_on_(sire|dam|both)$")


@dataclass(frozen=True)
class LociCase:
    """1交配ぶんの座位→出力 oracle 期待値。

    確率は丸め依存で脆いため厳密固定せず、「どの色が確定/推定/禁止か」という
    座位由来の構造だけを検証対象にする。
    """

    #: 父の毛色 (入力 alias 可)。
    sire: str
    #: 母の毛色 (入力 alias 可)。
    dam: str
    #: 猫種文脈 (無ければ None)。
    breed: str | None
    #: このケースが検証する座位エッジの説明 (日本語)。
    rationale: str
    #: `confirmed_results` に必ず含まれるべき (性別, 色)。保因に依らず確定する色。
    confirmed: frozenset[tuple[str, str]] = field(default_factory=frozenset)
    #: `conditional_color_groups` に (scenario, 色) で現れるべき推定色。潜在保因前提でのみ出る色。
    conditional: frozenset[tuple[str, str]] = field(default_factory=frozenset)
    #: 周辺分布 `results` に必ず含まれるべき (性別, 色)。confirmed_results が空のケース等で使う。
    results_present: frozenset[tuple[str, str]] = field(default_factory=frozenset)
    #: 周辺分布 `results` に現れてはならない (性別, 色)。優性白 epistasis の非対称性検証等。
    results_absent: frozenset[tuple[str, str]] = field(default_factory=frozenset)
    #: `results` のどの色にも部分文字列として現れてはならない語 (不可逆/カテゴリC違反の検出)。
    forbidden_substrings: frozenset[str] = field(default_factory=frozenset)
    #: 指定時、`results` の全色がこの語を含むこと (例: ポイント固定交配は全て "Point")。
    require_all_contain: str | None = None

    @property
    def label(self) -> str:
        return f"{self.sire}|{self.dam}|{self.breed or '-'}"


# --- カテゴリC (潜在保因) 由来の非展開カラー群。通常モードの確定/周辺結果に出てはならない。 ---
_CATEGORY_C = frozenset({"Chocolate", "Cinnamon", "Lilac", "Point", "Sepia", "Mink", "Fawn"})


CASES: tuple[LociCase, ...] = (
    LociCase(
        sire="Brown Tabby-White",
        dam="Cream Tabby",
        breed=None,
        rationale="A(タビー)+S(白斑)+O連鎖。確定=Brown Patched Tabby♀/Red Tabby♂。"
        "D保因で希釈Blue系・A/aでソリッド(Calico/Red)が推定として現れる。i/iなのでシルバー無し。",
        confirmed=frozenset(
            {
                ("Female", "Brown Patched Tabby"),
                ("Female", "Brown Patched Tabby-White"),
                ("Male", "Red Tabby"),
                ("Male", "Red Tabby-White"),
            }
        ),
        conditional=frozenset(
            {
                ("D_d_on_sire", "Blue Patched Tabby"),
                ("D_d_on_sire", "Cream Tabby"),
                ("A_a_on_both", "Calico"),
                ("A_a_on_both", "Tortoiseshell"),
                ("A_a_on_both", "Red"),
            }
        ),
        forbidden_substrings=_CATEGORY_C | {"Silver", "Smoke"},
    ),
    LociCase(
        sire="Blue Tabby",
        dam="Cream Tabby-White",
        breed=None,
        rationale="★D座位 d/d×d/d 不可逆。両親とも希釈のため濃色(Black/Brown/Red)は"
        "絶対に出ない。全個体が希釈(Blue/Cream)。A/aで素のソリッドが推定に出る。",
        confirmed=frozenset(
            {
                ("Female", "Blue Patched Tabby"),
                ("Female", "Blue Patched Tabby-White"),
                ("Male", "Cream Tabby"),
                ("Male", "Cream Tabby-White"),
            }
        ),
        conditional=frozenset(
            {
                ("A_a_on_both", "Blue Cream"),
                ("A_a_on_both", "Dilute Calico"),
                ("A_a_on_both", "Cream"),
            }
        ),
        # 不可逆ルールの核心: 濃色系 (Black/Brown/Red) が1色も出ないことを保証する。
        forbidden_substrings=_CATEGORY_C | {"Silver", "Smoke", "Black", "Brown", "Red"},
    ),
    LociCase(
        sire="Silver Tabby-White",
        dam="Brown Tabby",
        breed=None,
        rationale="I座位 I/-×i/i。確定=Silver Tabby。I保因(i/i化)で非シルバーBrown、"
        "A/aでBlack Smoke、D保因でBlue Silver が推定として現れる。赤親不在なのでトーティ無し。",
        confirmed=frozenset(
            {
                ("Female", "Silver Tabby"),
                ("Female", "Silver Tabby-White"),
                ("Male", "Silver Tabby"),
                ("Male", "Silver Tabby-White"),
            }
        ),
        conditional=frozenset(
            {
                ("I_i_on_sire", "Brown Tabby"),
                ("A_a_on_both", "Black Smoke"),
                ("D_d_on_both", "Blue Silver Tabby"),
            }
        ),
        forbidden_substrings=_CATEGORY_C | {"Tortie", "Tortoiseshell", "Calico"},
    ),
    LociCase(
        sire="Red Tabby-White",
        dam="Silver Tabby-White",
        breed=None,
        rationale="O(赤父)+I保因+D保因の複合。確定=Silver Patched Tabby♀/Silver Tabby♂。"
        "I保因で非シルバーBrown、A/aでSmoke(♀はTortie Smoke)、D保因でBlue Silver が推定。",
        confirmed=frozenset(
            {
                ("Female", "Silver Patched Tabby"),
                ("Female", "Silver Patched Tabby-White"),
                ("Male", "Silver Tabby"),
                ("Male", "Silver Tabby-White"),
            }
        ),
        conditional=frozenset(
            {
                ("I_i_on_dam", "Brown Patched Tabby"),
                ("I_i_on_dam", "Brown Tabby"),
                ("A_a_on_both", "Black Smoke"),
                ("A_a_on_both", "Tortie Smoke"),
                ("D_d_on_both", "Blue Silver Tabby"),
            }
        ),
        forbidden_substrings=_CATEGORY_C,
    ),
    LociCase(
        sire="Seal Point-White",
        dam="Red Tabby",
        breed=None,
        rationale="★C座位 ポイント×レギュラー。父 cs/cs だが子は C/cs でフルカラー化するため"
        "確定はフルカラーのタビー系。ポイントは母が cs 保因のとき(C_cs_on_dam)だけ推定に現れ、"
        "確定/周辺結果には出ない。A/aでソリッド、D保因で希釈も推定。",
        confirmed=frozenset(
            {
                ("Female", "Brown Patched Tabby"),
                ("Female", "Brown Patched Tabby-White"),
                ("Male", "Red Tabby"),
                ("Male", "Red Tabby-White"),
            }
        ),
        conditional=frozenset(
            {
                ("C_cs_on_dam", "Red Lynx Point"),
                ("C_cs_on_dam", "Seal Tortie Lynx Point"),
                ("A_a_on_dam", "Calico"),
                ("A_a_on_dam", "Tortoiseshell"),
                ("D_d_on_both", "Blue Patched Tabby"),
                ("D_d_on_both", "Cream Tabby"),
            }
        ),
        # ポイントは推定にのみ存在し、周辺結果に漏れてはならない (確定vs推定の分離の核心)。
        forbidden_substrings=_CATEGORY_C | {"Silver", "Smoke"},
    ),
    LociCase(
        sire="Seal Point",
        dam="Blue Point",
        breed=None,
        rationale="C座位 cs/cs×cs/cs 固定。全個体ポイント。確定=Seal Point、"
        "D保因でBlue Point が推定。両親 a/a なのでタビー(Lynx)にはならない。",
        confirmed=frozenset({("Female", "Seal Point"), ("Male", "Seal Point")}),
        conditional=frozenset({("D_d_on_sire", "Blue Point")}),
        # 全個体ポイント。タビー/シルバー/濃色フルカラー等が混ざらないこと。
        require_all_contain="Point",
        forbidden_substrings=frozenset(
            {"Tabby", "Lynx", "Silver", "Smoke", "Chocolate", "Sepia", "Mink", "Tortie", "Calico"}
        ),
    ),
    LociCase(
        sire="Chocolate Tabby",
        dam="Brown Tabby",
        breed=None,
        rationale="★B座位 カテゴリC。父 b/b でも子は B/b で黒系(Brown Tabby)が確定。"
        "チョコは母が b 保因のとき(B_b_on_dam)だけ推定に現れ、確定/周辺結果には出ない。",
        confirmed=frozenset({("Female", "Brown Tabby"), ("Male", "Brown Tabby")}),
        conditional=frozenset(
            {
                ("B_b_on_dam", "Chocolate Tabby"),
                ("A_a_on_both", "Black"),
                ("D_d_on_both", "Blue Tabby"),
            }
        ),
        # チョコ系は推定にのみ存在。周辺結果に漏れてはならない。
        forbidden_substrings=_CATEGORY_C | {"Silver", "Smoke", "Tortie", "Tortoiseshell", "Calico"},
    ),
    LociCase(
        sire="Black Smoke",
        dam="Red Tabby",
        breed=None,
        rationale="I(スモーク=ソリッド上のシルバー)+O連鎖。確定=Silver Patched Tabby♀/"
        "Cameo Tabby♂(赤シルバー)。A/aでTortie Smoke(♀)・Cameo、I保因で非シルバー、D保因で希釈が推定。",
        confirmed=frozenset(
            {("Female", "Silver Patched Tabby"), ("Male", "Cameo Tabby")}
        ),
        conditional=frozenset(
            {
                ("A_a_on_dam", "Tortie Smoke"),
                ("A_a_on_dam", "Cameo"),
                ("I_i_on_sire", "Brown Patched Tabby"),
                ("I_i_on_sire", "Red Tabby"),
                ("D_d_on_both", "Blue Silver Patched Tabby"),
                ("D_d_on_both", "Cream Cameo Tabby"),
            }
        ),
        forbidden_substrings=_CATEGORY_C,
    ),
    LociCase(
        sire="White",
        dam="Brown Tabby-White",
        breed=None,
        rationale="★W座位 優性白 epistasis (§2.1)。White父×有色母では、有色の娘は色柄を"
        "特定できず AOC、有色の息子は母の色柄が出る。この性別非対称を検証する。",
        # このケースは confirmed_results が空のため results 側で性別付き presence/absence を検証する。
        results_present=frozenset(
            {
                ("Female", "White"),
                ("Male", "White"),
                ("Female", "AOC"),
                ("Male", "Brown Tabby-White"),
            }
        ),
        results_absent=frozenset({("Male", "AOC"), ("Female", "Brown Tabby-White")}),
        forbidden_substrings=frozenset({"Silver", "Smoke", "Chocolate", "Point", "Sepia", "Mink"}),
    ),
    LociCase(
        sire="Brown Tabby",
        dam="Calico",
        breed=None,
        rationale="O(トーティ母 Calico=トーティ+白斑)+S(白斑)。確定=Brown系タビー(±White)。"
        "A/aでソリッド(♀Calico/Tortoiseshell)、D保因でBlue系が推定。i/iなのでシルバー無し。",
        confirmed=frozenset(
            {
                ("Female", "Brown Patched Tabby"),
                ("Female", "Brown Patched Tabby-White"),
                ("Female", "Brown Tabby"),
                ("Female", "Brown Tabby-White"),
                ("Male", "Brown Tabby"),
                ("Male", "Brown Tabby-White"),
                ("Male", "Red Tabby"),
                ("Male", "Red Tabby-White"),
            }
        ),
        conditional=frozenset(
            {
                ("A_a_on_sire", "Black"),
                ("A_a_on_sire", "Calico"),
                ("A_a_on_sire", "Tortoiseshell"),
                ("A_a_on_sire", "Red"),
                ("D_d_on_both", "Blue Tabby"),
                ("D_d_on_both", "Cream Tabby"),
            }
        ),
        forbidden_substrings=_CATEGORY_C | {"Silver", "Smoke"},
    ),
)


@pytest.fixture(scope="session")
def reports() -> dict[str, object]:
    """全ケースのレポートを1度だけ計算してラベル引きできるようにする。"""

    calculator = CoatColorCalculator()
    return {
        case.label: calculator.calculate_report(case.sire, case.dam, breed=case.breed)
        for case in CASES
    }


def _result_pairs(report: object) -> set[tuple[str, str]]:
    """周辺結果 `results` の (性別, 色) 集合。"""

    return {(r.sex, r.color) for r in report.results}


def _confirmed_pairs(report: object) -> set[tuple[str, str]]:
    """確定結果 `confirmed_results` の (性別, 色) 集合。"""

    return {(r.sex, r.color) for r in (report.confirmed_results or [])}


def _conditional_pairs(report: object) -> set[tuple[str, str]]:
    """推定グループを (scenario, 色) のフラットな集合へ展開する。"""

    pairs: set[tuple[str, str]] = set()
    for group in report.conditional_color_groups or []:
        for color in group.colors:
            pairs.add((group.scenario, color))
    return pairs


@pytest.mark.parametrize("case", CASES, ids=[c.label for c in CASES])
def test_no_unmatched_genotypes(case: LociCase, reports: dict[str, object]) -> None:
    """分類不能を捨てて再正規化していない (未分類率ゼロ)。"""

    report = reports[case.label]
    assert report.unmatched_probability == 0, (
        f"{case.label}: 未分類の遺伝子型が残っている (prob={report.unmatched_probability})"
    )


@pytest.mark.parametrize("case", CASES, ids=[c.label for c in CASES])
def test_probabilities_sum_to_100(case: LociCase, reports: dict[str, object]) -> None:
    """表示確率の合計は100%。"""

    report = reports[case.label]
    total = round(sum(r.probability_pct for r in report.results), 4)
    assert abs(total - 100.0) < 0.01, f"{case.label}: 合計が100%でない ({total})"


@pytest.mark.parametrize("case", CASES, ids=[c.label for c in CASES])
def test_no_nonpositive_probabilities(case: LociCase, reports: dict[str, object]) -> None:
    """0%以下 (丸めで消える項目) は出力しない。"""

    report = reports[case.label]
    bad = [(r.sex, r.color, r.probability_pct) for r in report.results if r.probability_pct <= 0]
    assert not bad, f"{case.label}: 0%以下の項目が出力されている: {bad}"


@pytest.mark.parametrize("case", CASES, ids=[c.label for c in CASES])
def test_males_have_no_female_only_colors(case: LociCase, reports: dict[str, object]) -> None:
    """X連鎖O座位により、トーティ/キャリコ/クリーム混合はオスに出ない。"""

    report = reports[case.label]
    offenders = [
        (r.color, token)
        for r in report.results
        if r.sex == "Male"
        for token in FEMALE_ONLY_SUBSTRINGS
        if token in r.color
    ]
    assert not offenders, f"{case.label}: オス結果にメス限定カラーが含まれている: {offenders}"


@pytest.mark.parametrize("case", CASES, ids=[c.label for c in CASES])
def test_confirmed_colors_present(case: LociCase, reports: dict[str, object]) -> None:
    """座位から保因に依らず確定するはずの色が confirmed_results に出ている。"""

    if not case.confirmed:
        pytest.skip("確定色の期待値なし (results 側で検証するケース)")
    report = reports[case.label]
    missing = case.confirmed - _confirmed_pairs(report)
    assert not missing, f"{case.label}: 確定色が欠落している: {sorted(missing)}"


@pytest.mark.parametrize("case", CASES, ids=[c.label for c in CASES])
def test_confirmed_colors_are_in_marginal_results(
    case: LociCase, reports: dict[str, object]
) -> None:
    """確定色は周辺分布 results にも必ず含まれる (整合性)。"""

    report = reports[case.label]
    leaked = _confirmed_pairs(report) - _result_pairs(report)
    assert not leaked, f"{case.label}: 確定色が周辺結果に無い (不整合): {sorted(leaked)}"


@pytest.mark.parametrize("case", CASES, ids=[c.label for c in CASES])
def test_conditional_colors_classified(case: LociCase, reports: dict[str, object]) -> None:
    """潜在保因前提でのみ出る推定色が、正しい scenario の conditional グループに入っている。"""

    if not case.conditional:
        pytest.skip("推定色の期待値なし")
    report = reports[case.label]
    missing = case.conditional - _conditional_pairs(report)
    assert not missing, f"{case.label}: 推定色が期待 scenario に欠落: {sorted(missing)}"


@pytest.mark.parametrize("case", CASES, ids=[c.label for c in CASES])
def test_conditional_scenarios_well_formed(case: LociCase, reports: dict[str, object]) -> None:
    """conditional シナリオ ID は 座位_保因型_on_{sire|dam|both} 形式である。"""

    report = reports[case.label]
    malformed = [
        group.scenario
        for group in (report.conditional_color_groups or [])
        if not SCENARIO_PATTERN.match(group.scenario)
    ]
    assert not malformed, f"{case.label}: 想定外の scenario 書式: {malformed}"


@pytest.mark.parametrize("case", CASES, ids=[c.label for c in CASES])
def test_forbidden_colors_absent(case: LociCase, reports: dict[str, object]) -> None:
    """不可逆ルール/カテゴリC非展開に反する色が周辺結果に漏れていない。"""

    if not case.forbidden_substrings:
        pytest.skip("禁止語なし")
    report = reports[case.label]
    offenders = sorted(
        {
            (r.color, token)
            for r in report.results
            for token in case.forbidden_substrings
            if token in r.color
        }
    )
    assert not offenders, f"{case.label}: 禁止色が周辺結果に含まれている: {offenders}"


@pytest.mark.parametrize("case", CASES, ids=[c.label for c in CASES])
def test_results_present_and_absent(case: LociCase, reports: dict[str, object]) -> None:
    """明示指定した (性別, 色) の周辺結果への出現/非出現を検証する (優性白 epistasis 等)。"""

    if not case.results_present and not case.results_absent:
        pytest.skip("results presence/absence の期待値なし")
    report = reports[case.label]
    pairs = _result_pairs(report)
    missing = case.results_present - pairs
    present_but_forbidden = case.results_absent & pairs
    assert not missing, f"{case.label}: 期待する (性別,色) が欠落: {sorted(missing)}"
    assert not present_but_forbidden, (
        f"{case.label}: 出てはならない (性別,色) が出現: {sorted(present_but_forbidden)}"
    )


@pytest.mark.parametrize("case", CASES, ids=[c.label for c in CASES])
def test_require_all_contain(case: LociCase, reports: dict[str, object]) -> None:
    """固定座位交配で全個体が特定語を含む (例: ポイント固定→全て "Point")。"""

    if case.require_all_contain is None:
        pytest.skip("全含有条件なし")
    report = reports[case.label]
    offenders = sorted(
        {r.color for r in report.results if case.require_all_contain not in r.color}
    )
    assert not offenders, (
        f"{case.label}: 全色が '{case.require_all_contain}' を含むはずが例外: {offenders}"
    )
