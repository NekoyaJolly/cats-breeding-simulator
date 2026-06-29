"""表現型と潜在遺伝子型の対応表、および計算モード別の親遺伝子型生成。"""

from __future__ import annotations

import re
from dataclasses import dataclass

AUTOSOMAL_LOCI: tuple[str, ...] = ("B", "D", "A", "C", "W", "S", "Mc", "Ta", "Sp", "I", "Wb")

# サポートする計算モード。
SUPPORTED_MODES: tuple[str, ...] = ("normal", "explicit_carrier", "carrier_exploration")

# normal_mode で X/- 展開する座位 (優性ヘテロ未確定) と、閉じる座位 (キャリア非展開)。
NORMAL_OPENED_LOCI: tuple[str, ...] = ("D", "I", "Mc", "Ta")
NORMAL_CLOSED_LOCI: tuple[str, ...] = ("A", "B", "C", "Wb")


@dataclass(frozen=True, slots=True)
class ParentGenotype:
    """親猫候補の遺伝子型。"""

    phenotype: str
    sex: str
    loci: dict[str, tuple[str, str]]


@dataclass(frozen=True, slots=True)
class KittenGenotype:
    """子猫1個体の遺伝子型。engine (交配) と phenotype_naming (命名) で共有する。"""

    sex: str
    loci: dict[str, tuple[str, str]]


