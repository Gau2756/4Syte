from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Direction(StrEnum):
    BEARISH = "bearish"
    NEUTRAL = "neutral"
    BULLISH = "bullish"


class NewsItem(StrictModel):
    news_id: str
    source: str
    published_at: datetime
    observed_at: datetime
    headline: str
    body: str

    @field_validator("published_at", "observed_at")
    @classmethod
    def timezone_required(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("timestamps must be timezone-aware")
        return value

    @model_validator(mode="after")
    def publication_precedes_observation(self):
        if self.published_at > self.observed_at:
            raise ValueError("published_at cannot follow observed_at")
        return self


class AnalystAssessment(StrictModel):
    event_type: str
    direction: Direction
    magnitude: float = Field(ge=0, le=1)
    horizon_days: int = Field(ge=1, le=30)
    novelty: float = Field(ge=0, le=1)
    surprise: float = Field(ge=-1, le=1)
    sectors: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)
    evidence: str = Field(max_length=500)

    @property
    def signed_score(self) -> float:
        sign = {
            Direction.BEARISH: -1.0,
            Direction.NEUTRAL: 0.0,
            Direction.BULLISH: 1.0,
        }[self.direction]
        return sign * self.magnitude * self.confidence


class IndependentAssessment(StrictModel):
    direction: Direction
    magnitude: float = Field(ge=0, le=1)
    confidence: float = Field(ge=0, le=1)
    already_priced_in: float = Field(ge=0, le=1)
    evidence_quality: float = Field(ge=0, le=1)

    @property
    def signed_score(self) -> float:
        sign = {
            Direction.BEARISH: -1.0,
            Direction.NEUTRAL: 0.0,
            Direction.BULLISH: 1.0,
        }[self.direction]
        return sign * self.magnitude * self.confidence


class SupervisedAssessment(StrictModel):
    agree: bool
    unsupported_claims: list[str] = Field(default_factory=list)
    duplicate_information: bool
    already_priced_in: float = Field(ge=0, le=1)
    revised_direction: Direction
    revised_magnitude: float = Field(ge=0, le=1)
    revised_confidence: float = Field(ge=0, le=1)
    abstain: bool
    rationale: str = Field(max_length=500)

    @property
    def signed_score(self) -> float:
        if self.abstain:
            return 0.0
        sign = {
            Direction.BEARISH: -1.0,
            Direction.NEUTRAL: 0.0,
            Direction.BULLISH: 1.0,
        }[self.revised_direction]
        return sign * self.revised_magnitude * self.revised_confidence
