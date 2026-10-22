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
    """항목별 집계 (mentioned, ratios, counts, top_pros, top_cons 계산)."""
    # 실패한 리뷰는 집계에서 제외
    successful_results = [r for r in results if r.status == ReviewStatus.OK]

    cat_mentioned = defaultdict(set)
    counts: dict[Category, SentimentCounts] = defaultdict(SentimentCounts)
    cat_pros = defaultdict(list)
    cat_cons = defaultdict(list)

    for result in successful_results:
        review_id = result.review_id
        # 언급된 리뷰 수 계산을 위해 해당 리뷰에서 등장한 카테고리 기록 (리뷰당 1회)
        mentioned_categories_in_review = {item.category for item in result.items}
        for cat in mentioned_categories_in_review:
            cat_mentioned[cat].add(review_id)

        # 같은 리뷰에서 같은 항목·같은 감성이 여러 번 나와도 1로 세기
        seen_sentiment = {(item.category, item.sentiment) for item in result.items}
        for category, sentiment in seen_sentiment:
            c = counts[category]
            setattr(c, sentiment.value, getattr(c, sentiment.value) + 1)

        # top_pros / top_cons 수집을 위한 데이터 (summary, evidence_verified, keyword_count)
        for item in result.items:
            if item.summary:
                item_info = (item.summary, item.evidence_verified, len(item.keywords))
                if item.sentiment == Sentiment.POSITIVE:
                    cat_pros[item.category].append(item_info)
                elif item.sentiment == Sentiment.NEGATIVE:
                    cat_cons[item.category].append(item_info)

    summaries = []
    for category in Category:
        if category not in counts:
            continue

        c = counts[category]
        total_sentiments = c.positive + c.negative + c.neutral

        # 비율 계산 (분모: 해당 항목의 감성 건수 합계, 합 100%)
        ratios = {
            "positive": round((c.positive / total_sentiments * 100), 1)
            if total_sentiments > 0
            else 0.0,
            "negative": round((c.negative / total_sentiments * 100), 1)
            if total_sentiments > 0
            else 0.0,
            "neutral": round((c.neutral / total_sentiments * 100), 1)
            if total_sentiments > 0
            else 0.0,
        }

        # top_pros / top_cons 정렬 및 중복 제거 (evidence_verified=True 우선, 키워드 많은 순, 최대 3개)
        def get_top_items(items_list):
            sorted_items = sorted(items_list, key=lambda x: (x[1], x[2]), reverse=True)
            unique = []
            seen = set()
            for summary, _, _ in sorted_items:
                if summary not in seen:
                    seen.add(summary)
                    unique.append(summary)
                if len(unique) == 3:
                    break
            return unique

        summaries.append(
            CategorySummary(
                category=category,
                mentioned=len(cat_mentioned[category]),
                counts=c,
                ratios=ratios,
                top_pros=get_top_items(cat_pros[category]),
                top_cons=get_top_items(cat_cons[category]),
            )
        )
    return summaries
