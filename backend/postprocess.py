"""LLM이 아니라 코드가 책임지는 계산들.

Mock이든 실제 LLM이든 이 함수들은 그대로 쓰인다.
"""

import re
from collections import defaultdict

from backend.schemas import (
    AnalyzedItem,
    Category,
    CategorySummary,
    EvidenceMatch,
    LLMReviewOutput,
    OverallSentiment,
    ReviewInput,
    ReviewResult,
    ReviewStatus,
    Sentiment,
    SentimentCounts,
)

# 공백과 문장부호만 제거 (조사·글자 차이는 허용하지 않음)
_IGNORABLE = re.compile(r"[\s.,!?~…·:;'\"“”‘’()\[\]{}\-_/^]+")


def _normalize(s: str) -> str:
    return _IGNORABLE.sub("", s)


def match_evidence(evidence: str, text: str) -> EvidenceMatch:
    """원문 그대로 일치 → exact, 공백·문장부호만 다름 → normalized, 그 외 → none."""
    if evidence.strip() and evidence in text:
        return EvidenceMatch.EXACT
    norm = _normalize(evidence)
    if norm and norm in _normalize(text):
        return EvidenceMatch.NORMALIZED
    return EvidenceMatch.NONE


def compute_overall(items: list[AnalyzedItem]) -> OverallSentiment | None:
    if not items:
        return None
    found = {item.sentiment for item in items}
    if Sentiment.POSITIVE in found and Sentiment.NEGATIVE in found:
        return OverallSentiment.MIXED
    if Sentiment.POSITIVE in found:
        return OverallSentiment.POSITIVE
    if Sentiment.NEGATIVE in found:
        return OverallSentiment.NEGATIVE
    return OverallSentiment.NEUTRAL


def build_result(review: ReviewInput, output: LLMReviewOutput) -> ReviewResult:
    items = []
    for item in output.items:
        match = match_evidence(item.evidence, review.text)
        items.append(
            AnalyzedItem(
                **item.model_dump(),
                evidence_match=match,
                evidence_verified=match != EvidenceMatch.NONE,
            )
        )
    return ReviewResult(
        review_id=review.id,
        semester=review.semester,
        status=ReviewStatus.OK,
        overall_sentiment=compute_overall(items),
        items=items,
    )


def failed_result(review: ReviewInput, reason: str) -> ReviewResult:
    return ReviewResult(
        review_id=review.id,
        semester=review.semester,
        status=ReviewStatus.FAILED,
        error=reason,
    )


def summarize_by_category(results: list[ReviewResult]) -> list[CategorySummary]:
    """항목별 감성 '리뷰 수' 집계.

    같은 리뷰에서 같은 항목·같은 감성이 여러 번 나와도 1로 세고,
    같은 항목에 긍정·부정이 둘 다 있으면 양쪽에 1씩 더한다.
    """
    counts: dict[Category, SentimentCounts] = defaultdict(SentimentCounts)
    for result in results:
        seen = {(item.category, item.sentiment) for item in result.items}
        for category, sentiment in seen:
            c = counts[category]
            setattr(c, sentiment.value, getattr(c, sentiment.value) + 1)
    return [
        CategorySummary(category=category, counts=counts[category])
        for category in Category
        if category in counts
    ]
