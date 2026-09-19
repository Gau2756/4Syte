from spx_research.backtest import expanding_window_backtest
from spx_research.demo import synthetic_dataset
from spx_research.pipeline import enforce_point_in_time


def test_backtest_produces_all_baselines():
    result = expanding_window_backtest(
        enforce_point_in_time(synthetic_dataset(400)), min_train=252
    )
    assert set(result.metrics.model) == {
        "market_only",
        "analyst_only",
        "dual_llm",
        "combined",
    }
    assert result.predictions.prob_up.between(0, 1).all()
