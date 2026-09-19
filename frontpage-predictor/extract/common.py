"""Shared helpers: config loading, date iteration, paths."""
from __future__ import annotations

import datetime as dt
from pathlib import Path
from typing import Iterator

import yaml

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"


def load_yaml(name: str) -> dict:
    with open(ROOT / "config" / name, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def as_date(v) -> dt.date:
    if isinstance(v, dt.datetime):
        return v.date()
    if isinstance(v, dt.date):
        return v
    return dt.date.fromisoformat(str(v))


def daterange(start: dt.date, end: dt.date) -> Iterator[dt.date]:
    """Yield dates from start (inclusive) to end (exclusive)."""
    d = start
    while d < end:
        yield d
        d += dt.timedelta(days=1)
