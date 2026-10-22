"""Notion Ver 3.1 model output only. Public backend schemas are unchanged."""
from typing import Literal
from .runtime import enable_local_packages

enable_local_packages()
from pydantic import BaseModel, ConfigDict, Field, model_validator

Category = Literal["workload", "exam", "team_project", "delivery", "attendance", "grade", "learning", "professor", "general_impression", "etc"]
Sentiment = Literal["positive", "negative", "neutral"]


class StrictOutput(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class LLMItem(StrictOutput):
    category: Category
    sentiment: Sentiment
    summary: str = Field(min_length=1)
    evidence: str = Field(min_length=1)
    keywords: list[str] = Field(max_length=3)
    condition: str | None
    mentions_change: bool

    @model_validator(mode="after")
    def validate_text(self):
        if not self.summary.strip() or "\n" in self.summary or "\r" in self.summary:
            raise ValueError("summary는 비어 있지 않은 한 줄이어야 합니다.")
        if not self.evidence.strip():
            raise ValueError("evidence는 비어 있을 수 없습니다.")
        if self.condition is not None and not self.condition.strip():
            raise ValueError("조건이 없으면 null을 사용하세요.")
        if any(not word.strip() or word != word.strip() for word in self.keywords):
            raise ValueError("keywords에 빈 값이나 양끝 공백을 넣을 수 없습니다.")
        if len(set(self.keywords)) != len(self.keywords):
            raise ValueError("keywords는 중복할 수 없습니다.")
        return self


class LLMWireOutput(StrictOutput):
    items: list[LLMItem]


class LLMReviewOutput(LLMWireOutput):
    @model_validator(mode="after")
    def validate_pairs(self):
        pairs = [(item.category, item.sentiment) for item in self.items]
        if len(pairs) != len(set(pairs)):
            raise ValueError("같은 항목과 감성은 하나의 item으로 합쳐야 합니다.")
        return self
