# Dual-LLM S&P 500 Research MVP

This project tests whether structured news signals from an analyst LLM and an
independent supervisor improve out-of-sample S&P 500 forecasts beyond market
features alone. It is a research scaffold, not trading advice or a production
trading system.

## Design

1. Ingest immutable, timestamped news and market snapshots.
2. Analyst extracts a structured event assessment.
3. Supervisor first judges the evidence independently, then adjudicates the
   analyst output to reduce anchoring.
4. Aggregate signals at a fixed forecast cutoff.
5. Fit simple market-only, analyst, supervised, and combined baselines.
6. Evaluate chronologically with expanding-window splits and costs.

The central anti-leakage rule is `published_at <= cutoff_at`. Store the first
observed article text and first-release macro values; never silently replace
them with edited stories or revised releases.

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
spx-research demo --output outputs
pytest
```

The demo is entirely offline and generates synthetic data. It writes fold-level
predictions and model metrics to `outputs/`. Replace the synthetic rows with
your point-in-time data using the contracts in `schemas.py`.

## Expected input boundaries

- All timestamps are timezone-aware UTC.
- `cutoff_at` is the decision time (for example 09:25 America/New_York,
  converted to UTC).
- News text is the version visible at `observed_at`, with source and stable ID.
- Market features are stamped with `available_at`, not the period they describe.
- Targets begin strictly after the cutoff and include no overlapping future data.

## Live LLM integration

Implement the `StructuredLLM` protocol in `llm.py`. For production experiments,
persist the model name, prompt version, request hash, raw response, parsed JSON,
latency, and token cost. Run extraction once and cache it—never re-query models
differently for train and test rows.

## Next data sources

Start small: licensed timestamped news, official SEC/Fed/BLS first releases,
SPY or SPX bars, VIX, Treasury yields, credit spreads, breadth, and volume.
Confirm redistribution and historical-access rights before collecting content.

