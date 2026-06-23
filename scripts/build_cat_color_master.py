"""猫色柄マスター唯一正本 cat_color_master.csv を生成するビルドスクリプト。

目的:
    元データ (docs/architecture/色柄データUTF8Ver.csv) と
    遺伝子座付き作業版 (docs/architecture/cat_color_genetic_map.csv) を比較し、
    機械可読な色柄概念マスター cat_color_master.csv と
    人間レビュー用レポート cat_color_master_review.md を生成する。

設計方針 (カラー正本作成依頼プロンプトに準拠):
    - 元データ名を一切失わない (全行を SourceCodes / SourceNames に保持)。
    - 別名 (alias) も独立行として持つ。固有 ColorId + Status=alias + Notes に
      resolves_to=<canonical_color_id> を記録する (ユーザー確定の構造)。
    - CFA / TICA / 日本実務の呼称差は同一概念の alias として統合する。
    - 猫種固有呼称 (Burmese / Tonkinese / Oriental / Abyssinian / Somali / Bengal /
      Ragdoll 等) は breed_specific として分離し、一般表示しない。
    - `Pt` は Patched と解釈し Notes に明記する (Point へ無条件変換しない)。
    - 不確かなものは canonical 確定せず review に残す。
    - `Any` という語は仕様値・モード名として使わない (breed_unselected /
      no_breed_filter / general / unrestricted 等に置換)。

このスクリプトは engine.py / API ロジック / 運用系ファイルを一切変更しない。

実行:
    cd "C:/Users/Nekoya2/appprojects/cats-breeding-simulator"
    PYTHONPATH=. python scripts/build_cat_color_master.py
    (Windows PowerShell: python scripts/build_cat_color_master.py)
"""

from __future__ import annotations

import csv
import os
import re

# ---------------------------------------------------------------------------
# パス定義 (リポジトリルートからの相対)
# ---------------------------------------------------------------------------
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARCH_DIR = os.path.join(ROOT, "docs", "architecture")
SOURCE_CSV = os.path.join(ARCH_DIR, "色柄データUTF8Ver.csv")
MAP_CSV = os.path.join(ARCH_DIR, "cat_color_genetic_map.csv")
OUT_MASTER = os.path.join(ARCH_DIR, "cat_color_master.csv")
OUT_REVIEW = os.path.join(ARCH_DIR, "cat_color_master_review.md")

# master CSV のカラム順 (依頼プロンプトの必須カラム + CanonicalColorId)。
# CanonicalColorId は alias 解決を機械可読にする専用カラム。ColorId の直後に置く。
MASTER_COLUMNS = [
    "ColorId", "CanonicalColorId", "Status", "PrimaryName", "Aliases", "RegistryNotes",
    "BreedContext", "ColorGroup", "BaseSeries", "OrangeState", "Dilution", "AgoutiState",
    "SilverState", "WhiteState", "PointState", "PatternState", "SexRestriction",
    "DisplayAllowed", "InputAllowed", "OutputPriority", "SourceCodes", "SourceNames",
    "GeneticRuleSource", "Notes",
]


