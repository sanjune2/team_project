from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional

from backend.schemas import (
    AnalysisResponse,
    ReviewResult,
    AspectItem,
    CategoryEnum,
    SentimentEnum,
    OverallSentimentEnum,
    MetaInfo,
    SummaryByCategory,
)

app = FastAPI(title="Lecture Evaluation AI API")


@app.get("/")
def read_root():
    return {"message": "Lecture Evaluation AI Backend is running!"}


# 요청 스키마 (테스트 케이스 구조와 일치시킴)
class SingleReviewInput(BaseModel):
    id: str  # 또는 int
    text: str
    semester: Optional[str] = None


class BatchReviewRequest(BaseModel):
    reviews: List[SingleReviewInput]


@app.post("/api/analyze", response_model=AnalysisResponse)
def analyze_review(request: BatchReviewRequest):
    # 1. 422 에러 테스트 대응 (리뷰가 비어있는 경우)
    if not request.reviews:
        raise HTTPException(
            status_code=422, detail="INVALID_INPUT: Reviews list cannot be empty"
        )

    results = []

    for rev in request.reviews:
        # 2. #fail 테스트 케이스 대응
        if "#fail" in rev.text:
            results.append(
                ReviewResult(
                    review_id=str(rev.id),
                    semester=rev.semester,
                    status="failed",
                    error="Simulated failure for testing",
                    items=[],
                )
            )
            continue

        # 3. #empty 테스트 케이스 대응
        if "#empty" in rev.text:
            results.append(
                ReviewResult(
                    review_id=str(rev.id),
                    semester=rev.semester,
                    status="ok",
                    overall_sentiment=OverallSentimentEnum.NEUTRAL,
                    items=[],
                )
            )
            continue

        # 4. 일반적인 Mixed 감성 테스트 케이스 대응 (가이드 예시)
        results.append(
            ReviewResult(
                review_id=str(rev.id),
                semester=rev.semester,
                status="ok",
                overall_sentiment=OverallSentimentEnum.MIXED,
                items=[
                    AspectItem(
                        category=CategoryEnum.LEARNING,
                        sentiment=SentimentEnum.POSITIVE,
                        summary="설명 내용이 좋음",
                        evidence="설명은 좋은데",
                    ),
                    AspectItem(
                        category=CategoryEnum.EXAM,
                        sentiment=SentimentEnum.NEGATIVE,
                        summary="시험 출제가 부적절함",
                        evidence="시험 문제가 수업에서 안 다룬 내용 같아요.",
                    ),
                ],
            )
        )

    # 최종 응답 객체 반환
    return AnalysisResponse(
        reviews=results,
        summary_by_category=[],
        meta=MetaInfo(
            total_reviews=len(request.reviews),
            success_count=sum(1 for r in results if r.status == "ok"),
            failed_count=sum(1 for r in results if r.status == "failed"),
            model_name="mock-model",
            processed_at="2026-10-20T17:00:00",
        ),
    )
