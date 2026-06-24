"""FastAPIエンドポイント定義。"""

from __future__ import annotations

from functools import lru_cache

from fastapi import APIRouter, FastAPI, HTTPException
from pydantic import BaseModel, Field

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


class CalculationResponse(BaseModel):
    """計算APIの出力。"""

    status: str
    mode: str
    parameters: CalculationRequest
    results: list[ResultEntry]
    diagnostics: ModeDiagnostics


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
    )


def create_app() -> FastAPI:
    """アプリ本体を生成する。"""

    app = FastAPI(title="Cats Breeding Simulator", version="0.1.0")
    app.include_router(router)
    return app
