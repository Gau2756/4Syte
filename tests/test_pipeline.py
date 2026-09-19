from datetime import UTC, datetime, timedelta

import pandas as pd
import pytest

from spx_research.pipeline import enforce_point_in_time
from spx_research.schemas import NewsItem


def test_news_requires_timezone():
    with pytest.raises(ValueError):
        NewsItem(
            news_id="1",
            source="x",
            published_at=datetime.now(),  # noqa: DTZ005 - deliberately naive
            observed_at=datetime.now(),  # noqa: DTZ005 - deliberately naive
            headline="h",
            body="b",
        )


def test_rejects_future_feature():
    now = datetime.now(UTC)
    frame = pd.DataFrame(
        {
            "cutoff_at": [now],
            "available_at": [now + timedelta(seconds=1)],
            "target_start_at": [now + timedelta(minutes=5)],
        }
    )
    with pytest.raises(ValueError, match="lookahead"):
        enforce_point_in_time(frame)
