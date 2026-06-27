"""FastAPIエンドポイント定義。"""

from __future__ import annotations

from functools import lru_cache

from fastapi import APIRouter, FastAPI, HTTPException, Request
from pydantic import BaseModel, Field

from cat_breeding_simulator.color_master import COLOR_MASTER
from cat_breeding_simulator.color_reading_ja import reading_ja
from cat_breeding_simulator.engine import BreedingCalculationError, CoatColorCalculator
from cat_breeding_simulator.feedback import (
    MAX_MESSAGE_LENGTH,
    check_rate_limit,
    send_feedback_email,
)
from cat_breeding_simulator.master_data import (
    CANONICAL_BREEDS,
    VALID_BREEDS,
    recognized_color_keys_for_breed,
)


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


class ParentColorNoteEntry(BaseModel):
    """入力した親色が子に出現しないことを示す注釈。"""

    parent: str                  # sire / dam
    color: str                   # canonical な親色
    blocked_factors: list[str]   # 子に再現できない劣性因子 (相手親が持たない)


class CalculationResponse(BaseModel):
    """計算APIの出力。"""

    status: str
    mode: str
    parameters: CalculationRequest
    results: list[ResultEntry]
    diagnostics: ModeDiagnostics
    # carrier_exploration_mode のときのみ非 null。normal/explicit では null。
    carrier_exploration_results: list[CarrierScenarioEntry] | None = None
    # 入力した親色が子に出ないときの注釈 (normal モードのみ、無ければ空配列)。
    parent_color_notes: list[ParentColorNoteEntry] = Field(default_factory=list)


class ColorOption(BaseModel):
    """入力サジェスト用の 1 色エントリ。"""

    value: str                  # 送信に用いる canonical 正式名
    reading_ja: str             # カタカナ読み (合成生成)
    status: str                 # canonical / breed_specific
    # 猫種固有色 (breed_specific) のときのみ猫種名 (例: Abyssinian)。
    # 一般色 (master の BreedContext=general) は猫種名ではないため "" に正規化して返す。
    breed_context: str
    sex_restriction: str        # female_only / unrestricted
    # 突合キー群 (英正式名 / alias / 略称 / カナ読みを含む)。フロントの絞り込みに使う。
    keywords: list[str]


class ColorsResponse(BaseModel):
    """入力サジェスト用の色一覧。"""

    colors: list[ColorOption]


class BreedOption(BaseModel):
    """入力サジェスト用の 1 猫種エントリ。"""

    value: str               # 送信に使う猫種名 (BREED_FILTERS のキー)
    affects_genetics: bool   # 座位制約があり計算結果に影響するか


class BreedsResponse(BaseModel):
    """入力サジェスト + バリデーション用の猫種一覧。"""

    breeds: list[BreedOption]


class BreedColorsResponse(BaseModel):
    """猫種で「使える毛色」(その猫種の遺伝制約を満たす色) 一覧。"""

    breed: str
    # 遺伝制約を持つ猫種か。false の場合 colors は空で「全色が使える」を意味する。
    constrained: bool
    colors: list[str]


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
        parent_color_notes=[
            ParentColorNoteEntry(
                parent=note.parent,
                color=note.color,
                blocked_factors=note.blocked_factors,
            )
            for note in (report.parent_color_notes or [])
        ],
    )


@router.get("/colors", response_model=ColorsResponse)
def colors_endpoint() -> ColorsResponse:
    """入力サジェスト用の色一覧を返す (canonical 正式名 + カナ読み + 突合キー)。"""

    colors: list[ColorOption] = []
    for option in COLOR_MASTER.list_input_colors():
        reading = reading_ja(option.value)
        # カナ読みも突合キーに含める (日本語入力での絞り込み用)。重複は順序保持で除去。
        keywords = list(dict.fromkeys([*option.keywords, reading]))
        # 一般色の BreedContext=general は猫種名ではないため "" に正規化する。
        # breed_specific のときだけ猫種名が入る契約に揃える。
        breed_context = "" if option.breed_context == "general" else option.breed_context
        colors.append(
            ColorOption(
                value=option.value,
                reading_ja=reading,
                status=option.status,
                breed_context=breed_context,
                sex_restriction=option.sex_restriction,
                keywords=keywords,
            )
        )
    return ColorsResponse(colors=colors)


