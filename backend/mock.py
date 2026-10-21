"""USE_MOCK=true일 때 쓰는 고정 응답 (프론트 개발용).

리뷰 텍스트에 아래 태그를 넣으면 프론트가 각 화면 상태를 확인할 수 있다.

    #fail      → 해당 리뷰 status: failed (에러 화면 확인용)
    #empty     → items: [] / overall_sentiment: null ("평가 내용 없음" 화면)
    #neutral   → 중립 항목 1개 (overall_sentiment: neutral)
    #positive  → 긍정 항목 1개 (overall_sentiment: positive)
    #negative  → 부정 항목 1개 (overall_sentiment: negative)
    태그 없음   → 긍정 + 부정 항목 2개 (overall_sentiment: mixed)

태그 없는 기본 응답은 README 예시 리뷰 기준이라, 다른 문장을 넣으면
evidence_match가 none으로 나온다 ("원문 확인 필요" 화면 확인용).
"""

from backend.schemas import Category, LLMItem, LLMReviewOutput, Sentiment

DEFAULT_OUTPUT = LLMReviewOutput(
    items=[
        LLMItem(
            category=Category.DELIVERY,
            sentiment=Sentiment.POSITIVE,
            summary="수업 설명이 이해하기 좋다는 의견",
            evidence="설명은 좋은데",
            keywords=["설명"],
            condition=None,
            mentions_change=False,
        ),
        LLMItem(
            category=Category.EXAM,
            sentiment=Sentiment.NEGATIVE,
            summary="시험 범위가 수업 내용과 다르다는 의견",
            evidence="시험 문제가 수업에서 안 다룬 내용 같아요",
            keywords=["시험 범위", "수업과 괴리"],
            condition=None,
            mentions_change=False,
        ),
    ]
)

_SINGLE = {
    "#neutral": (Category.TEAM_PROJECT, Sentiment.NEUTRAL, "팀 프로젝트가 있다는 언급"),
    "#positive": (Category.LEARNING, Sentiment.POSITIVE, "배운 것이 많다는 의견"),
    "#negative": (Category.WORKLOAD, Sentiment.NEGATIVE, "과제 부담이 크다는 의견"),
}


class MockFailure(RuntimeError):
    pass


def mock_analyze(text: str) -> LLMReviewOutput:
    if "#fail" in text:
        raise MockFailure("Mock: 분석 실패 시뮬레이션 (#fail)")
    if "#empty" in text:
        return LLMReviewOutput(items=[])
    for tag, (category, sentiment, summary) in _SINGLE.items():
        if tag in text:
            evidence = text.replace(tag, "").strip() or text
            return LLMReviewOutput(
                items=[
                    LLMItem(
                        category=category,
                        sentiment=sentiment,
                        summary=summary,
                        evidence=evidence,
                        keywords=[],
                        condition=None,
                        mentions_change=False,
                    )
                ]
            )
    return DEFAULT_OUTPUT.model_copy(deep=True)
