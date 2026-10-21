"""강의평 분석 API.

실행 (저장소 루트에서): uvicorn backend.main:app --reload --port 8000
"""

import os
from datetime import datetime, timezone

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from backend.mock import mock_analyze
from backend.postprocess import build_result, failed_result, summarize_by_category
from backend.schemas import (
    CATEGORY_LABELS,
    AnalyzeRequest,
    AnalyzeResponse,
    CategoryInfo,
    LLMReviewOutput,
    Meta,
    ReviewInput,
    ReviewResult,
    ReviewStatus,
)

load_dotenv()
USE_MOCK = os.getenv("USE_MOCK", "true").lower() == "true"
MODEL_NAME = "mock" if USE_MOCK else os.getenv("OPENAI_MODEL", "unknown")

app = FastAPI(title="Lecture Review Analysis API")


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    """입력 오류를 합의한 에러 형식 {"error": {"code", "message"}}으로 반환."""
    details = [
        {"loc": ".".join(str(p) for p in e["loc"]), "msg": e["msg"]}
        for e in exc.errors()
    ]
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "INVALID_INPUT",
                "message": "요청 형식이 올바르지 않습니다.",
                "details": details,
            }
        },
    )


def call_llm(text: str) -> LLMReviewOutput:
    """실제 LLM 호출. 분석 파트(analysis/)가 구현하면 여기서 연결."""
    raise NotImplementedError("LLM 분석 함수가 아직 연결되지 않았습니다.")


def analyze_one(review: ReviewInput) -> ReviewResult:
    try:
        output = mock_analyze(review.text) if USE_MOCK else call_llm(review.text)
        return build_result(review, output)
    except Exception as e:  # 리뷰 하나가 실패해도 나머지는 계속 처리
        return failed_result(review, str(e))


@app.get("/api/health")
def health():
    return {"status": "ok", "mock": USE_MOCK}


@app.get("/api/categories", response_model=list[CategoryInfo])
def categories():
    return [CategoryInfo(code=c, label=label) for c, label in CATEGORY_LABELS.items()]


@app.post("/api/analyze", response_model=AnalyzeResponse)
def analyze(request: AnalyzeRequest):
    results = [analyze_one(r) for r in request.reviews]
    succeeded = sum(r.status == ReviewStatus.OK for r in results)
    return AnalyzeResponse(
        reviews=results,
        summary_by_category=summarize_by_category(results),
        meta=Meta(
            total_reviews=len(results),
            succeeded=succeeded,
            failed=len(results) - succeeded,
            model=MODEL_NAME,
            processed_at=datetime.now(timezone.utc),
        ),
    )