# ---------------------------------------------------------------------------
# 1. 入力ファイルの読み込み (UTF-8 BOM を考慮)
# ---------------------------------------------------------------------------
def load_source_colors() -> dict[int, str]:
    """元データを {Code: 生の色柄名} で返す。空行 (名前なし) は除外する。"""

    colors: dict[int, str] = {}
    with open(SOURCE_CSV, mode="r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            code_raw = (row.get("Code") or "").strip()
            name = (row.get("CoatColor") or "").strip()
            if not code_raw:
                continue
            code = int(code_raw)
            if not name:
                # 名前なし (code 0 等) は excluded 扱いとして別途記録するためここでは保持しない
                continue
            colors[code] = name
    return colors


def load_genetic_map() -> dict[int, dict[str, str]]:
    """遺伝子座付き作業版を {Code: 行dict} で返す。"""

    rows: dict[int, dict[str, str]] = {}
    with open(MAP_CSV, mode="r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            code_raw = (row.get("Code") or "").strip()
            if not code_raw:
                continue
            rows[int(code_raw)] = {k: (v or "").strip() for k, v in row.items()}
    return rows


# ---------------------------------------------------------------------------
# 2. 名前の正規化 (略称・タイポ展開)
# ---------------------------------------------------------------------------
def expand_abbreviations(raw: str) -> tuple[str, list[str]]:
    """略称・タイポを正規形へ展開する。変更点リストも返す。

    Pt → Patched は依頼プロンプトの最重要注意点。Point へは変換しない。
    """

    changes: list[str] = []
    name = re.sub(r"\s+", " ", raw.strip())

    def sub(pattern: str, repl: str, label: str) -> None:
        nonlocal name
        new = re.sub(pattern, repl, name)
        if new != name:
            changes.append(label)
            name = new

    # タイポ修正
    sub(r"\bBrowm\b", "Brown", "Browm→Brown")
    sub(r"\bTobie\b", "Torbie", "Tobie→Torbie")
    # 略称 (ハイフン系を先に処理)
    sub(r"\bP-F\b", "Peke-Face", "P-F→Peke-Face")
    sub(r"\bBi-C\b", "Bi-Color", "Bi-C→Bi-Color")
    sub(r"-W Van\b", "-White Van", "-W Van→-White Van")
    sub(r"\bT-W\b", "Tabby-White", "T-W→Tabby-White")
    sub(r"Tabby-W\b", "Tabby-White", "Tabby-W→Tabby-White")
    sub(r"-W\b", "-White", "-W→-White")
    # 単語単位の略称展開
    sub(r"\bMc\b", "Mackerel", "Mc→Mackerel")
    sub(r"\bSp\b", "Spotted", "Sp→Spotted")
    sub(r"\bTc\b", "Ticked", "Tc→Ticked")
    sub(r"\bPt\b", "Patched", "Pt→Patched (Point ではない)")
    sub(r"\bChoco\b", "Chocolate", "Choco→Chocolate")

    name = re.sub(r"\s+", " ", name).strip()
    return name, changes


PAREN_RE = re.compile(r"\s*\(([^)]*)\)\s*")


def strip_parentheticals(name: str) -> tuple[str, list[str]]:
    """括弧内の団体タグ・補足を概念名から除き、括弧内容を別途返す。"""

    notes = [m.strip() for m in PAREN_RE.findall(name) if m.strip()]
    base = re.sub(PAREN_RE, " ", name)
    base = re.sub(r"\s+", " ", base).strip()
    return base, notes


def make_color_id(name: str) -> str:
    """概念名から snake_case の ColorId を生成する。"""

    cid = name.lower()
    cid = re.sub(r"\([^)]*\)", "", cid)
    cid = cid.replace("&", " and ").replace("+", " plus ")
    cid = cid.replace("'", "")
    cid = re.sub(r"[^a-z0-9]+", "_", cid)
    cid = re.sub(r"_+", "_", cid).strip("_")
    return cid


# ---------------------------------------------------------------------------
# 3. 分類用の決定テーブル
# ---------------------------------------------------------------------------
# 純粋に運用上の非カラー (通常計算・入力候補に使わない)
EXCLUDED_CONCEPTS = {"any other color", "aov"}

# 別名 → canonical 概念名。CFA/TICA/日本実務/猫種呼称差の同一概念統合。
# resolves_to は対象概念の ColorId を後段で算出する。
ALIAS_TARGETS: dict[str, str] = {
    # 希釈トーティ系: CFA「Blue Cream」= TICA「Blue Tortie」
    "blue cream": "Blue Tortie",
    "lilac cream": "Lilac Tortie",
    "blue cream point": "Blue Tortie Point",
    "blue cream-white": "Dilute Calico",
    # トーティ&白 / 三毛系
    "tortoiseshell-white": "Calico",
    "blue tortie-white": "Dilute Calico",
    "mike tri color": "Calico",
    # 実務商標名・別系統呼称
    "blue gray": "Blue",
    "bronze": "Brown Tabby",
    # Oriental 呼称 (一般概念へ寄せる。表示は alias map 側で Oriental 文脈に復元)
    "ebony": "Black",
    "lavender": "Lilac",
    "chestnut": "Chocolate",
    "chestnut tortie": "Chocolate Tortie",
}

# 猫種固有呼称の検出: (判定するトークン/部分文字列, BreedContext)
# 順序が優先度。最初にマッチしたものを採用する。
BREED_SPECIFIC_RULES: list[tuple[str, str]] = [
    ("ruddy", "Abyssinian"),
    ("usual", "Abyssinian"),
    ("sorrel", "Abyssinian"),
    ("mink", "Tonkinese"),
    ("sable", "Burmese"),
    ("champagne", "Burmese"),
    ("platinum", "Burmese"),
    ("sepia", "Burmese"),
    ("natural mink", "Tonkinese"),
    ("natural point", "Tonkinese"),
    ("natural solid", "Tonkinese"),
    ("leopard", "Bengal"),
    ("rosettes", "Bengal"),
    ("marble", "Bengal"),
    ("marbled", "Bengal"),
    ("snow", "Bengal"),
    ("ebony", "Oriental"),
    ("chestnut", "Oriental"),
    ("lavender", "Oriental"),
    ("mitted", "Ragdoll"),
    ("bi-color", "Ragdoll"),
]

# 自動判断できず人間レビューに回す概念 (依頼プロンプトの review 指定相当)
# 注: Shaded は別概念として canonical 維持 (追加レビュー判断 #3) のため review から外した。
#     Shell は Chinchilla と同一概念へ寄せる (#2) が、基色不明な単独 Shell は review に残す。
REVIEW_CONCEPTS = {
    "smoke",                       # 単独 Smoke は基色不明
    "calico smoke", "smoke calico", "smoke dilute calico", "smoke calico van",
    "smoke tortoiseshell",         # スモーク×トーティ/キャリコ境界が曖昧
    "shell cream", "shell blue", "cream shell cameo",  # 基色不明な Shell 系
}

# 一般表示してよい代表 canonical 概念 (DisplayAllowed=true の明示許可リスト)。
# ここに無い canonical でも構造から true 判定する場合があるが、Point/Mink/Sepia/
# Van/Mitted/Bi-Color は構造ルールで false にする。
GENERAL_SOLID = {"black", "blue", "chocolate", "lilac", "cinnamon", "fawn", "red", "cream"}


# ---------------------------------------------------------------------------
# 4. 遺伝属性の導出
# ---------------------------------------------------------------------------
def tokens(name: str) -> set[str]:
    return set(re.sub(r"[()/-]", " ", name.lower()).split())


def _loci_from_map(map_row: dict[str, str] | None) -> dict[str, str]:
    if not map_row:
        return {}
    out: dict[str, str] = {}
    for key, val in map_row.items():
        if key.endswith("_Locus") and val:
            out[key[: -len("_Locus")]] = val
    return out


def derive_attributes(name: str, loci: dict[str, str]) -> dict[str, str]:
    """概念名 + (あれば) 遺伝子座から各属性を導出する。

    遺伝子座が揃っている座 (D/A/C/O/I/S/Wb) は loci を優先し、
    パターン (Mc/Ta/Sp) と基色 (B) は名前から判定する
    (engine.py の方針: パターン座の符号は不安定、B 列はマップに無い)。
    """

    cn = name.lower()
    tok = tokens(name)

    is_white = "white" in cn
    is_van = "van" in tok
    is_mitted = "mitted" in tok
    is_bicolor = ("bi" in tok and "color" in tok) or "bicolor" in cn
    is_point = "point" in tok
    is_lynx = "lynx" in tok
    is_mink = "mink" in tok
    is_sepia = "sepia" in tok
    is_smoke = "smoke" in tok
    is_cameo = "cameo" in tok
    is_tabby = "tabby" in tok
    is_patched = "patched" in tok or "torbie" in tok
    is_calico = "calico" in tok or "tri" in tok
    is_shaded = "shaded" in tok  # noqa: E501 (以降の属性導出で参照)
    is_shell = "shell" in tok
    is_chinchilla = "chinchilla" in tok
    is_golden = "golden" in tok
    has_ticked = "ticked" in tok
    has_spotted = "spotted" in tok or "rosettes" in cn or "leopard" in cn
    has_mackerel = "mackerel" in tok
    has_classic = "classic" in tok or "marble" in cn or "marbled" in cn

    is_tortie = is_calico or any(
        w in cn for w in ("tortie", "tortoiseshell", "torbie")
    ) or ("cream" in tok and any(w in cn for w in ("blue cream", "lilac cream", "choco cream", "chocolate cream")))

    # --- BaseSeries (B 系列: 名前から) ---
    if any(w in cn for w in ("chocolate", "choco", "chestnut", "champagne")):
        base_series = "chocolate"
    elif any(w in cn for w in ("cinnamon", "fawn", "sorrel")):
        base_series = "cinnamon"
    elif any(w in cn for w in ("lilac", "lavender", "platinum")):
        base_series = "chocolate"  # lilac/lavender = 希釈チョコ, platinum = Burmese lilac
    elif is_tortie:
        base_series = "black"  # トーティの eumelanin 側は既定で black 系
    elif any(w in cn for w in ("red", "cream", "cameo", "flame", "peke-face red")):
        base_series = "red"
    elif any(w in cn for w in ("black", "blue", "silver", "brown", "seal", "ebony", "sable", "smoke", "natural", "snow", "bronze", "tawny", "leopard")):
        base_series = "black"
    else:
        base_series = "unknown"

    # --- OrangeState ---
    o_loc = loci.get("O", "")
    if is_tortie:
        orange = "tortie"
    elif any(w in cn for w in ("red", "cream", "cameo", "flame", "peke-face red")):
        orange = "orange"
    elif o_loc == "o/o":
        orange = "non_orange"
    elif o_loc in ("O/O",):
        orange = "orange"
    elif o_loc in ("O/o", "o/O"):
        orange = "tortie"
    else:
        orange = "non_orange"

    # --- Dilution ---
    d_loc = loci.get("D", "")
    if d_loc == "d/d":
        dilution = "dilute"
    elif d_loc in ("D/D", "D/d", "d/D"):
        dilution = "dense"
    elif any(w in cn for w in ("blue", "cream", "lilac", "fawn", "lavender", "platinum", "dilute")):
        dilution = "dilute"
    else:
        dilution = "dense"

    # --- AgoutiState ---
    a_loc = loci.get("A", "")
    is_agouti_name = is_tabby or has_ticked or has_spotted or has_mackerel or has_classic or is_patched or (is_point and is_lynx) or is_chinchilla or is_shaded or is_golden or is_shell
    if a_loc == "a/a":
        agouti = "solid"
    elif a_loc and "A" in a_loc:
        agouti = "agouti"
    elif is_agouti_name:
        agouti = "agouti"
    else:
        agouti = "solid"

    # --- SilverState ---
    i_loc = loci.get("I", "")
    silver_present = ("I" in i_loc) if i_loc else (is_smoke or is_cameo or "silver" in cn or is_chinchilla or (is_shaded and "golden" not in cn))
    if not silver_present:
        silver = "non_silver"
    elif is_smoke:
        silver = "smoke"
    elif is_cameo:
        silver = "cameo"
    else:
        silver = "silver"

    # 追加レビュー判断 #5: Smoke = solid(a/a) + inhibitor I/-。常に非アグチ。
    if is_smoke:
        agouti = "solid"
        silver = "smoke"
    # 追加レビュー判断 #4: Golden = non_silver + agouti + wideband/tipping。
    # マップに I/I・a/a の誤りがあっても Golden は non_silver・agouti として扱う。
    if is_golden:
        silver = "non_silver"
        agouti = "agouti"

    # --- WhiteState ---
    s_loc = loci.get("S", "")
    if is_van or s_loc == "S/S":
        white = "van"
    elif is_mitted:
        white = "mitted"
    elif is_bicolor:
        white = "bicolor"
    elif is_white or s_loc in ("S/s", "s/S"):
        white = "white"
    else:
        white = "none"

    # --- PointState ---
    c_loc = loci.get("C", "")
    if is_mink or c_loc == "cb/cs":
        point = "mink"
    elif is_sepia or c_loc == "cb/cb":
        point = "sepia"
    elif is_point or c_loc == "cs/cs":
        point = "point"
    else:
        point = "full"

    # --- PatternState (名前優先) ---
    if has_ticked:
        pattern = "ticked"
    elif has_spotted:
        pattern = "spotted"
    elif has_mackerel:
        pattern = "mackerel"
    elif has_classic:
        pattern = "classic"
    elif is_shaded:
        pattern = "shaded"
    elif is_shell or is_chinchilla:
        pattern = "shell"
    elif is_tabby or is_patched:
        pattern = "tabby"
    else:
        pattern = "none"

    # --- ColorGroup ---
    if is_calico:
        group = "calico"
    elif is_mink:
        group = "mink"
    elif is_sepia:
        group = "sepia"
    elif is_point:
        group = "point"
    elif is_patched:
        group = "patched_tabby"
    elif is_smoke:
        group = "smoke"
    elif is_shaded or is_shell or is_chinchilla:
        group = "shaded"
    elif is_tortie:
        group = "tortie"
    elif is_tabby and silver_present:
        group = "silver_tabby"
    elif is_tabby:
        group = "tabby"
    else:
        group = "solid"

    return {
        "ColorGroup": group,
        "BaseSeries": base_series,
        "OrangeState": orange,
        "Dilution": dilution,
        "AgoutiState": agouti,
        "SilverState": silver,
        "WhiteState": white,
        "PointState": point,
        "PatternState": pattern,
    }


def sex_restriction(name: str, attrs: dict[str, str]) -> str:
    """性別制限を判定する。トーティ/キャリコ/パッチド系はメス限定。"""

    if attrs["OrangeState"] == "tortie" or attrs["ColorGroup"] in ("calico", "patched_tabby", "tortie"):
        return "female_only"
    cn = name.lower()
    if any(w in cn for w in ("tortie", "tortoiseshell", "calico", "torbie", "patched", "blue cream", "lilac cream", "choco cream")):
        return "female_only"
    return "unrestricted"


# ---------------------------------------------------------------------------
# 5. Status 分類
# ---------------------------------------------------------------------------
def detect_breed_specific(concept_lower: str) -> str | None:
    """猫種固有呼称なら BreedContext を返す。一般色なら None。"""

    tok = set(concept_lower.replace("-", " ").split())
    for needle, breed in BREED_SPECIFIC_RULES:
        # スペース/ハイフンを含む語は部分一致 (例: "bi-color" はトークン分割されるため)、
        # 単一トークン語は単語一致で判定する。
        if " " in needle or "-" in needle:
            if needle in concept_lower:
                return breed
        else:
            if needle in tok:
                return breed
    return None


def classify(concept: str, attrs: dict[str, str], in_map: bool) -> dict[str, str]:
    """概念を Status 等へ分類する。

    返却: Status, BreedContext, DisplayAllowed, InputAllowed, GeneticRuleSource,
          ResolvesTo, RegistryNotes(追加分), Notes(追加分)
    """

    cl = concept.lower()
    notes: list[str] = []
    registry: list[str] = []
    resolves_to = ""
    genetic_src = "current_map" if in_map else "inferred"

    # 1) excluded
    if cl in EXCLUDED_CONCEPTS:
        return _decision("excluded", "general", False, False, "review_required",
                         "", [], ["運用上の非カラー区分。通常計算・入力候補に使わない。"])

    # 2) review (明示)
    if cl in REVIEW_CONCEPTS:
        return _decision("review", "general", False, False, "review_required",
                         "", [], ["自動判断不能。スモーク×トーティ/shell境界等で人間確認待ち。"])

    # 3) alias (明示テーブル)
    if cl in ALIAS_TARGETS:
        target = ALIAS_TARGETS[cl]
        resolves_to = make_color_id(target)
        breed = detect_breed_specific(cl) or "general"
        registry.append(f"同一概念: {concept} → {target} ({make_color_id(target)})")
        notes.append(f"一般表示は {target} に寄せる (機械処理は CanonicalColorId を参照)。")
        if breed != "general":
            notes.append(f"{breed} 文脈の呼称。")
        return _decision("alias", breed, False, True, "review_required" if breed != "general" else genetic_src,
                         resolves_to, registry, notes)

    # 3.5) Peke-Face / P-F = 形態・タイプ由来語 (色柄ではない / 追加レビュー判断 #1)
    # 「Peke-Face」を除去して残った汎用カラーへ alias 解決する。
    if "peke-face" in cl:
        target_name = re.sub(r"peke-face\s*", "", concept, flags=re.IGNORECASE).strip()
        target_name = re.sub(r"\s+", " ", target_name)
        resolves_to = make_color_id(target_name)
        registry.append(f"Peke-Face は形態/タイプ由来語: {concept} → {target_name} ({resolves_to})")
        notes.append(f"Peke-Face は色柄ではないため除去し、残った色柄 {target_name} へ解決。")
        # 旧データ互換のため InputAllowed=true は許容、DisplayAllowed=false。
        return _decision("alias", "general", False, True, genetic_src, resolves_to, registry, notes)

    # 3.6) Chinchilla = Shell と同一概念 (追加レビュー判断 #2)
    # 内部 canonical は Shell 側に寄せ、Chinchilla は alias とする。
    if "chinchilla" in cl:
        shell_name = re.sub(r"chinchilla", "Shell", concept, flags=re.IGNORECASE)
        shell_name = re.sub(r"\s+", " ", shell_name).strip()
        resolves_to = make_color_id(shell_name)
        registry.append(f"Shell/Chinchilla 同一概念: {concept} → {shell_name} ({resolves_to})")
        notes.append(f"Chinchilla は Shell と同一概念。一般表示は {shell_name} に寄せる (機械処理は CanonicalColorId)。")
        return _decision("alias", "general", False, True, "review_required", resolves_to, registry, notes)

    # 4) Torbie (TICA) = Patched Tabby (CFA/実務)
    if "torbie" in cl:
        target_name = re.sub(r"torbie", "Patched Tabby", concept, flags=re.IGNORECASE)
        # パターン語を除いた基本 patched tabby を resolves_to 候補にする
        base_target = re.sub(r"\b(classic|mackerel|spotted|ticked)\b", " ", target_name, flags=re.IGNORECASE)
        base_target = re.sub(r"\s+", " ", base_target).strip()
        resolves_to = make_color_id(base_target)
        registry.append(f"TICA: Torbie = Patched Tabby ({base_target})")
        notes.append(f"一般表示は {base_target} に寄せる (機械処理は CanonicalColorId を参照)。")
        return _decision("alias", "general", False, True, genetic_src, resolves_to, registry, notes)

    # 5) breed_specific
    breed = detect_breed_specific(cl)
    if breed is not None:
        notes.append(f"{breed} 固有呼称。breed_unselected の normal_mode 結果には出さない。")
        return _decision("breed_specific", breed, False, True, "review_required", "", [], notes)

    # 6) canonical
    # DisplayAllowed: Point/Mink/Sepia/Van/Mitted/Bi-Color は一般表示しない (エンジンのモード/
    # 白斑正規化が別途担う)。それ以外の標準色は一般表示可。
    no_general = attrs["PointState"] in ("point", "mink", "sepia") or attrs["WhiteState"] in ("van", "mitted", "bicolor")
    display = not no_general
    # ワイドバンド/Cameo境界/Point系/Golden系は遺伝子ルール要確認
    if attrs["ColorGroup"] in ("shaded",) or attrs["PointState"] in ("point", "mink", "sepia") or "golden" in cl:
        genetic_src = "review_required"
        notes.append("遺伝子座 (Wb / C系) は要確認。")
    # 追加レビュー判断 #4: Golden の概念条件を明記
    if "golden" in cl:
        notes.append("Golden = non_silver + agouti + wideband/tipping。i/i のみ・Wb/- のみでは確定しない (要 Wb/- + tipping)。")
    # 追加レビュー判断 #5: Smoke は別系統
    if "smoke" in cl:
        notes.append("Smoke = solid(a/a) + inhibitor I/-。Shell/Shaded/Chinchilla/Golden(Wb系)とは別系統。")
    # 追加レビュー判断 #2/#3: Shell/Shaded の区別
    if attrs["ColorGroup"] == "shaded" and "golden" not in cl:
        if "shell" in cl:
            notes.append("Shell = Chinchilla と同一概念 (canonical は Shell 側)。tipping量で Shaded と区別。")
        else:
            notes.append("Shaded = tipping量が Shell/Chinchilla と異なる別概念 (canonical 維持)。")
    if attrs["PointState"] in ("point",):
        notes.append("Point は normal_mode (breed_unselected) では C キャリア規則によりエンジンが非表示にする。")
    if attrs["WhiteState"] == "van":
        notes.append("Van (S/S) は一般表示で -White に正規化。入力/猫種文脈でのみ Van 表示。")
    return _decision("canonical", "general", display, True, genetic_src, "", registry, notes)


def _decision(status, breed, display, inp, genetic_src, resolves_to, registry, notes) -> dict[str, str]:
    return {
        "Status": status,
        "BreedContext": breed,
        "DisplayAllowed": "true" if display else "false",
        "InputAllowed": "true" if inp else "false",
        "GeneticRuleSource": genetic_src,
        "ResolvesTo": resolves_to,
        "RegistryNotesExtra": " / ".join(registry),
        "NotesExtra": " / ".join(notes),
    }


def output_priority(status: str, attrs: dict[str, str]) -> int:
    if status == "excluded":
        return 0
    if status == "review":
        return 5
    if status == "alias":
        return 10
    if status == "breed_specific":
        return 20
    # canonical
    if attrs["WhiteState"] in ("van", "mitted", "bicolor"):
        return 30
    if attrs["PointState"] in ("point", "mink", "sepia"):
        return 50
    if attrs["ColorGroup"] in ("shaded",):
        return 70
    if attrs["SilverState"] in ("silver", "smoke", "cameo") or attrs["ColorGroup"] in ("silver_tabby", "smoke"):
        return 80
    if attrs["ColorGroup"] in ("tabby", "patched_tabby", "calico", "tortie"):
        return 90
    if attrs["ColorGroup"] == "solid" and attrs["BaseSeries"] in ("black", "chocolate", "cinnamon", "red"):
        return 100
    return 60


# ---------------------------------------------------------------------------
# 6. 概念グループの構築
# ---------------------------------------------------------------------------
class Concept:
    """1 つの色柄概念 (1 出力行に対応)。"""

    def __init__(self, primary_name: str):
        self.primary_name = primary_name
        self.source_codes: list[int] = []
        self.source_names: list[str] = []
        self.aliases: set[str] = set()
        self.registry_notes: list[str] = []
        self.paren_tags: list[str] = []  # 括弧内の団体/補足タグ (重複排除して保持)
        self.change_notes: set[str] = set()
        self.loci: dict[str, str] = {}
        self.in_map = False
        self.synthetic = False       # Shell/Chinchilla 同一概念のため合成した canonical 行
        self.derived_from = ""       # 合成元 (Chinchilla 名)


def normalize_concept(raw: str) -> tuple[str, str, list[str], list[str]]:
    """生名 → (概念名, 概念名lower, 変更点, 括弧補足)。"""

    expanded, changes = expand_abbreviations(raw)
    concept, paren = strip_parentheticals(expanded)
    return concept, concept.lower(), changes, paren


def build_concepts(
    source: dict[int, str], gmap: dict[int, dict[str, str]]
) -> tuple[dict[str, Concept], dict[str, object]]:
    """元データ + マップ から概念グループを構築する。差分統計も返す。"""

    concepts: dict[str, Concept] = {}
    name_mismatches: list[tuple[int, str, str]] = []

    # 元データを概念へ集約
    for code in sorted(source):
        raw = source[code]
        concept_name, cl, changes, paren = normalize_concept(raw)
        c = concepts.get(cl)
        if c is None:
            c = Concept(concept_name)
            concepts[cl] = c
        c.source_codes.append(code)
        c.source_names.append(raw)
        c.change_notes.update(changes)
        for p in paren:
            if p not in c.paren_tags:
                c.paren_tags.append(p)

        # 同一 code の遺伝子座マップ名と概念名を比較
        if code in gmap:
            map_name = gmap[code].get("CoatColor", "")
            map_concept, _, _, _ = normalize_concept(map_name)
            if map_concept.lower() == cl:
                if not c.loci:
                    c.loci = _loci_from_map(gmap[code])
                    c.in_map = True
            else:
                name_mismatches.append((code, raw, map_name))

    # マップにしか無い概念を追加 (元データに無い色柄)
    source_concept_keys = set(concepts.keys())
    map_only: list[tuple[int, str]] = []
    for code in sorted(gmap):
        map_name = gmap[code].get("CoatColor", "")
        if not map_name:
            continue
        concept_name, cl, changes, paren = normalize_concept(map_name)
        if cl in source_concept_keys:
            continue
        # 同名概念が既にマップ由来で追加済みなら統合
        c = concepts.get(cl)
        if c is None:
            c = Concept(concept_name)
            c.registry_notes.append("map_only: 元データに無く cat_color_genetic_map.csv のみに存在")
            concepts[cl] = c
            map_only.append((code, map_name))
        c.source_codes.append(code)
        c.source_names.append(f"[map] {map_name}")
        c.change_notes.update(changes)
        if not c.loci:
            c.loci = _loci_from_map(gmap[code])
            c.in_map = True

    # 追加レビュー判断 #2: Chinchilla = Shell 同一概念。
    # Chinchilla 概念に対応する Shell 側 canonical が無ければ合成する
    # (Chinchilla 行は classify() で alias 化され、ここで作る Shell 行が解決先になる)。
    synthesized_shell: list[str] = []
    for cl in list(concepts.keys()):
        if "chinchilla" not in cl:
            continue
        ch = concepts[cl]
        shell_name = re.sub(r"chinchilla", "Shell", ch.primary_name, flags=re.IGNORECASE)
        shell_name = re.sub(r"\s+", " ", shell_name).strip()
        shell_cl = shell_name.lower()
        if shell_cl in concepts:
            continue
        sc = Concept(shell_name)
        sc.loci = dict(ch.loci)        # 遺伝子座は Chinchilla から引き継ぐ (要確認)
        sc.synthetic = True
        sc.derived_from = ch.primary_name
        concepts[shell_cl] = sc
        synthesized_shell.append(shell_name)

    stats = {
        "name_mismatches": name_mismatches,
        "map_only": map_only,
        "synthesized_shell": synthesized_shell,
        "source_codes": set(source.keys()),
        "map_codes": set(gmap.keys()),
    }
    return concepts, stats


# ---------------------------------------------------------------------------
# 7. master 行の生成
# ---------------------------------------------------------------------------
def build_rows(concepts: dict[str, Concept]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    used_ids: set[str] = set()

    for cl in sorted(concepts):
        c = concepts[cl]
        attrs = derive_attributes(c.primary_name, c.loci)
        decision = classify(c.primary_name, attrs, c.in_map)

        color_id = make_color_id(c.primary_name)
        # ColorId 衝突回避 (理論上ほぼ起きないが安全のため)
        if color_id in used_ids:
            suffix = 2
            while f"{color_id}_{suffix}" in used_ids:
                suffix += 1
            color_id = f"{color_id}_{suffix}"
        used_ids.add(color_id)

        registry_parts = list(c.registry_notes)
        if c.paren_tags:
            registry_parts.append("団体/補足タグ: " + ", ".join(c.paren_tags))
        if decision["RegistryNotesExtra"]:
            registry_parts.append(decision["RegistryNotesExtra"])

        note_parts: list[str] = []
        if c.synthetic:
            note_parts.append(
                f"派生概念: Shell = Chinchilla 同一概念。{c.derived_from} (alias) から canonical 化。"
                "元データに直接の行は無い (SourceCode/Name は Chinchilla 側 alias 行が保持)。"
            )
        if decision["NotesExtra"]:
            note_parts.append(decision["NotesExtra"])
        if c.change_notes:
            note_parts.append("正規化: " + ", ".join(sorted(c.change_notes)))
        if not c.in_map and not c.synthetic:
            note_parts.append("遺伝子座はマップ未収載のため名前から推定。")

        aliases = sorted(c.aliases)

        # CanonicalColorId (機械可読な解決先):
        # - canonical      -> 自分自身 (ColorId)
        # - alias          -> 解決先 canonical の ColorId (Notes の resolves_to と一致)
        # - breed_specific -> 一般 canonical へ確実に解決できない限り自分自身
        #                     (一般概念へのマッピングは人間レビューに委ねる)
        # - review/excluded -> 確定不能のため空欄 (理由は Notes に記録済み)
        status = decision["Status"]
        if status == "canonical":
            canonical_id = color_id
        elif status == "alias":
            canonical_id = decision["ResolvesTo"]
        elif status == "breed_specific":
            canonical_id = color_id
        else:  # review / excluded
            canonical_id = ""

        rows.append({
            "ColorId": color_id,
            "CanonicalColorId": canonical_id,
            "Status": decision["Status"],
            "PrimaryName": c.primary_name,
            "Aliases": " | ".join(aliases),
            "RegistryNotes": " / ".join(registry_parts),
            "BreedContext": decision["BreedContext"],
            "ColorGroup": attrs["ColorGroup"],
            "BaseSeries": attrs["BaseSeries"],
            "OrangeState": attrs["OrangeState"],
            "Dilution": attrs["Dilution"],
            "AgoutiState": attrs["AgoutiState"],
            "SilverState": attrs["SilverState"],
            "WhiteState": attrs["WhiteState"],
            "PointState": attrs["PointState"],
            "PatternState": attrs["PatternState"],
            "SexRestriction": sex_restriction(c.primary_name, attrs),
            "DisplayAllowed": decision["DisplayAllowed"],
            "InputAllowed": decision["InputAllowed"],
            "OutputPriority": str(output_priority(decision["Status"], attrs)),
            "SourceCodes": " | ".join(str(x) for x in sorted(set(c.source_codes))),
            "SourceNames": " | ".join(dict.fromkeys(c.source_names)),  # 重複除去・順序保持
            "GeneticRuleSource": decision["GeneticRuleSource"],
            "Notes": " / ".join(note_parts),
        })

    # 出力順: OutputPriority 降順 → PrimaryName
    rows.sort(key=lambda r: (-int(r["OutputPriority"]), r["PrimaryName"]))
    return rows


# ---------------------------------------------------------------------------
# 8. バリデーション
# ---------------------------------------------------------------------------
def validate(rows: list[dict[str, str]], source_codes: set[int]) -> list[str]:
    errors: list[str] = []
    seen_ids: set[str] = set()
    allowed_status = {"canonical", "alias", "breed_specific", "excluded", "review"}
    allowed_sex = {"unrestricted", "female_only", "male_only"}
    snake = re.compile(r"^[a-z0-9_]+$")

    all_ids = {r["ColorId"] for r in rows}
    canonical_ids = {r["ColorId"] for r in rows if r["Status"] == "canonical"}

    for r in rows:
        cid = r["ColorId"]
        if cid in seen_ids:
            errors.append(f"ColorId 重複: {cid}")
        seen_ids.add(cid)
        if not snake.match(cid):
            errors.append(f"ColorId が snake_case でない: {cid}")
        if not r["PrimaryName"]:
            errors.append(f"PrimaryName 空: {cid}")
        if r["Status"] not in allowed_status:
            errors.append(f"Status 不正: {cid} -> {r['Status']}")
        if r["DisplayAllowed"] not in ("true", "false"):
            errors.append(f"DisplayAllowed 不正: {cid}")
        if r["InputAllowed"] not in ("true", "false"):
            errors.append(f"InputAllowed 不正: {cid}")
        if r["SexRestriction"] not in allowed_sex:
            errors.append(f"SexRestriction 不正: {cid} -> {r['SexRestriction']}")
        # SourceNames は SourceCodes を持つ行 (= 元データ直結の行) でのみ必須。
        # 派生 canonical (Shell 合成行) は元データ直結ではないため空欄可。ただし Notes に由来を要記録。
        if r["SourceCodes"] and not r["SourceNames"]:
            errors.append(f"SourceNames 空 (元データ名喪失): {cid}")
        if not r["SourceCodes"] and not r["SourceNames"] and not r["Notes"]:
            errors.append(f"元データ直結でない行に由来 Notes が無い: {cid}")
        # breed_specific で DisplayAllowed=true は Notes に理由が必要
        if r["Status"] == "breed_specific" and r["DisplayAllowed"] == "true" and "理由" not in r["Notes"]:
            errors.append(f"breed_specific なのに DisplayAllowed=true (理由未記載): {cid}")

        # --- CanonicalColorId 検証 ---
        canon = r["CanonicalColorId"]
        if r["Status"] == "alias":
            # V1: alias は CanonicalColorId 必須
            if not canon:
                errors.append(f"alias に CanonicalColorId が無い: {cid}")
            else:
                # V2: 実在する ColorId を参照
                if canon not in all_ids:
                    errors.append(f"alias の CanonicalColorId が実在しない: {cid} -> {canon}")
                # V3: 参照先は原則 canonical
                elif canon not in canonical_ids:
                    errors.append(f"alias の CanonicalColorId 参照先が canonical でない: {cid} -> {canon}")
        elif r["Status"] == "canonical":
            # V4: canonical は自分自身
            if canon != cid:
                errors.append(f"canonical の CanonicalColorId が自分自身でない: {cid} -> {canon}")
        elif r["Status"] == "breed_specific":
            # breed_specific は自分自身 または実在 ColorId
            if canon and canon not in all_ids:
                errors.append(f"breed_specific の CanonicalColorId が実在しない: {cid} -> {canon}")
        else:  # review / excluded
            # 空欄可。空欄でない場合は実在を要求
            if canon and canon not in all_ids:
                errors.append(f"{r['Status']} の CanonicalColorId が実在しない: {cid} -> {canon}")
            # 空欄なら Notes に理由 (review/excluded は分類時に理由を必ず付与済み)
            if not canon and not r["Notes"]:
                errors.append(f"{r['Status']} で CanonicalColorId 空欄かつ Notes 理由なし: {cid}")

        # V7: breed_specific は通常表示に混ざらない (DisplayAllowed=false)
        if r["Status"] == "breed_specific" and r["DisplayAllowed"] != "false":
            errors.append(f"breed_specific が通常表示可能 (DisplayAllowed!=false): {cid}")

        # V8: Any という語が「自分で付与する分類値カラム」に残っていないか。
        # 元データ名 (PrimaryName/Aliases/SourceNames/RegistryNotes/Notes) に含まれる
        # "Any Other Color" 等は元データ保持のため対象外 (依頼プロンプト: 元データ名を失わない)。
        taxonomy_cols = (
            "Status", "BreedContext", "ColorGroup", "BaseSeries", "OrangeState",
            "Dilution", "AgoutiState", "SilverState", "WhiteState", "PointState",
            "PatternState", "SexRestriction", "GeneticRuleSource",
        )
        joined = " ".join(r[col] for col in taxonomy_cols)
        if re.search(r"\bAny\b", joined):
            errors.append(f"分類値カラムに 'Any' が残存: {cid}")

    # V5/V6: 元データ全 Code が少なくとも 1 行に保持されている (元データ行の完全喪失なし)
    covered: set[int] = set()
    for r in rows:
        for token in r["SourceCodes"].split(" | "):
            token = token.strip()
            if token.isdigit():
                covered.add(int(token))
    missing = source_codes - covered
    for code in sorted(missing):
        errors.append(f"元データ Code が master に保持されていない (喪失): {code}")

    return errors


# ---------------------------------------------------------------------------
# 9. 出力
# ---------------------------------------------------------------------------
def write_master(rows: list[dict[str, str]]) -> None:
    with open(OUT_MASTER, mode="w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=MASTER_COLUMNS)
        writer.writeheader()
        for r in rows:
            writer.writerow(r)


def write_review(rows, concepts, stats, source, gmap) -> None:
    by_status: dict[str, list[dict[str, str]]] = {}
    for r in rows:
        by_status.setdefault(r["Status"], []).append(r)

    def names_of(status: str) -> list[str]:
        return [f"{r['PrimaryName']} (`{r['ColorId']}`)" for r in by_status.get(status, [])]

    normalized_rows = [r for r in rows if "正規化:" in r["Notes"]]
    review_required = [r for r in rows if r["GeneticRuleSource"] == "review_required"]
    aliases = by_status.get("alias", [])
    breed_specific = by_status.get("breed_specific", [])

    # CanonicalColorId / カバレッジ統計
    all_ids = {r["ColorId"] for r in rows}
    alias_resolved = [r for r in aliases if r["CanonicalColorId"]]
    alias_unresolved = [r for r in aliases if not r["CanonicalColorId"] or r["CanonicalColorId"] not in all_ids]
    covered_codes: set[int] = set()
    for r in rows:
        for token in r["SourceCodes"].split(" | "):
            token = token.strip()
            if token.isdigit():
                covered_codes.add(int(token))
    src_total = len(source)
    src_covered = len(set(source.keys()) & covered_codes)

    lines: list[str] = []
    a = lines.append
    a("# cat_color_master.csv レビューレポート")
    a("")
    a("> 自動生成: `scripts/build_cat_color_master.py`。人間レビュー用。数値・一覧はビルド時点のもの。")
    a("")
    a("## 0. 設計確定事項")
    a("")
    a("- **別名は独立行**で保持する (ユーザー確定)。各 alias は固有 `ColorId` + `Status=alias` を持ち、`Notes` に `resolves_to=<canonical_color_id>` を記録する。")
    a("- 1 行 = 1 色柄概念。`ColorId` は一意。`SourceCodes` / `SourceNames` に元データの全コード・全名を保持し、元データ名を失わない。")
    a("- `Any` は仕様値・モード名として使用しない (`breed_unselected` / `no_breed_filter` / `normal_mode` / `general` / `unrestricted` 等)。")
    a("")
    a("## 1. 件数サマリー")
    a("")
    a(f"- 元データ件数 (色柄データUTF8Ver.csv, 名前あり): **{len(source)}**")
    a(f"- 現行正本件数 (cat_color_genetic_map.csv): **{len(gmap)}**")
    a(f"- 生成した色柄概念 (ColorId) 件数: **{len(rows)}**")
    a("")
    a("| Status | 件数 |")
    a("|---|---|")
    for st in ("canonical", "alias", "breed_specific", "excluded", "review"):
        a(f"| {st} | {len(by_status.get(st, []))} |")
    a(f"| **合計** | **{len(rows)}** |")
    a("")
    a(f"- `GeneticRuleSource=review_required` (遺伝子ルール要確認): **{len(review_required)}** 件")
    a(f"- 正規化 (略称・タイポ展開) を適用した概念: **{len(normalized_rows)}** 件")
    a("")
    a("### 1.1 CanonicalColorId と元データカバレッジ")
    a("")
    a(f"- alias 解決件数 (`Status=alias` かつ `CanonicalColorId` あり): **{len(alias_resolved)} / {len(aliases)}**")
    a(f"- alias 解決先が存在しない行数 (`CanonicalColorId` が空 or 実在しない): **{len(alias_unresolved)}**" + ("" if not alias_unresolved else " ← 要修正"))
    a(f"- 元データ {src_total} 件のカバレッジ (SourceCode が master のいずれかの行に保持): **{src_covered} / {src_total}** ({'100%' if src_covered == src_total else f'{src_covered / src_total * 100:.1f}%'})")
    a("")
    a("**CanonicalColorId を追加した理由**: alias の解決先をこれまで `Notes` の `resolves_to=` という人間用メモに持たせていたが、機械可読な唯一正本としては危険 (パース依存・欠落検出不能)。`Notes` は人間用メモへ戻し、alias 解決に必要な情報は専用カラム `CanonicalColorId` に分離した。機械処理は必ず `CanonicalColorId` を参照する。`canonical` は自分自身、`alias` は解決先 canonical、`breed_specific` は原則自分自身、`review`/`excluded` は確定不能なら空欄 (理由は `Notes`)。")
    a("")

    a("## 2. 差分: 元データ ↔ 現行正本")
    a("")
    src_codes = stats["source_codes"]
    map_codes = stats["map_codes"]
    only_source = sorted(src_codes - map_codes)
    only_map = sorted(map_codes - src_codes)
    a(f"### 2.1 元データにあるが現行マップに無い Code ({len(only_source)})")
    a("")
    a(", ".join(f"{c}:{source.get(c, '')}" for c in only_source) or "(なし)")
    a("")
    a(f"### 2.2 現行マップにあるが元データに無い Code ({len(only_map)})")
    a("")
    a(", ".join(f"{c}:{gmap[c].get('CoatColor','')}" for c in only_map) or "(なし)")
    a("")
    a(f"### 2.3 Code 一致だが名前不一致 ({len(stats['name_mismatches'])})")
    a("")
    if stats["name_mismatches"]:
        a("| Code | 元データ名 | マップ名 |")
        a("|---|---|---|")
        for code, sname, mname in stats["name_mismatches"]:
            a(f"| {code} | {sname} | {mname} |")
    else:
        a("(なし)")
    a("")
    a(f"### 2.4 マップのみに存在する色柄 ({len(stats['map_only'])})")
    a("")
    a(", ".join(f"{c}:{n}" for c, n in stats["map_only"]) or "(なし)")
    a("")

    a("## 3. 同一概念として統合した別名 (alias)")
    a("")
    a("| PrimaryName | CanonicalColorId | RegistryNotes |")
    a("|---|---|---|")
    for r in aliases:
        a(f"| {r['PrimaryName']} | `{r['CanonicalColorId']}` | {r['RegistryNotes']} |")
    a("")

    a("## 4. 猫種固有呼称として分離 (breed_specific)")
    a("")
    by_breed: dict[str, list[str]] = {}
    for r in breed_specific:
        by_breed.setdefault(r["BreedContext"], []).append(r["PrimaryName"])
    for breed in sorted(by_breed):
        a(f"- **{breed}** ({len(by_breed[breed])}): " + ", ".join(sorted(by_breed[breed])))
    a("")

    a("## 5. タイポ・略称として正規化した色柄")
    a("")
    a("| PrimaryName | SourceNames | 正規化内容 |")
    a("|---|---|---|")
    for r in normalized_rows:
        m = re.search(r"正規化: ([^/]+)", r["Notes"])
        # SourceNames の `|` 区切りは markdown 表の列区切りと衝突するため `,` に置換して表示
        src = r["SourceNames"].replace(" | ", ", ")
        a(f"| {r['PrimaryName']} | {src} | {m.group(1).strip() if m else ''} |")
    a("")

    a("## 6. review にした色柄")
    a("")
    a(", ".join(names_of("review")) or "(なし)")
    a("")
    a("## 7. excluded にした色柄")
    a("")
    a(", ".join(names_of("excluded")) or "(なし)")
    a("")

    a("## 8. 遺伝子ルールがまだ不確かな項目 (GeneticRuleSource=review_required)")
    a("")
    a(f"計 {len(review_required)} 件。代表: ")
    a(", ".join(f"{r['PrimaryName']}" for r in review_required[:60]) + (" ..." if len(review_required) > 60 else ""))
    a("")

    a("## 9. 判断の根拠と不確かな点")
    a("")
    a("- **Pt の扱い**: 元データの `Pt` は全て Tabby 文脈であり `Patched` と解釈した (例: `Blue Pt Tabby-White` → `Blue Patched Tabby-White`)。`Point` は `Point` と明示された名のみ Point 系とした。各行 `Notes` に正規化内容を残している。")
    a("- **CFA/TICA 差**: `Blue Cream`=`Blue Tortie`, `Lilac Cream`=`Lilac Tortie`, `Tortoiseshell-White`/`Mike Tri Color`=`Calico`, `Blue Tortie-White`/`Blue Cream-White`=`Dilute Calico`, `Torbie`=`Patched Tabby` を同一概念の alias として統合した。")
    a("- **猫種固有呼称**: Ruddy/Sorrel(Aby), Sable/Champagne/Platinum/Sepia(Burmese), 各種 Mink(Tonkinese), Ebony/Chestnut/Lavender(Oriental), Leopard/Snow/Marble(Bengal), Mitted/Bi-Color(Ragdoll) を breed_specific とし `DisplayAllowed=false`。")
    a("- **白斑**: `Van`(S/S) は一般表示で `-White` に正規化する方針のため `DisplayAllowed=false`。`Mitted`/`Bi-Color` も同様に一般非表示。")
    a("- **遺伝子座**: マップに同一 Code・同一名で存在する座のみ `current_map` として取り込み、それ以外は名前から `inferred`。Point/Mink/Sepia/Shaded/WideBand 系と alias/breed_specific は `review_required`。")
    a("- **既知のマップ不整合 (要確認)**: `Blue Cream`(code31) はマップ上 `O/O` (ホモ接合オレンジ) だがトーティは `O/o` のはず。master では `OrangeState=tortie` に補正した。エンジン側 CSV は本タスクでは変更していない。")
    a("- **未確定で review に残したもの**: 単独 `Smoke`、`Calico Smoke`/`Smoke Calico`/`Smoke Dilute Calico` 等のスモーク×トーティ/キャリコ、`Shell Cream`/`Shell Blue`/`Cream Shell Cameo` 等の基色不明な Shell 系。")
    a("")
    a("### 9.1 追加レビュー判断 (2026-06-24 反映)")
    a("")
    a("1. **Peke-Face / P-F**: 形態・タイプ由来語で色柄概念ではない。canonical にせず、`Peke-Face` を除去した汎用カラーへ alias 解決 (例: `Peke-Face Red`→`red`, `Peke-Face Red Tabby`→`red_tabby`)。`DisplayAllowed=false`、旧データ互換のため `InputAllowed=true`。")
    a("2. **Chinchilla / Shell**: 同一概念。canonical は Shell 側に寄せ、`Chinchilla *` は alias とし `CanonicalColorId` を対応 Shell へ向ける (例: `Chinchilla Silver`→`shell_silver`, `Blue Chinchilla Silver`→`blue_shell_silver`)。元データに無い Shell 側 canonical は派生合成し、由来を Notes に記録 (SourceCode/Name は Chinchilla alias 行が保持)。")
    a("3. **Shaded**: Shell/Chinchilla とは tipping 量が異なる別概念として canonical 維持。`GeneticRuleSource=review_required` を維持 (`Shaded Chocolate`/`Shaded Tortie` 等も review から canonical へ移動)。")
    a("4. **Golden**: 単なる non_silver ではなく non_silver + agouti + wideband/tipping 系概念。`i/i` のみ・`Wb/-` のみでは確定しない。`SilverState=non_silver`・`AgoutiState=agouti` に補正し `GeneticRuleSource=review_required` を維持。")
    a("5. **Smoke**: Shell/Shaded/Chinchilla/Golden(Wb系) とは別系統。`solid(a/a) + inhibitor I/-` の概念として `AgoutiState=solid`・`SilverState=smoke` に固定。")
    a("")
    a("## 10. 今後人間がレビューすべきポイント")
    a("")
    a("1. `review` 行を canonical / alias / breed_specific のいずれへ確定するか。")
    a("2. `review_required` の遺伝子座 (特に Wb 系 Shaded/Chinchilla/Golden、Point/Mink/Sepia の C 系)。")
    a("3. alias の `CanonicalColorId` 解決先が妥当か (特に Torbie→Patched Tabby のパターン語処理)。")
    a("4. breed_specific の BreedContext 割り当て (Oriental/Burmese/Tonkinese の境界)。")
    a("5. `Tortoiseshell-White` を `Calico` へ寄せた判断 (CFA は白量で区別する場合あり)。")
    a("")

    with open(OUT_REVIEW, mode="w", encoding="utf-8", newline="") as f:
        f.write("\n".join(lines))


# ---------------------------------------------------------------------------
# 10. main
# ---------------------------------------------------------------------------
def main() -> int:
    source = load_source_colors()
    gmap = load_genetic_map()
    concepts, stats = build_concepts(source, gmap)
    rows = build_rows(concepts)

    errors = validate(rows, set(source.keys()))
    write_master(rows)
    write_review(rows, concepts, stats, source, gmap)

    print(f"元データ件数: {len(source)}")
    print(f"現行マップ件数: {len(gmap)}")
    print(f"生成概念 (行) 件数: {len(rows)}")
    status_count: dict[str, int] = {}
    for r in rows:
        status_count[r["Status"]] = status_count.get(r["Status"], 0) + 1
    for st in ("canonical", "alias", "breed_specific", "excluded", "review"):
        print(f"  {st}: {status_count.get(st, 0)}")
    print(f"review_required (遺伝子ルール要確認): {sum(1 for r in rows if r['GeneticRuleSource'] == 'review_required')}")
    print(f"出力: {OUT_MASTER}")
    print(f"出力: {OUT_REVIEW}")

    if errors:
        print("\n[バリデーションエラー]")
        for e in errors:
            print("  - " + e)
        return 1
    print("\nバリデーション: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
