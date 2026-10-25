"""Notion overview 시험 형식과 근거 ID 검증. 생성 및 API 계약과 분리한다."""
from copy import deepcopy
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

CategoryCode = Literal['workload', 'exam', 'team_project', 'delivery', 'attendance',
                       'grade', 'learning', 'professor', 'general_impression', 'etc']
Sentiment = Literal['positive', 'negative', 'neutral']
DISPLAY_LABELS = {
    'workload': '과제량', 'exam': '시험', 'team_project': '팀 프로젝트',
    'delivery': '전달력', 'attendance': '출석', 'grade': '성적',
    'learning': '학습 가치', 'professor': '교수자 태도',
    'general_impression': '총평', 'etc': '기타',
}


class StrictModel(BaseModel):
    model_config = ConfigDict(extra='forbid')


class Advice(StrictModel):
    keyword: str
    text: str
    review_ids: list[str]
    basis: int | None = Field(default=None, ge=0)

    @field_validator('keyword', 'text')
    @classmethod
    def nonempty(cls, value):
        if not value.strip():
            raise ValueError('빈 문장을 사용할 수 없습니다.')
        return value


class Headline(StrictModel):
    positive: str | None
    negative: str | None


class Group(StrictModel):
    sentiment: Sentiment
    topic: str
    short: str
    detail: str
    review_ids: list[str]
    basis: int | None = Field(default=None, ge=0)

    @field_validator('topic', 'short', 'detail')
    @classmethod
    def nonempty(cls, value):
        if not value.strip():
            raise ValueError('빈 의견 묶음을 사용할 수 없습니다.')
        return value


class Category(StrictModel):
    category: CategoryCode
    headline: Headline
    groups: list[Group] = Field(max_length=5)


class Overview(StrictModel):
    audience: Literal['instructor', 'learner']
    left: list[Advice] = Field(max_length=3)
    right: list[Advice] = Field(max_length=3)
    suggestion: str | None
    categories: list[Category]


def validate_overview(value: dict, result: dict, *, audience: str) -> tuple[dict, list[dict]]:
    """Validate a copy, filter invalid IDs, compute basis and report review needs.

    Invalid schemas raise ValueError. Callers must retain their original result.
    Removing IDs does not prove the remaining text: affected text needs review.
    """
    overview = Overview.model_validate(deepcopy(value)).model_dump()
    if overview['audience'] != audience:
        raise ValueError('파일 대상과 overview 대상이 다릅니다.')
    if audience == 'learner' and overview['suggestion'] is not None:
        raise ValueError('학습자 suggestion은 null이어야 합니다.')
    if audience == 'instructor' and not (overview['suggestion'] or '').strip():
        raise ValueError('교수자 방향 제안이 필요합니다.')
    codes = [c['category'] for c in overview['categories']]
    if len(codes) != len(set(codes)):
        raise ValueError('같은 항목을 중복 생성했습니다.')
    pairs = {(str(r['review_id']), i['category'], i['sentiment'])
             for r in result['reviews'] if r['status'] == 'ok' for i in r['items']}
    labels = {name: code for code, name in DISPLAY_LABELS.items()}
    issues = []

    def clean(item, code, sentiment, location):
        before = item['review_ids']
        kept = list(dict.fromkeys(rid for rid in before if (rid, code, sentiment) in pairs))
        removed = [rid for rid in dict.fromkeys(before) if (rid, code, sentiment) not in pairs]
        if removed:
            issues.append({'location': location, 'removed_ids': removed,
                           'requires_text_review': True})
        item['review_ids'] = kept
        item['basis'] = len(kept)
        return bool(kept)

    for side, sentiment in [('left', 'positive'), ('right', 'negative')]:
        retained = []
        for n, item in enumerate(overview[side]):
            if item['keyword'] not in labels:
                raise ValueError(f"정의되지 않은 keyword: {item['keyword']}")
            if clean(item, labels[item['keyword']], sentiment, f'{side}[{n}]'):
                retained.append(item)
        overview[side] = retained
    for category in overview['categories']:
        code = category['category']
        retained = []
        for n, group in enumerate(category['groups']):
            if clean(group, code, group['sentiment'], f'{code}.groups[{n}]'):
                retained.append(group)
        category['groups'] = sorted(retained, key=lambda g: -g['basis'])
        for sentiment in ('positive', 'negative'):
            if not any(c == code and s == sentiment for _, c, s in pairs):
                category['headline'][sentiment] = None
    return overview, issues
