from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, brier_score_loss, log_loss, roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler


@dataclass(frozen=True)
class BacktestResult:
    predictions: pd.DataFrame
    metrics: pd.DataFrame


FEATURE_SETS = {
    "market_only": ["momentum_5d", "realized_vol_20d", "vix", "rate_change_5d"],
    "analyst_only": ["analyst_score", "mean_confidence", "news_count"],
    "dual_llm": [
        "supervised_score",
        "disagreement",
        "mean_confidence",
        "abstention_rate",
        "news_count",
    ],
    "combined": [
        "momentum_5d",
        "realized_vol_20d",
        "vix",
        "rate_change_5d",
        "supervised_score",
        "disagreement",
        "mean_confidence",
        "abstention_rate",
        "news_count",
    ],
}


def expanding_window_backtest(
    df: pd.DataFrame, min_train: int = 252, test_size: int = 63, cost_bps: float = 1.0
) -> BacktestResult:
    rows = []
    for train_end in range(min_train, len(df), test_size):
        test_end = min(train_end + test_size, len(df))
        train, test = df.iloc[:train_end], df.iloc[train_end:test_end]
        if test.empty or train["target_up"].nunique() < 2:
            continue
        for name, features in FEATURE_SETS.items():
            model = make_pipeline(
                StandardScaler(), LogisticRegression(C=0.2, max_iter=2000)
            )
            fitted = clone(model).fit(train[features], train["target_up"])
            prob = fitted.predict_proba(test[features])[:, 1]
            for idx, p in zip(test.index, prob, strict=True):
                position = 1.0 if p > 0.55 else (-1.0 if p < 0.45 else 0.0)
                rows.append(
                    {
                        "row": idx,
                        "cutoff_at": test.loc[idx, "cutoff_at"],
                        "model": name,
                        "prob_up": p,
                        "target_up": int(test.loc[idx, "target_up"]),
                        "target_return": test.loc[idx, "target_return"],
                        "position": position,
                    }
                )
    pred = pd.DataFrame(rows)
    if pred.empty:
        raise ValueError(
            "not enough observations for a valid expanding-window evaluation"
        )
    metrics = []
    for name, group in pred.groupby("model"):
        turnover = group.position.diff().abs().fillna(group.position.abs())
        net = group.position * group.target_return - turnover * cost_bps / 10_000
        std = net.std(ddof=1)
        metrics.append(
            {
                "model": name,
                "n": len(group),
                "accuracy": accuracy_score(group.target_up, group.prob_up >= 0.5),
                "brier": brier_score_loss(group.target_up, group.prob_up),
                "log_loss": log_loss(group.target_up, group.prob_up, labels=[0, 1]),
                "auc": roc_auc_score(group.target_up, group.prob_up)
                if group.target_up.nunique() == 2
                else np.nan,
                "net_mean_daily": net.mean(),
                "annualized_sharpe": np.sqrt(252) * net.mean() / std if std else np.nan,
                "max_drawdown": (net.cumsum() - net.cumsum().cummax()).min(),
                "turnover": turnover.mean(),
            }
        )
    return BacktestResult(pred, pd.DataFrame(metrics).sort_values("brier"))
