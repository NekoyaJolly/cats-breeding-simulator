"""FastAPIエンドポイント定義。"""

from __future__ import annotations

from functools import lru_cache

from fastapi import APIRouter, FastAPI, HTTPException
from pydantic import BaseModel, Field

from cat_breeding_simulator.color_master import COLOR_MASTER
from cat_breeding_simulator.color_reading_ja import reading_ja
from cat_breeding_simulator.engine import BreedingCalculationError, CoatColorCalculator


class CalculationRequest(BaseModel):
    """計算APIの入力。"""

    sire_color: str = Field(min_length=1)
    dam_color: str = Field(min_length=1)
    breed: str | None = Field(default=None, min_length=1)
    # 計算モード。normal / explicit_carrier をサポート (carrier_exploration は Phase 2)。
    mode: str = Field(default="normal")
    # explicit_carrier_mode で開ける座位。例: {"C": "C/cs", "B": "B/b"}。
    sire_carriers: dict[str, str] | None = Field(default=None)
    dam_carriers: dict[str, str] | None = Field(default=None)


class ResultEntry(BaseModel):
    """1表現型の返却形式。"""

    sex: str
    color: str
    probability_pct: float


class ModeDiagnostics(BaseModel):
    """モード情報・診断値 (後方互換のため追加フィールド)。"""

    opened_loci: list[str]
    closed_loci: list[str]
    assumptions: list[str]
    matched_probability: float
    unmatched_probability: float
    unmatched_genotype_count: int


class CarrierScenarioEntry(BaseModel):
    """carrier_exploration の条件付きシナリオ (normal results とは分離)。"""

    scenario: str
    label: str
    assumed_carriers: dict[str, dict[str, str]]
    probability_basis: str
    prior_probability_applied: bool
    results: list[ResultEntry]
    new_colors: list[str]


class CalculationResponse(BaseModel):
    """計算APIの出力。"""

    status: str
    mode: str
    parameters: CalculationRequest
    results: list[ResultEntry]
    diagnostics: ModeDiagnostics
    # carrier_exploration_mode のときのみ非 null。normal/explicit では null。
    carrier_exploration_results: list[CarrierScenarioEntry] | None = None


class ColorOption(BaseModel):
    """入力サジェスト用の 1 色エントリ。"""

    value: str                  # 送信に用いる canonical 正式名
    reading_ja: str             # カタカナ読み (合成生成)
    status: str                 # canonical / breed_specific
    breed_context: str          # 猫種固有色なら猫種名 (例: Abyssinian)
    sex_restriction: str        # female_only / unrestricted
    # 突合キー群 (英正式名 / alias / 略称 / カナ読みを含む)。フロントの絞り込みに使う。
    keywords: list[str]


class ColorsResponse(BaseModel):
    """入力サジェスト用の色一覧。"""

    colors: list[ColorOption]


router = APIRouter(prefix="/api/v1")


@lru_cache(maxsize=1)
def get_calculator() -> CoatColorCalculator:
    """起動後に共有する計算器を返す。"""

    return CoatColorCalculator()


@router.post("/calculate", response_model=CalculationResponse)
def calculate_endpoint(payload: CalculationRequest) -> CalculationResponse:
    """親猫の表現型から子猫表現型の確率を返す。"""

    try:
        report = get_calculator().calculate_report(
            sire_color=payload.sire_color,
            dam_color=payload.dam_color,
            breed=payload.breed,
            mode=payload.mode,
            sire_carriers=payload.sire_carriers,
            dam_carriers=payload.dam_carriers,
        )
    except BreedingCalculationError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    return CalculationResponse(
        status="success",
        mode=report.mode,
        parameters=payload,
        results=[
            ResultEntry(sex=entry.sex, color=entry.color, probability_pct=entry.probability_pct)
            for entry in report.results
        ],
        diagnostics=ModeDiagnostics(
            opened_loci=report.opened_loci or [],
            closed_loci=report.closed_loci or [],
            assumptions=report.assumptions or [],
            matched_probability=report.matched_probability,
            unmatched_probability=report.unmatched_probability,
            unmatched_genotype_count=report.unmatched_genotype_count,
        ),
        carrier_exploration_results=(
            [
                CarrierScenarioEntry(
                    scenario=scenario.scenario,
                    label=scenario.label,
                    assumed_carriers=scenario.assumed_carriers,
                    probability_basis=scenario.probability_basis,
                    prior_probability_applied=scenario.prior_probability_applied,
                    results=[
                        ResultEntry(sex=e.sex, color=e.color, probability_pct=e.probability_pct)
                        for e in scenario.results
                    ],
                    new_colors=scenario.new_colors,
                )
                for scenario in report.carrier_exploration_results
            ]
            if report.carrier_exploration_results is not None
            else None
        ),
    )


@router.get("/colors", response_model=ColorsResponse)
def colors_endpoint() -> ColorsResponse:
    """入力サジェスト用の色一覧を返す (canonical 正式名 + カナ読み + 突合キー)。"""

    colors: list[ColorOption] = []
    for option in COLOR_MASTER.list_input_colors():
        reading = reading_ja(option.value)
        # カナ読みも突合キーに含める (日本語入力での絞り込み用)。重複は順序保持で除去。
        keywords = list(dict.fromkeys([*option.keywords, reading]))
        colors.append(
            ColorOption(
                value=option.value,
                reading_ja=reading,
                status=option.status,
                breed_context=option.breed_context,
                sex_restriction=option.sex_restriction,
                keywords=keywords,
            )
        )
    return ColorsResponse(colors=colors)


def create_app() -> FastAPI:
    """アプリ本体を生成する。"""

    app = FastAPI(title="Cats Breeding Simulator", version="0.1.0")
    app.include_router(router)
    return app