def expressed_genotype_key(loci: dict[str, tuple[str, str]], sex: str) -> tuple:
    """遺伝子型を「実際に発現する表現型」レベルへ還元したキーを返す。

    完全一致辞書だけに頼ると、D/d のようなヘテロ接合の子猫が D/D の正規遺伝子型に
    一致せず分類不能になる。優性・劣性を解決した発現状態でキー化することで、親
    (CSV正規遺伝子型) と子猫 (ヘテロ接合を含む) を同じ土俵で突き合わせる。

    パターン座 (Mc / Ta / Sp) は CSV 上の符号付けが不安定なためキーから除外し、
    パターン名は親カラー名ベースの後処理 (simplify_patterns) に委ねる。
    engine (交配) と phenotype_naming (命名) の両方が使うため共有モジュールに置く。
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


@dataclass(frozen=True, slots=True)
class ColorBase:
    """1カラー (CSV 1行) の基準遺伝子型。親候補生成はここから mode 別に行う。"""

    autosomal: dict[str, tuple[str, str]]  # B/D/A/C/W/S/Mc/Ta/Sp/I/Wb
    o: tuple[str, str]                      # O_Locus (例: ("o","o"), ("O","o"))


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
        Calico / Smoke (いずれも a/a 前提) が出てしまう。A/a は explicit_carrier_mode /
        carrier_exploration_mode でのみ使う。
    - カテゴリB (表現型確定・劣性固定 / 固定する):
        d/d, a/a, cs/cs, cb/cb, cb/cs, i/i, s/s など。CSVの劣性ホモはそのまま固定。
    - カテゴリC (表現型から要求されない潜在キャリア / 通常モードでは展開しない):
        B/b チョコ, B/bl シナモン, C/cs ポイント, C/cb セピア, Wb ワイドバンド。
        明示キャリア情報または血統・産子履歴がある場合のみ explicit_carrier で扱う。

    シミュレーター正本 V9 §2.4 に準拠 (A・Wb の非展開を含む)。
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
    # Wb (ワイドバンド) も除外する。normal_mode では Wb を展開しない (Shell/Shaded/Chinchilla/
    #   Golden の wide band キャリアを自動展開しない)。Wb は explicit_carrier 等でのみ扱う。
    # S (白斑) は除外する。白斑は不完全優性で S/S(Van) と S/s(バイカラー/-White) は
    # 表現型で区別でき、入力の白斑レベルから接合性が確定する (= ヘテロ不可視ではない)。
    # さらに S/S の Van 色を S/s へ展開すると逆引きMAPが汚染され、S/s の子が Van 名へ
    # 誤マッチするため、S は CSV 記載値のまま固定する。
    dominant_expandable: dict[str, tuple[str, str]] = {
        "D": ("D", "d"),
        "I": ("I", "i"),
        "Mc": ("Mc", "mc"),
        "Ta": ("Ta", "ta"),
    }

    loci_options: dict[str, list[tuple[str, str]]] = {}
    for locus, val in full_loci.items():
        options = [val]
        hetero = dominant_expandable.get(locus)
        # 優性形質が「優性ホモ」で表現されている場合のみ X/- としてヘテロを追加する。
        # 劣性ホモ (カテゴリB) や B/C/A/Wb (カテゴリC/A') はここで展開しない。
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


def _color_base_from_row(color: str, locus_cols: list[str], row: dict[str, str]) -> ColorBase:
    """CSV 1行から ColorBase (基準遺伝子型) を構築する。B は名前から推定する。"""

    color_lower = color.lower()
    if "chocolate" in color_lower or "lilac" in color_lower or "choco" in color_lower:
        b_allele = ("b", "b")
    elif "cinnamon" in color_lower or "fawn" in color_lower:
        b_allele = ("bl", "bl")
    else:
        b_allele = ("B", "B")

    autosomal: dict[str, tuple[str, str]] = {"B": b_allele}
    for col in locus_cols:
        val = row.get(col)
        if val and val.strip():
            locus_name = col.split("_")[0]
            if locus_name == "O":
                continue
            alleles = val.strip().split("/")
            if len(alleles) == 2:
                autosomal[locus_name] = (alleles[0], alleles[1])

    o_val = (row.get("O_Locus") or "o/o").strip()
    o_parts = o_val.split("/")
    o_alleles: tuple[str, str] = (o_parts[0], o_parts[1]) if len(o_parts) == 2 else ("o", "o")
    return ColorBase(autosomal=autosomal, o=o_alleles)


def _load_color_base_loci() -> dict[str, list[ColorBase]]:
    """cat_color_genetic_map.csv から色ごとの基準遺伝子型を読み込む。

    同名複数行 (同一カラー名で複数 Code) は list で保持する。親遺伝子型は mode に応じて
    build_parent_genotypes() がこの基準から動的に生成する。
    """

    import csv
    import os

    filename = "cat_color_genetic_map.csv"
    paths_to_try = [
        filename,
        os.path.join("docs", "architecture", filename),
        os.path.join(os.path.dirname(os.path.dirname(__file__)), "docs", "architecture", filename),
        os.path.join(os.path.dirname(os.path.dirname(__file__)), filename),
    ]
    filepath = next((path for path in paths_to_try if os.path.exists(path)), None)
    # Fail-Fast: マスタが無い/壊れている状態で空データのまま起動すると、全リクエストが
    # 「未対応の毛色」になる無言の機能不全に陥る。起動時に明確に落として原因を露見させる。
    if not filepath:
        raise RuntimeError(
            f"{filename} が見つかりません (起動を中止)。CSV のコピー漏れ等を確認してください。"
            f" 探索パス: {paths_to_try}"
        )

    base: dict[str, list[ColorBase]] = {}
    try:
        with open(filepath, mode="r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            locus_cols = [c for c in (reader.fieldnames or []) if c.endswith("_Locus")]
            for row in reader:
                color = row.get("CoatColor")
                if not color:
                    continue
                base.setdefault(color, []).append(_color_base_from_row(color, locus_cols, row))
    except (OSError, UnicodeDecodeError, csv.Error) as exc:
        raise RuntimeError(
            f"{filename} の読み込みに失敗しました ({filepath}): {exc}"
        ) from exc
    # Fail-Fast: DictReader は例外を出さなくても、空ファイル・ヘッダ不正・CoatColor 列欠落だと
    # 有効行が 0 件のまま空データで起動してしまう。読み込めても中身が空なら破損として落とす。
    if not base:
        raise RuntimeError(
            f"{filename} に有効なデータがありません ({filepath})。"
            " 空ファイル・ヘッダ不正・CoatColor 列の欠落の可能性があります。"
        )
    return base


COLOR_BASE_LOCI = _load_color_base_loci()


def _parse_carrier_genotype(value: str) -> tuple[str, str] | None:
    """"C/cs" のような明示キャリア指定を (allele, allele) に変換する。不正なら None。"""

    parts = value.strip().split("/")
    if len(parts) != 2:
        return None
    return (parts[0], parts[1])


def _genotype_signature(loci: dict[str, tuple[str, str]]) -> tuple:
    """重複排除用に遺伝子型を順序非依存のキーへ変換する。"""

    return tuple(sorted((locus, tuple(sorted(alleles))) for locus, alleles in loci.items()))


def _apply_explicit_carriers(
    genotypes: list[ParentGenotype],
    color: str,
    sex: str,
    carriers: dict[str, str],
) -> list[ParentGenotype]:
    """normal 展開済み候補に、明示キャリア指定座位を上書きして「開ける」。"""

    overrides: dict[str, tuple[str, str]] = {}
    for locus, value in carriers.items():
        parsed = _parse_carrier_genotype(value)
        if parsed is not None:
            overrides[locus] = parsed
    if not overrides:
        return genotypes

    out: list[ParentGenotype] = []
    seen: set[tuple] = set()
    for genotype in genotypes:
        loci = dict(genotype.loci)
        loci.update(overrides)
        signature = _genotype_signature(loci)
        if signature in seen:
            continue
        seen.add(signature)
        out.append(ParentGenotype(phenotype=color, sex=sex, loci=loci))
    return out


def build_parent_genotypes(
    color: str,
    sex: str,
    mode: str = "normal",
    carriers: dict[str, str] | None = None,
) -> list[ParentGenotype]:
    """指定モードに応じた親遺伝子型候補を生成する。

    - normal: 未明示キャリアを閉じる (A/B/C/Wb 非展開、D/I/Mc/Ta のみ X/- 展開)。
    - explicit_carrier: normal を基準に、carriers で指定された座位のみ上書きで開ける。

    carrier_exploration は本関数では扱わない (Phase 2)。色が未知なら空リストを返す。
    """

    entries = COLOR_BASE_LOCI.get(color)
    if not entries:
        return []

    out: list[ParentGenotype] = []
    seen: set[tuple] = set()
    for entry in entries:
        sex_loci: dict[str, tuple[str, str]] = dict(entry.autosomal)
        if sex == "male":
            # トーティ (O/o) はメス限定。オスは O/Y または o/Y。
            if "O" in entry.o and "o" in entry.o:
                continue
            male_o = "O" if "O" in entry.o else "o"
            sex_loci["O"] = (male_o, "Y")
        else:
            sex_loci["O"] = entry.o

        genotypes = _build_normal_parent_genotypes(color, sex, sex_loci)
        if mode == "explicit_carrier" and carriers:
            genotypes = _apply_explicit_carriers(genotypes, color, sex, carriers)

        for genotype in genotypes:
            signature = _genotype_signature(genotype.loci)
            if signature in seen:
                continue
            seen.add(signature)
            out.append(genotype)
    return out


def _build_phenotype_genotypes() -> dict[str, dict[str, list[ParentGenotype]]]:
    """全色の normal_mode 親遺伝子型を事前構築する (逆引きMAP・入力名解決に使用)。"""

    results: dict[str, dict[str, list[ParentGenotype]]] = {}
    for color in COLOR_BASE_LOCI:
        results[color] = {
            "male": build_parent_genotypes(color, "male", "normal"),
            "female": build_parent_genotypes(color, "female", "normal"),
        }
    return results


PHENOTYPE_GENOTYPES = _build_phenotype_genotypes()


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

    # Fail-Fast: 部分データや空データで起動を続けず、欠落・破損を起動時に露見させる。
    if not filepath:
        raise RuntimeError(
            f"{filename} が見つかりません (起動を中止)。CSV のコピー漏れ等を確認してください。"
            f" 探索パス: {paths_to_try}"
        )

    definitions = []
    try:
        with open(filepath, mode="r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get("CoatColor"):
                    definitions.append(dict(row))
    except (OSError, UnicodeDecodeError, csv.Error) as exc:
        raise RuntimeError(
            f"{filename} の読み込みに失敗しました ({filepath}): {exc}"
        ) from exc
    # Fail-Fast: 空ファイル・ヘッダ不正・CoatColor 列欠落だと有効行 0 件で空のまま起動するため落とす。
    if not definitions:
        raise RuntimeError(
            f"{filename} に有効なデータがありません ({filepath})。"
            " 空ファイル・ヘッダ不正・CoatColor 列の欠落の可能性があります。"
        )
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

    # Fail-Fast: 猫種マスタが無いまま少数のハードコード猫種で起動すると、
    # 大半の猫種が無言で欠落する。起動時に落として CSV のコピー漏れを露見させる。
    if not filepath:
        raise RuntimeError(
            f"{filename} が見つかりません (起動を中止)。CSV のコピー漏れ等を確認してください。"
            f" 探索パス: {paths_to_try}"
        )

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
    except (OSError, UnicodeDecodeError, csv.Error) as exc:
        raise RuntimeError(
            f"{filename} の読み込みに失敗しました ({filepath}): {exc}"
        ) from exc

    # Fail-Fast: 空ファイル・ヘッダ不正・Breed 列欠落だと有効な猫種行が 0 件になる。
    # Munchkin 補完で非空に見えてしまう前に、ここで破損を検知して落とす。
    if not filters:
        raise RuntimeError(
            f"{filename} に有効な猫種データがありません ({filepath})。"
            " 空ファイル・ヘッダ不正・Breed 列の欠落の可能性があります。"
        )

    # Munchkin は SH/LH 変種のみで bare 行が無い場合があるため、テスト互換で空制約を補完する。
    if "Munchkin" not in filters:
        filters["Munchkin"] = {}

    return filters


BREED_FILTERS = _load_breed_filters()


def _breed_allele_matches(actual: tuple[str, str], required: tuple[str, str]) -> bool:
    """genotype の actual が breed 制約 required を満たすか (engine._matches_exact と同等)。

    X 連鎖 (Y を含むオス) は非 Y 側アレルで判定する。
    """

    if "Y" in actual:
        non_y = actual[0] if actual[1] == "Y" else actual[1]
        return non_y == required[0] if required[0] == required[1] else False
    return actual == required or actual == (required[1], required[0])


def breed_color_group_label(breed_key: str) -> str:
    """猫種制約を代表する「系」ラベルを返す (エラーメッセージ用)。該当なしは空文字。"""

    constraints = BREED_FILTERS.get(breed_key, {})
    c_pair = constraints.get("C")
    if c_pair is not None:
        c_sorted = tuple(sorted(c_pair))
        if c_sorted == ("cb", "cb"):
            return "セピア系"
        if c_sorted == ("cs", "cs"):
            return "ポイント系"
        if c_sorted == ("cb", "cs"):
            return "ミンク系"
    if constraints.get("Ta") == ("Ta", "Ta"):
        return "ティックドタビー系"
    if constraints.get("A") == ("a", "a"):
        return "ソリッド系"
    return ""


def recognized_color_keys_for_breed(breed_key: str) -> list[str] | None:
    """その猫種の遺伝制約を満たす毛色 (PHENOTYPE_GENOTYPES のキー) 一覧を返す。

    制約の無い猫種は None (= 全色が認定カラー扱い)。canonical 化は呼び出し側に委ねる。
    """

    constraints = BREED_FILTERS.get(breed_key)
    if not constraints:
        return None
    result: list[str] = []
    for color, sex_dict in PHENOTYPE_GENOTYPES.items():
        matched = any(
            all(
                _breed_allele_matches(genotype.loci[locus], required)
                for locus, required in constraints.items()
                if locus in genotype.loci
            )
            for sex in ("male", "female")
            for genotype in sex_dict[sex]
        )
        if matched:
            result.append(color)
    return result


def is_real_breed(name: str) -> bool:
    """ASCII 英字を含む猫種名か (CSV 由来の文字化け / ゴミ行 "ｱｷ" 等を弾く)。

    /api/v1/breeds の一覧と calculate のバリデーションで同一基準を使うための共通判定。
    """

    return any("a" <= char.lower() <= "z" for char in name)


# コート/物理バリアントのトークン (Short/Long Hair, ear/leg 等の登録変種コード)。
# 括弧注記がこれらだけで構成される場合は同一猫種のバリアント違いとみなし base に集約する。
# 色違い等 (AOC / HIMALAYAN 等) は意味が異なるため畳まず残す。
_BREED_VARIANT_TOKENS: frozenset[str] = frozenset(
    {"SH", "LH", "NL", "SE", "LE", "ST", "LWH", "SWH"}
)
_BREED_VARIANT_PAREN = re.compile(r"^(.*?)\s*\(([^)]*)\)\s*$")


def _breed_base(name: str) -> str:
    """コートバリアント注記 (例 "Kinkaro (SH.SE)") を base ("Kinkaro") へ畳む。"""

    match = _BREED_VARIANT_PAREN.match(name)
    if not match:
        return name
    tokens = [token for token in re.split(r"[.\s]+", match.group(2)) if token]
    if tokens and all(token.upper() in _BREED_VARIANT_TOKENS for token in tokens):
        return match.group(1).strip()
    return name


def _build_canonical_breeds() -> dict[str, bool]:
    """入力候補 / バリデーション用に猫種を base 集約する (ゴミ除外 + 変種統合)。

    返り値: 猫種名 -> affects_genetics (座位制約があり計算結果に影響するか)。
    変種は制約 OR で統合する (実データ上、集約対象は全て制約なし)。
    """

    canonical: dict[str, bool] = {}
    for name, constraints in BREED_FILTERS.items():
        if not is_real_breed(name):
            continue
        base = _breed_base(name)
        canonical[base] = canonical.get(base, False) or bool(constraints)
    return canonical


# 入力候補 / バリデーションの正本 (base 集約済 + ゴミ除外)。
CANONICAL_BREEDS: dict[str, bool] = _build_canonical_breeds()
VALID_BREEDS: frozenset[str] = frozenset(CANONICAL_BREEDS)
