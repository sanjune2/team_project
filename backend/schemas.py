"""API 요청·응답과 LLM 출력 스키마.

노션 '5. JSON 스키마'를 코드로 옮긴 것으로, 프론트·백엔드·분석 파트의 공통 계약서입니다.
"""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


# ── 공통 enum ──────────────────────────────────────────────


class Category(str, Enum):
    """평가 항목 (노션 2번, 10개). 한글 표시는 프론트가 /api/categories로 매핑."""

    WORKLOAD = "workload"
    EXAM = "exam"
    TEAM_PROJECT = "team_project"
    DELIVERY = "delivery"
    ATTENDANCE = "attendance"
    GRADE = "grade"
    LEARNING = "learning"
    PROFESSOR = "professor"
    GENERAL_IMPRESSION = "general_impression"
    ETC = "etc"


CATEGORY_LABELS: dict[Category, str] = {
    Category.WORKLOAD: "과제량·로드",
    Category.EXAM: "시험·평가 방식",
    Category.TEAM_PROJECT: "팀 프로젝트",
    Category.DELIVERY: "전달력·수업 구성",
    Category.ATTENDANCE: "출석·참여",
    Category.GRADE: "성적·학점",
    Category.LEARNING: "학습 가치",
    Category.PROFESSOR: "교수자 태도",
    Category.GENERAL_IMPRESSION: "총평",
    Category.ETC: "기타",
}


class Sentiment(str, Enum):
    """항목 단위 감성. mixed는 여기 없음 (리뷰 단위에서 코드가 계산)."""

    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"


class OverallSentiment(str, Enum):
    """리뷰 단위 감성. LLM이 아니라 postprocess.py가 items로부터 계산."""

    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"
    MIXED = "mixed"


class EvidenceMatch(str, Enum):
    """evidence가 원문과 어떻게 일치하는지 (코드가 계산)."""

    EXACT = "exact"  # 원문 그대로의 부분 문자열 → 프론트에서 하이라이트 가능
    NORMALIZED = "normalized"  # 공백·문장부호만 다름 → 하이라이트는 불가
    NONE = "none"  # 원문에 없음 (환각 의심)


class ReviewStatus(str, Enum):
    OK = "ok"
    FAILED = "failed"


# ── 요청 ──────────────────────────────────────────────────


class ReviewInput(BaseModel):
    id: str = Field(min_length=1, max_length=50, description="리뷰 ID")
    text: str = Field(min_length=1, max_length=3000, description="리뷰 원문")
    semester: str | None = Field(default=None, description='수강 학기 (예: "25-2")')


class AnalyzeRequest(BaseModel):
    reviews: list[ReviewInput] = Field(min_length=1, max_length=50)


# ── LLM 출력 (Structured Outputs에 그대로 넘기는 스키마) ──────
# OpenAI strict 모드는 모든 필드가 '필수'여야 하므로 기본값을 두지 않는다.
# 값이 없을 때는 LLM이 null / [] / false를 직접 채운다.


class LLMItem(BaseModel):
    category: Category
    sentiment: Sentiment
    summary: str = Field(description="비난·실명을 뺀 한 줄 요약")
    evidence: str = Field(description="원문 부분 문자열, 오타까지 그대로")
    keywords: list[str] = Field(description="핵심 키워드 0~3개")
    condition: str | None = Field(description="조건부 평가의 조건, 없으면 null")
    mentions_change: bool = Field(description="수업 방식 변화 언급 여부")


class LLMReviewOutput(BaseModel):
    items: list[LLMItem] = Field(description="평가 대상이 없으면 빈 배열")


# ── 응답 ──────────────────────────────────────────────────


class AnalyzedItem(LLMItem):
    evidence_match: EvidenceMatch = Field(description="원문 일치 방식 (코드가 계산)")
    evidence_verified: bool = Field(description="evidence_match가 none이 아니면 true")


class ReviewResult(BaseModel):
    review_id: str
    semester: str | None = None
    status: ReviewStatus
    overall_sentiment: OverallSentiment | None = Field(
        default=None, description="items가 비거나 실패하면 null"
    )
    items: list[AnalyzedItem] = Field(default_factory=list)
    error: str | None = Field(default=None, description="status가 failed일 때 사유")


class SentimentCounts(BaseModel):
    """감성별 '리뷰 수'. 같은 리뷰에서 같은 항목이 여러 번 나와도 1로 센다."""

    positive: int = 0
    negative: int = 0
    neutral: int = 0


class CategorySummary(BaseModel):
    category: Category
    counts: SentimentCounts
    top_pros: list[str] = Field(default_factory=list, description="21일 이후 구현")
    top_cons: list[str] = Field(default_factory=list, description="21일 이후 구현")


class Meta(BaseModel):
    total_reviews: int
    succeeded: int
    failed: int
    model: str
    processed_at: datetime


class AnalyzeResponse(BaseModel):
    reviews: list[ReviewResult]
    summary_by_category: list[CategorySummary]
    meta: Meta


class CategoryInfo(BaseModel):
    code: Category
    label: str
