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


class ResultEntry(BaseModel):
    """1表現型の返却形式。"""

    sex: str
    color: str
    probability_pct: float


class CalculationResponse(BaseModel):
    """計算APIの出力。"""

    status: str
    parameters: CalculationRequest
    results: list[ResultEntry]


router = APIRouter(prefix="/api/v1")


@lru_cache(maxsize=1)
def get_calculator() -> CoatColorCalculator:
    """起動後に共有する計算器を返す。"""

    return CoatColorCalculator()


@router.post("/calculate", response_model=CalculationResponse)
def calculate_endpoint(payload: CalculationRequest) -> CalculationResponse:
    """親猫の表現型から子猫表現型の確率を返す。"""

    try:
        results = get_calculator().calculate(
            sire_color=payload.sire_color,
            dam_color=payload.dam_color,
            breed=payload.breed,
        )
    except BreedingCalculationError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    return CalculationResponse(
        status="success",
        parameters=payload,
        results=[
            ResultEntry(sex=entry.sex, color=entry.color, probability_pct=entry.probability_pct)
            for entry in results
        ],
    )


def create_app() -> FastAPI:
    """アプリ本体を生成する。"""

    app = FastAPI(title="Cats Breeding Simulator", version="0.1.0")
    app.include_router(router)
    return app
