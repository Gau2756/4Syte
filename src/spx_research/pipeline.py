from dataclasses import dataclass
from datetime import datetime

import numpy as np
import pandas as pd

from .llm import StructuredLLM
from .prompts import (
    ANALYST_SYSTEM,
    SUPERVISOR_ADJUDICATE_SYSTEM,
    SUPERVISOR_INDEPENDENT_SYSTEM,
)
from .schemas import (
    AnalystAssessment,
    IndependentAssessment,
    NewsItem,
    SupervisedAssessment,
)


@dataclass(frozen=True)
class AssessmentBundle:
    news: NewsItem
    analyst: AnalystAssessment
    independent: IndependentAssessment
    supervised: SupervisedAssessment


def assess_news(
    item: NewsItem, cutoff_at: datetime, llm: StructuredLLM
) -> AssessmentBundle:
    if cutoff_at.tzinfo is None or cutoff_at.utcoffset() is None:
        raise ValueError("cutoff_at must be timezone-aware")
    if item.published_at > cutoff_at or item.observed_at > cutoff_at:
        raise ValueError("lookahead violation: news was unavailable at cutoff")
    evidence = {
        "cutoff_at": cutoff_at.isoformat(),
        "news": item.model_dump(mode="json"),
    }
    analyst = llm.complete(
        system=ANALYST_SYSTEM, payload=evidence, response_model=AnalystAssessment
    )
    independent = llm.complete(
        system=SUPERVISOR_INDEPENDENT_SYSTEM,
        payload=evidence,
        response_model=IndependentAssessment,
    )
    supervised = llm.complete(
        system=SUPERVISOR_ADJUDICATE_SYSTEM,
        payload={
            **evidence,
            "analyst": analyst.model_dump(),
            "independent": independent.model_dump(),
        },
        response_model=SupervisedAssessment,
    )
    return AssessmentBundle(item, analyst, independent, supervised)


def aggregate_assessments(bundles: list[AssessmentBundle]) -> dict[str, float]:
    if not bundles:
        return {
            "analyst_score": 0.0,
            "supervised_score": 0.0,
            "disagreement": 0.0,
            "mean_confidence": 0.0,
            "abstention_rate": 1.0,
            "news_count": 0.0,
        }
    analyst = np.array([b.analyst.signed_score for b in bundles])
    independent = np.array([b.independent.signed_score for b in bundles])
    supervised = np.array([b.supervised.signed_score for b in bundles])
    return {
        "analyst_score": float(analyst.mean()),
        "supervised_score": float(supervised.mean()),
        "disagreement": float(np.abs(analyst - independent).mean()),
        "mean_confidence": float(
            np.mean([b.supervised.revised_confidence for b in bundles])
        ),
        "abstention_rate": float(np.mean([b.supervised.abstain for b in bundles])),
        "news_count": float(len(bundles)),
    }


def enforce_point_in_time(frame: pd.DataFrame) -> pd.DataFrame:
    required = {"cutoff_at", "available_at", "target_start_at"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"missing columns: {sorted(missing)}")
    out = frame.copy()
    for col in required:
        out[col] = pd.to_datetime(out[col], utc=True)
    if (out.available_at > out.cutoff_at).any():
        raise ValueError("lookahead violation: feature unavailable at cutoff")
    if (out.target_start_at <= out.cutoff_at).any():
        raise ValueError("target must start strictly after cutoff")
    return out.sort_values("cutoff_at").reset_index(drop=True)