@router.get("/breeds", response_model=BreedsResponse)
def breeds_endpoint() -> BreedsResponse:
    """入力サジェスト + バリデーション用の有効な猫種一覧を返す。

    ゴミ行を除外し、コートバリアント違い (SH/LH/SE/NL 等) は base に集約済み。
    affects_genetics=true の猫種だけが座位制約を持ち計算結果に影響する。
    """

    breeds = [
        BreedOption(value=name, affects_genetics=affects)
        for name, affects in sorted(CANONICAL_BREEDS.items())
    ]
    return BreedsResponse(breeds=breeds)


@router.get("/breed-colors", response_model=BreedColorsResponse)
def breed_colors_endpoint(breed: str) -> BreedColorsResponse:
    """指定猫種で使える毛色 (遺伝制約を満たす canonical 色名) を返す。

    認定カラーの案内ポップアップ用。制約を持たない猫種は constrained=false / colors=[]
    (全色が使える) を返す。
    """

    breed_key = CoatColorCalculator._normalize_breed_key(breed)
    # /calculate と同じ基準 (VALID_BREEDS) で未対応の猫種は弾く (API 間で挙動を揃える)。
    if breed_key not in VALID_BREEDS:
        raise HTTPException(status_code=422, detail=f"未対応の猫種です: '{breed}'")
    keys = recognized_color_keys_for_breed(breed_key)
    if keys is None:
        return BreedColorsResponse(breed=breed, constrained=False, colors=[])
    # 生の遺伝マップ名を canonical 表示名へ寄せ、重複を除去 (set 併用で O(n)) してソートする。
    seen_set: set[str] = set()
    seen: list[str] = []
    for key in keys:
        display = COLOR_MASTER.canonical_name(key)
        if display not in seen_set:
            seen_set.add(display)
            seen.append(display)
    return BreedColorsResponse(breed=breed, constrained=True, colors=sorted(seen))


class FeedbackRequest(BaseModel):
    """フィードバック送信の入力 (最大 200 文字)。"""

    message: str = Field(min_length=1, max_length=MAX_MESSAGE_LENGTH)


class FeedbackResponse(BaseModel):
    """フィードバック受付結果。sent=管理者へのメール送信に成功したか。"""

    sent: bool


# レート制限キーとして保持する IP 文字列の最大長 (長大ヘッダ値の dict キー化を防ぐ)。
_MAX_IP_KEY_LENGTH = 64


def _client_ip(request: Request) -> str:
    """レート制限用のクライアント IP。プロキシ経由は X-Forwarded-For の先頭要素を使う。

    ヘッダは詐称・長大化され得るため、先頭要素のみ採用し、空/過長は無視して
    request.client.host にフォールバックする。
    """

    forwarded = request.headers.get("x-forwarded-for", "")
    candidate = forwarded.split(",")[0].strip() if forwarded else ""
    if candidate and len(candidate) <= _MAX_IP_KEY_LENGTH:
        return candidate
    return request.client.host if request.client else "unknown"


@router.post("/feedback", response_model=FeedbackResponse)
def feedback_endpoint(payload: FeedbackRequest, request: Request) -> FeedbackResponse:
    """常駐ウィジェットからのフィードバックを受け付け、管理者宛にメール送信する。

    匿名アプリのため IP 単位の簡易レート制限をかける。メール基盤未設定の環境では
    送信は行わず sent=false を返す (受付自体は成功扱い)。
    """

    if not check_rate_limit(_client_ip(request)):
        raise HTTPException(
            status_code=429,
            detail="フィードバックの送信が多すぎます。しばらくしてからお試しください。",
        )
    message = payload.message.strip()
    if not message:
        raise HTTPException(status_code=422, detail="メッセージを入力してください。")
    return FeedbackResponse(sent=send_feedback_email(message))


def create_app() -> FastAPI:
    """アプリ本体を生成する。"""

    app = FastAPI(title="Cats Breeding Simulator", version="0.1.0")
    app.include_router(router)
    return app
