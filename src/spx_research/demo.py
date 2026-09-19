import numpy as np
import pandas as pd


def synthetic_dataset(n: int = 900, seed: int = 7) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    cutoff = pd.date_range("2019-01-02 14:25", periods=n, freq="B", tz="UTC")
    momentum = rng.normal(0, 0.01, n)
    vol = np.clip(rng.normal(0.012, 0.004, n), 0.003, None)
    vix = np.clip(14 + 500 * vol + rng.normal(0, 2, n), 9, 60)
    rates = rng.normal(0, 0.04, n)
    latent_news = rng.normal(0, 1, n)
    analyst = np.tanh(latent_news + rng.normal(0, 0.8, n))
    independent = np.tanh(latent_news + rng.normal(0, 0.7, n))
    disagreement = np.abs(analyst - independent)
    supervised = (analyst + independent) / 2 * (1 - 0.5 * disagreement)
    confidence = np.clip(1 - disagreement / 2, 0, 1)
    abstain = (confidence < 0.35).astype(float)
    logit = 0.18 * momentum / 0.01 - 0.12 * (vix - 20) / 10 + 0.30 * supervised
    probability = 1 / (1 + np.exp(-logit))
    up = rng.binomial(1, probability)
    ret = (2 * up - 1) * np.abs(rng.normal(0.006, 0.005, n))
    return pd.DataFrame(
        {
            "cutoff_at": cutoff,
            "available_at": cutoff - pd.Timedelta(minutes=1),
            "target_start_at": cutoff + pd.Timedelta(minutes=5),
            "momentum_5d": momentum,
            "realized_vol_20d": vol,
            "vix": vix,
            "rate_change_5d": rates,
            "analyst_score": analyst,
            "supervised_score": supervised,
            "disagreement": disagreement,
            "mean_confidence": confidence,
            "abstention_rate": abstain,
            "news_count": rng.integers(1, 15, n),
            "target_up": up,
            "target_return": ret,
        }
    )
