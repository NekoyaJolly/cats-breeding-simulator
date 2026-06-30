#!/usr/bin/env python3
"""猫種なし normal モードの親色総当たり監査ツール。

通常の pytest / CI には入れず、時間があるときに手動実行して、計算不能・未分類・
不可逆ルール違反などをまとめて抽出するための診断スクリプト。
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from cat_breeding_simulator.color_master import COLOR_MASTER, ResolvedColor
from cat_breeding_simulator.engine import (
    BreedingCalculationError,
    CalculationReport,
    CoatColorCalculator,
    KittenResult,
)


DEFAULT_OUTPUT_DIR = REPO_ROOT / ".artifacts" / "exhaustive-cross-audit" / "latest"
MODE = "normal"
BREED = None
TOTAL_TOLERANCE = 0.01
ACCOUNTING_TOLERANCE = 0.05
FEMALE_ONLY_TOKENS = (
    "Tortie",
    "Tortoiseshell",
    "Calico",
    "Blue Cream",
    "Lilac Cream",
    "Patched",
)
SILVER_TOKENS = ("Silver", "Smoke", "Cameo", "Chinchilla", "Shaded", "Shell")
WHITE_SPOTTING_TOKENS = ("-White", " Van", " Bi-Color", " Mitted")


@dataclass(frozen=True, slots=True)
class AuditIssue:
    """監査で検出した違反または要確認事項。"""

    issue_type: str
    sire_color: str
    dam_color: str
    sex: str = ""
    color: str = ""
    probability_pct: str = ""
    detail: str = ""


@dataclass(frozen=True, slots=True)
class SkippedInput:
    """猫種なし normal では親入力として使えなかった色。"""

    parent: str
    color: str
    status: str
    breed_context: str
    reason: str


@dataclass(frozen=True, slots=True)
class ParentInputSets:
    """父・母それぞれの監査対象色と、対象外になった色。"""

    sire_colors: list[str]
    dam_colors: list[str]
    skipped_inputs: list[SkippedInput]


@dataclass(frozen=True, slots=True)
class AuditOptions:
    """監査実行オプション。"""

    output_dir: Path
    sire_filters: tuple[str, ...]
    dam_filters: tuple[str, ...]
    offset: int
    limit: int | None
    fail_fast: bool
    progress_every: int
    fail_on_suspicious: bool


def parse_args() -> AuditOptions:
    """CLI 引数を監査オプションへ変換する。"""

    parser = argparse.ArgumentParser(
        description=(
            "猫種なし normal モードで、親入力として有効な父色 x 母色を総当たり監査します。"
        )
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="監査結果の出力先。既定: .artifacts/exhaustive-cross-audit/latest",
    )
    parser.add_argument(
        "--sire",
        action="append",
        default=[],
        help="父色を完全一致で絞り込みます。複数指定可。",
    )
    parser.add_argument(
        "--dam",
        action="append",
        default=[],
        help="母色を完全一致で絞り込みます。複数指定可。",
    )
    parser.add_argument(
        "--offset",
        type=int,
        default=0,
        help="総当たり順の開始位置。長時間監査の分割実行に使います。",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="監査する組合せ数の上限。未指定なら全件。",
    )
    parser.add_argument(
        "--fail-fast",
        action="store_true",
        help="最初の違反を検出した時点で監査を停止します。",
    )
    parser.add_argument(
        "--progress-every",
        type=int,
        default=1000,
        help="進捗ログを出す間隔。0 で無効化します。",
    )
    parser.add_argument(
        "--fail-on-suspicious",
        action="store_true",
        help="要確認事項だけでも終了コードを 1 にします。",
    )
    args = parser.parse_args()

    if args.offset < 0:
        parser.error("--offset は 0 以上で指定してください。")
    if args.limit is not None and args.limit <= 0:
        parser.error("--limit は 1 以上で指定してください。")
    if args.progress_every < 0:
        parser.error("--progress-every は 0 以上で指定してください。")

    return AuditOptions(
        output_dir=args.out_dir,
        sire_filters=tuple(args.sire),
        dam_filters=tuple(args.dam),
        offset=args.offset,
        limit=args.limit,
        fail_fast=args.fail_fast,
        progress_every=args.progress_every,
        fail_on_suspicious=args.fail_on_suspicious,
    )


def build_parent_input_sets(calculator: CoatColorCalculator) -> ParentInputSets:
    """UI/API と同じ入力候補から、猫種なし normal で親に使える色だけを抽出する。"""

    sire_colors: list[str] = []
    dam_colors: list[str] = []
    skipped_inputs: list[SkippedInput] = []

    for option in COLOR_MASTER.list_input_colors():
        for parent, sex, target in (
            ("sire", "male", sire_colors),
            ("dam", "female", dam_colors),
        ):
            try:
                calculator.validate_parent_color(option.value, sex, BREED, MODE)
            except BreedingCalculationError as error:
                skipped_inputs.append(
                    SkippedInput(
                        parent=parent,
                        color=option.value,
                        status=option.status,
                        breed_context=option.breed_context,
                        reason=str(error),
                    )
                )
                continue
            target.append(option.value)

    return ParentInputSets(
        sire_colors=sire_colors,
        dam_colors=dam_colors,
        skipped_inputs=skipped_inputs,
    )


def apply_filters(colors: list[str], filters: tuple[str, ...], label: str) -> list[str]:
    """完全一致フィルタを適用し、指定ミスは早期に知らせる。"""

    if not filters:
        return colors

    available = set(colors)
    missing = [color for color in filters if color not in available]
    if missing:
        raise SystemExit(
            f"{label} フィルタに、猫種なし normal の親入力として使えない色があります: "
            + ", ".join(missing)
        )
    return [color for color in colors if color in set(filters)]


def iter_pairs(
    sire_colors: list[str],
    dam_colors: list[str],
    offset: int,
    limit: int | None,
):
    """父色 x 母色の総当たりを、offset / limit 付きで順序安定に列挙する。"""

    index = 0
    yielded = 0
    for sire_color in sire_colors:
        for dam_color in dam_colors:
            if index < offset:
                index += 1
                continue
            if limit is not None and yielded >= limit:
                return
            yield index, sire_color, dam_color
            index += 1
            yielded += 1


def allele_pair_is(loci: dict[str, tuple[str, str]] | None, locus: str, allele: str) -> bool:
    """指定座位が `allele/allele` で固定されているかを判定する。"""

    return loci is not None and loci.get(locus) == (allele, allele)


def allele_pair_has(loci: dict[str, tuple[str, str]] | None, locus: str, allele: str) -> bool:
    """指定座位に `allele` が含まれるかを判定する。"""

    return loci is not None and allele in loci.get(locus, ())


def result_loci(
    calculator: CoatColorCalculator,
    result: KittenResult,
    cache: dict[tuple[str, str], dict[str, tuple[str, str]] | None],
) -> dict[str, tuple[str, str]] | None:
    """結果色を座位へ解決する。大量実行で同じ結果名が出るためキャッシュする。"""

    sex = "male" if result.sex == "Male" else "female"
    key = (result.color, sex)
    if key not in cache:
        try:
            cache[key] = calculator.resolved_color_loci(result.color, sex, BREED)
        except BreedingCalculationError:
            cache[key] = None
    return cache[key]


def resolved_output(color: str) -> ResolvedColor | None:
    """出力色名を色柄マスターで解決する。"""

    return COLOR_MASTER.resolve(color)


def has_token(value: str, tokens: tuple[str, ...]) -> bool:
    """色名に監査用トークンが含まれるかを判定する。"""

    return any(token in value for token in tokens)


def validate_report(
    calculator: CoatColorCalculator,
    sire_color: str,
    dam_color: str,
    report: CalculationReport,
    loci_cache: dict[tuple[str, str], dict[str, tuple[str, str]] | None],
) -> tuple[list[AuditIssue], list[AuditIssue]]:
    """1交配レポートの不変条件を検証する。"""

    failures: list[AuditIssue] = []
    suspicious: list[AuditIssue] = []
    total_probability = round(sum(result.probability_pct for result in report.results), 4)
    matched_plus_unmatched = report.matched_probability + report.unmatched_probability

    if not report.results:
        failures.append(
            AuditIssue(
                issue_type="empty_results",
                sire_color=sire_color,
                dam_color=dam_color,
                detail="結果が空です。",
            )
        )

    if report.unmatched_probability > 0:
        failures.append(
            AuditIssue(
                issue_type="unmatched_probability",
                sire_color=sire_color,
                dam_color=dam_color,
                probability_pct=f"{report.unmatched_probability * 100:.4f}",
                detail=(
                    f"未分類率 {report.unmatched_probability:.6f}, "
                    f"未分類数 {report.unmatched_genotype_count}"
                ),
            )
        )

    if report.unmatched_probability == 0 and abs(total_probability - 100.0) > TOTAL_TOLERANCE:
        failures.append(
            AuditIssue(
                issue_type="probability_total_not_100",
                sire_color=sire_color,
                dam_color=dam_color,
                probability_pct=f"{total_probability:.4f}",
                detail="未分類ゼロなのに表示確率合計が100%ではありません。",
            )
        )

    accounted_probability = total_probability + round(report.unmatched_probability * 100, 4)
    if abs(accounted_probability - 100.0) > ACCOUNTING_TOLERANCE:
        failures.append(
            AuditIssue(
                issue_type="probability_accounting_mismatch",
                sire_color=sire_color,
                dam_color=dam_color,
                probability_pct=f"{accounted_probability:.4f}",
                detail="表示確率合計 + 未分類率 が100%と整合しません。",
            )
        )

    if abs(matched_plus_unmatched - 1.0) > 0.0001:
        failures.append(
            AuditIssue(
                issue_type="matched_unmatched_not_1",
                sire_color=sire_color,
                dam_color=dam_color,
                detail=f"matched + unmatched = {matched_plus_unmatched:.6f}",
            )
        )

    seen_results: set[tuple[str, str]] = set()
    sire_loci = calculator.resolved_color_loci(sire_color, "male", BREED)
    dam_loci = calculator.resolved_color_loci(dam_color, "female", BREED)

    if sire_loci is None:
        suspicious.append(
            AuditIssue(
                issue_type="sire_loci_unresolved",
                sire_color=sire_color,
                dam_color=dam_color,
                detail="父色の基準座位を解決できません。",
            )
        )
    if dam_loci is None:
        suspicious.append(
            AuditIssue(
                issue_type="dam_loci_unresolved",
                sire_color=sire_color,
                dam_color=dam_color,
                detail="母色の基準座位を解決できません。",
            )
        )

    parents_dilute = allele_pair_is(sire_loci, "D", "d") and allele_pair_is(dam_loci, "D", "d")
    parents_non_silver = allele_pair_is(sire_loci, "I", "i") and allele_pair_is(dam_loci, "I", "i")
    parents_no_spotting = allele_pair_is(sire_loci, "S", "s") and allele_pair_is(dam_loci, "S", "s")
    parents_no_dominant_white = allele_pair_is(sire_loci, "W", "w") and allele_pair_is(dam_loci, "W", "w")
    parents_point = allele_pair_is(sire_loci, "C", "cs") and allele_pair_is(dam_loci, "C", "cs")

    for result in report.results:
        result_key = (result.sex, result.color)
        if result_key in seen_results:
            failures.append(
                AuditIssue(
                    issue_type="duplicate_result",
                    sire_color=sire_color,
                    dam_color=dam_color,
                    sex=result.sex,
                    color=result.color,
                    detail="同一 sex/color の結果が重複しています。",
                )
            )
        seen_results.add(result_key)

        if result.probability_pct <= 0:
            failures.append(
                AuditIssue(
                    issue_type="non_positive_probability",
                    sire_color=sire_color,
                    dam_color=dam_color,
                    sex=result.sex,
                    color=result.color,
                    probability_pct=f"{result.probability_pct:.4f}",
                    detail="0%以下の結果が表示されています。",
                )
            )

        resolved = resolved_output(result.color)
        if resolved is None:
            suspicious.append(
                AuditIssue(
                    issue_type="output_color_not_in_master",
                    sire_color=sire_color,
                    dam_color=dam_color,
                    sex=result.sex,
                    color=result.color,
                    probability_pct=f"{result.probability_pct:.4f}",
                    detail="出力色を cat_color_master.csv で解決できません。",
                )
            )
        else:
            if result.sex == "Male" and resolved.sex_restriction == "female_only":
                failures.append(
                    AuditIssue(
                        issue_type="female_only_color_on_male",
                        sire_color=sire_color,
                        dam_color=dam_color,
                        sex=result.sex,
                        color=result.color,
                        probability_pct=f"{result.probability_pct:.4f}",
                        detail="オス結果にメス限定カラーが出ています。",
                    )
                )
            if resolved.status == "breed_specific":
                failures.append(
                    AuditIssue(
                        issue_type="breed_specific_output_without_breed",
                        sire_color=sire_color,
                        dam_color=dam_color,
                        sex=result.sex,
                        color=result.color,
                        probability_pct=f"{result.probability_pct:.4f}",
                        detail=f"猫種なし結果に猫種固有色 ({resolved.breed_context}) が出ています。",
                    )
                )
            if resolved.status in ("excluded", "review") or not resolved.display_allowed:
                failures.append(
                    AuditIssue(
                        issue_type="display_disallowed_output",
                        sire_color=sire_color,
                        dam_color=dam_color,
                        sex=result.sex,
                        color=result.color,
                        probability_pct=f"{result.probability_pct:.4f}",
                        detail="通常表示できない区分の色が出力されています。",
                    )
                )

        if result.sex == "Male" and has_token(result.color, FEMALE_ONLY_TOKENS):
            failures.append(
                AuditIssue(
                    issue_type="female_only_token_on_male",
                    sire_color=sire_color,
                    dam_color=dam_color,
                    sex=result.sex,
                    color=result.color,
                    probability_pct=f"{result.probability_pct:.4f}",
                    detail="オス結果にメス限定系の語が含まれています。",
                )
            )

        loci = result_loci(calculator, result, loci_cache)
        if loci is None:
            continue

        if parents_dilute and allele_pair_has(loci, "D", "D"):
            failures.append(
                AuditIssue(
                    issue_type="dense_from_dilute_parents",
                    sire_color=sire_color,
                    dam_color=dam_color,
                    sex=result.sex,
                    color=result.color,
                    probability_pct=f"{result.probability_pct:.4f}",
                    detail="d/d x d/d から D を含む濃色結果が出ています。",
                )
            )
        if parents_non_silver and (
            allele_pair_has(loci, "I", "I") or has_token(result.color, SILVER_TOKENS)
        ):
            failures.append(
                AuditIssue(
                    issue_type="silver_from_non_silver_parents",
                    sire_color=sire_color,
                    dam_color=dam_color,
                    sex=result.sex,
                    color=result.color,
                    probability_pct=f"{result.probability_pct:.4f}",
                    detail="i/i x i/i から Silver/Smoke/Cameo 系が出ています。",
                )
            )
        if parents_no_spotting and (
            allele_pair_has(loci, "S", "S") or has_token(result.color, WHITE_SPOTTING_TOKENS)
        ):
            failures.append(
                AuditIssue(
                    issue_type="white_spotting_from_non_spotted_parents",
                    sire_color=sire_color,
                    dam_color=dam_color,
                    sex=result.sex,
                    color=result.color,
                    probability_pct=f"{result.probability_pct:.4f}",
                    detail="s/s x s/s から白斑系結果が出ています。",
                )
            )
        if parents_no_dominant_white and allele_pair_has(loci, "W", "W"):
            failures.append(
                AuditIssue(
                    issue_type="dominant_white_from_non_white_parents",
                    sire_color=sire_color,
                    dam_color=dam_color,
                    sex=result.sex,
                    color=result.color,
                    probability_pct=f"{result.probability_pct:.4f}",
                    detail="w/w x w/w から W を含む優性白結果が出ています。",
                )
            )
        if parents_point and not allele_pair_is(loci, "C", "cs"):
            failures.append(
                AuditIssue(
                    issue_type="full_color_from_point_parents",
                    sire_color=sire_color,
                    dam_color=dam_color,
                    sex=result.sex,
                    color=result.color,
                    probability_pct=f"{result.probability_pct:.4f}",
                    detail="cs/cs x cs/cs から Point 以外の C 座位結果が出ています。",
                )
            )

    return failures, suspicious


def write_csv(path: Path, rows: list[object], fieldnames: list[str]) -> None:
    """Excel 等でも開きやすい UTF-8 BOM 付き CSV を出力する。"""

    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(asdict(row))


def write_outputs(
    options: AuditOptions,
    summary: dict[str, object],
    failures: list[AuditIssue],
    suspicious: list[AuditIssue],
    skipped_inputs: list[SkippedInput],
) -> None:
    """監査結果を .artifacts 配下へ出力する。"""

    options.output_dir.mkdir(parents=True, exist_ok=True)
    issue_fields = [
        "issue_type",
        "sire_color",
        "dam_color",
        "sex",
        "color",
        "probability_pct",
        "detail",
    ]
    skipped_fields = ["parent", "color", "status", "breed_context", "reason"]
    write_csv(options.output_dir / "failures.csv", failures, issue_fields)
    write_csv(options.output_dir / "suspicious.csv", suspicious, issue_fields)
    write_csv(options.output_dir / "skipped_inputs.csv", skipped_inputs, skipped_fields)
    (options.output_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def run_audit(options: AuditOptions) -> int:
    """監査を実行し、違反があれば終了コード 1 を返す。"""

    started = time.perf_counter()
    started_at = datetime.now(timezone.utc).isoformat()
    calculator = CoatColorCalculator()
    parent_sets = build_parent_input_sets(calculator)
    sire_colors = apply_filters(parent_sets.sire_colors, options.sire_filters, "父色")
    dam_colors = apply_filters(parent_sets.dam_colors, options.dam_filters, "母色")
    total_available_pairs = len(sire_colors) * len(dam_colors)

    if total_available_pairs == 0:
        raise SystemExit("監査対象の親色組合せがありません。")
    if options.offset >= total_available_pairs:
        raise SystemExit(
            f"--offset が総組合せ数を超えています: offset={options.offset}, total={total_available_pairs}"
        )

    planned_pairs = total_available_pairs - options.offset
    if options.limit is not None:
        planned_pairs = min(planned_pairs, options.limit)

    failures: list[AuditIssue] = []
    suspicious: list[AuditIssue] = []
    loci_cache: dict[tuple[str, str], dict[str, tuple[str, str]] | None] = {}
    audited_pairs = 0

    print(
        "監査開始: "
        f"mode={MODE}, breed=None, sire={len(sire_colors)}, dam={len(dam_colors)}, "
        f"planned_pairs={planned_pairs}"
    )

    for _, sire_color, dam_color in iter_pairs(
        sire_colors, dam_colors, options.offset, options.limit
    ):
        audited_pairs += 1
        try:
            report = calculator.calculate_report(sire_color, dam_color, BREED, MODE)
        except BreedingCalculationError as error:
            failures.append(
                AuditIssue(
                    issue_type="calculation_error",
                    sire_color=sire_color,
                    dam_color=dam_color,
                    detail=str(error),
                )
            )
            if options.fail_fast:
                break
            continue

        pair_failures, pair_suspicious = validate_report(
            calculator, sire_color, dam_color, report, loci_cache
        )
        failures.extend(pair_failures)
        suspicious.extend(pair_suspicious)

        if options.fail_fast and pair_failures:
            break
        if options.progress_every and audited_pairs % options.progress_every == 0:
            print(
                f"進捗: {audited_pairs}/{planned_pairs} "
                f"failures={len(failures)} suspicious={len(suspicious)}"
            )

    elapsed_seconds = round(time.perf_counter() - started, 3)
    finished_at = datetime.now(timezone.utc).isoformat()
    exit_code = 1 if failures or (options.fail_on_suspicious and suspicious) else 0
    summary: dict[str, object] = {
        "mode": MODE,
        "breed": BREED,
        "started_at": started_at,
        "finished_at": finished_at,
        "elapsed_seconds": elapsed_seconds,
        "sire_color_count": len(sire_colors),
        "dam_color_count": len(dam_colors),
        "skipped_input_count": len(parent_sets.skipped_inputs),
        "total_available_pairs": total_available_pairs,
        "offset": options.offset,
        "limit": options.limit,
        "planned_pairs": planned_pairs,
        "audited_pairs": audited_pairs,
        "failure_count": len(failures),
        "suspicious_count": len(suspicious),
        "fail_fast": options.fail_fast,
        "fail_on_suspicious": options.fail_on_suspicious,
        "output_dir": str(options.output_dir),
        "exit_code": exit_code,
    }
    write_outputs(options, summary, failures, suspicious, parent_sets.skipped_inputs)
    print(
        "監査完了: "
        f"audited={audited_pairs}, failures={len(failures)}, "
        f"suspicious={len(suspicious)}, elapsed={elapsed_seconds}s"
    )
    print(f"出力先: {options.output_dir}")
    return exit_code


def main() -> None:
    """CLI エントリポイント。"""

    options = parse_args()
    raise SystemExit(run_audit(options))


if __name__ == "__main__":
    main()
