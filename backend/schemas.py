from typing import List, Optional
from pydantic import BaseModel, Field
from enum import Enum

# 1. 영문 고정 Category Enum
class CategoryEnum(str, Enum):
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

class SentimentEnum(str, Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"

class OverallSentimentEnum(str, Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"
    MIXED = "mixed"

class EvidenceMatchEnum(str, Enum):
    EXACT = "exact"
    NORMALIZED = "normalized"
    NONE = "none"

# 2. 세부 항목 스키마 (items[])
class AspectItem(BaseModel):
    category: CategoryEnum
    sentiment: SentimentEnum
    summary: str
    evidence: str
    keywords: List[str] = Field(default_factory=list)
    condition: Optional[str] = None
    mentions_change: bool = False
    evidence_match: EvidenceMatchEnum = EvidenceMatchEnum.EXACT
    evidence_verified: bool = True

# 3. 리뷰별 응답 결과 스키마 (reviews[])
class ReviewResult(BaseModel):
    review_id: str
    semester: Optional[str] = None
    status: str = "ok"  # "ok" 또는 "failed"
    overall_sentiment: Optional[OverallSentimentEnum] = None
    error: Optional[str] = None
    items: List[AspectItem] = Field(default_factory=list)

# 4. 최종 API 응답 전체 스키마
class MetaInfo(BaseModel):
    total_reviews: int
    success_count: int
    failed_count: int
    model_name: str
    processed_at: str

class SummaryByCategory(BaseModel):
    category: CategoryEnum
    counts: dict  # {"positive": x, "negative": y, "neutral": z}
    top_pros: List[str] = Field(default_factory=list)
    top_cons: List[str] = Field(default_factory=list)

class AnalysisResponse(BaseModel):
    reviews: List[ReviewResult]
    summary_by_category: List[SummaryByCategory] = Field(default_factory=list)
    meta: MetaInfo