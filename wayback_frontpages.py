"""
Wayback Machine front-page extractor.

For each outlet and each local date:
  1. List snapshots via the CDX API (chunked by month).
  2. Pick the snapshot nearest the outlet's target local time.
  3. Download the raw archived HTML (the `id_` flag returns the original page
     without Wayback's toolbar/link rewriting) and store a gzipped copy.
  4. Parse headlines into rows, in document order.
  5. Record a coverage row (ok / no_snapshot / fetch_failed / parse_empty).

Outputs
  data/raw/wayback_html/<outlet>/<date>.html.gz
  data/raw/frontpage/outlet=<outlet>/date=<date>/part.parquet
  data/raw/frontpage/_coverage.jsonl         (append-only, makes runs resumable)
  data/interim/coverage.parquet              (consolidated at the end)

IMPORTANT
  * "date" is the LOCAL calendar date of the target snapshot time. A front page
    from date D is a LABEL for a prediction made at the cutoff on D-1.
  * Days with no usable snapshot are logged as missing. Do NOT treat them as
    empty front pages; exclude them from training.
  * position_rank is DOM order, an approximation of prominence, not a visual
    rank. Treat is_lead_story as a heuristic.

Usage
  python -m extract.wayback_frontpages --outlets nytimes
  python -m extract.wayback_frontpages --start 2026-06-01 --end 2026-06-08
"""
from __future__ import annotations

import argparse
import datetime as dt
import gzip
import json
import time
from zoneinfo import ZoneInfo

import pandas as pd
import requests
from bs4 import BeautifulSoup
from tqdm import tqdm
from urllib.parse import urljoin

from .common import DATA, as_date, daterange, load_yaml

CDX_URL = "https://web.archive.org/cdx/search/cdx"
SNAP_URL = "https://web.archive.org/web/{ts}id_/{url}"

HTML_DIR = DATA / "raw" / "wayback_html"
FP_DIR = DATA / "raw" / "frontpage"
COVERAGE_LOG = FP_DIR / "_coverage.jsonl"


# ---------------------------------------------------------------- HTTP helpers
def get_with_retry(session, url, *, params=None, max_retries=5, timeout=60):
    delay = 2.0
    for attempt in range(max_retries):
        try:
            r = session.get(url, params=params, timeout=timeout)
            if r.status_code == 200:
                return r
            if r.status_code in (429, 500, 502, 503, 504):
                time.sleep(delay)
                delay *= 2
                continue
            return None  # 404 etc.: don't retry
        except requests.RequestException:
            time.sleep(delay)
            delay *= 2
    return None


# ------------------------------------------------------------------ CDX lookup
def list_snapshots(session, url, start: dt.date, end: dt.date, retries: int):
    """Return sorted list of (utc_datetime, original_url) for 200-status captures.

    Queries month-sized chunks with a one-day margin either side, so local-time
    targets that straddle a UTC date boundary are still covered.
    """
    snaps: dict[dt.datetime, str] = {}
    cur = start - dt.timedelta(days=1)
    stop = end + dt.timedelta(days=1)
    while cur < stop:
        chunk_end = min(cur + dt.timedelta(days=31), stop)
        params = {
            "url": url,
            "matchType": "exact",
            "from": cur.strftime("%Y%m%d"),
            "to": chunk_end.strftime("%Y%m%d"),
            "output": "json",
            "fl": "timestamp,original,statuscode",
            "filter": "statuscode:200",
        }
        r = get_with_retry(session, CDX_URL, params=params, max_retries=retries)
        if r is not None and r.text.strip():
            rows = r.json()
            for ts, original, _status in rows[1:]:  # first row is the header
                t = dt.datetime.strptime(ts, "%Y%m%d%H%M%S").replace(tzinfo=dt.timezone.utc)
                snaps[t] = original
        cur = chunk_end
    return sorted(snaps.items())


def pick_nearest(snaps, day: dt.date, tz: ZoneInfo, hhmm: str, max_hours_off: float):
    hh, mm = (int(x) for x in hhmm.split(":"))
    target_local = dt.datetime.combine(day, dt.time(hh, mm), tzinfo=tz)
    target = target_local.astimezone(dt.timezone.utc)
    best = None
    best_diff = None
    for t, original in snaps:
        diff = abs((t - target).total_seconds())
        if best_diff is None or diff < best_diff:
            best, best_diff = (t, original), diff
    if best is None or best_diff > max_hours_off * 3600:
        return None
    return best


# --------------------------------------------------------------------- parsing
def _anchor_for(el):
    if el.name == "a":
        return el
    return el.find("a", href=True) or el.find_parent("a", href=True)


def parse_headlines(html: bytes, base_url: str, selector: str | None = None):
    """Extract headlines in document order.

    With `selector`, uses that CSS selector for headline elements. Otherwise
    falls back to h1/h2/h3 elements that carry a link. Layouts differ per
    outlet and change over time, so tune `headline_selector` per outlet.
    """
    soup = BeautifulSoup(html, "lxml")
    elements = soup.select(selector) if selector else soup.find_all(["h1", "h2", "h3"])

    rows, seen = [], set()
    for el in elements:
        a = _anchor_for(el)
        if a is None:
            continue
        text = el.get_text(" ", strip=True)
        if len(text) < 15 or len(text.split()) < 3:
            continue  # nav labels, "Sign in", etc.
        url = urljoin(base_url, a["href"])
        if url in seen:
            continue
        seen.add(url)

        subhead = None
        container = el.find_parent(["article", "section", "div"])
        if container is not None:
            p = container.find("p")
            if p is not None:
                s = p.get_text(" ", strip=True)
                if s and s != text:
                    subhead = s[:400]

        section = None
        sec_el = el.find_parent(attrs={"aria-label": True})
        if sec_el is not None:
            section = sec_el.get("aria-label")

        rows.append({
            "position_rank": len(rows) + 1,
            "headline": text,
            "subhead": subhead,
            "url": url,
            "section": section,
            "is_lead_story": len(rows) == 0,
        })
    return rows


# ------------------------------------------------------------------ bookkeeping
def load_done() -> set[tuple[str, str]]:
    done = set()
    if COVERAGE_LOG.exists():
        for line in COVERAGE_LOG.read_text().splitlines():
            rec = json.loads(line)
            if rec["status"] in ("ok", "no_snapshot", "parse_empty"):
                done.add((rec["outlet"], rec["date"]))  # retry only fetch_failed
    return done


def log_coverage(rec: dict):
    COVERAGE_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(COVERAGE_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec) + "\n")


def consolidate_coverage():
    if not COVERAGE_LOG.exists():
        return
    recs = [json.loads(l) for l in COVERAGE_LOG.read_text().splitlines()]
    df = pd.DataFrame(recs).drop_duplicates(["outlet", "date"], keep="last")
    out = DATA / "interim" / "coverage.parquet"
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out, index=False)
    print("\nCoverage summary:")
    print(df.groupby(["outlet", "status"]).size().unstack(fill_value=0))


# ------------------------------------------------------------------------ main
def process_outlet(session, outlet: dict, days: list[dt.date], run: dict, done: set):
    name = outlet["name"]
    tz = ZoneInfo(outlet["timezone"])
    todo = [d for d in days if (name, d.isoformat()) not in done]
    if not todo:
        print(f"{name}: nothing to do")
        return

    print(f"{name}: listing snapshots for {todo[0]} -> {todo[-1]} ...")
    snaps = list_snapshots(session, outlet["url"], todo[0], todo[-1], run["max_retries"])
    print(f"{name}: {len(snaps)} candidate snapshots")

    for day in tqdm(todo, desc=name):
        base = {"outlet": name, "date": day.isoformat()}
        pick = pick_nearest(snaps, day, tz, outlet["target_local_time"],
                            outlet["max_hours_off"])
        if pick is None:
            log_coverage({**base, "status": "no_snapshot", "snapshot_ts": None, "n_headlines": 0})
            continue

        ts, original = pick
        ts_str = ts.strftime("%Y%m%d%H%M%S")
        r = get_with_retry(session, SNAP_URL.format(ts=ts_str, url=original),
                           max_retries=run["max_retries"], timeout=90)
        time.sleep(run["request_delay_s"])
        if r is None:
            log_coverage({**base, "status": "fetch_failed", "snapshot_ts": ts.isoformat(),
                          "n_headlines": 0})
            continue

        html_path = HTML_DIR / name / f"{day.isoformat()}.html.gz"
        html_path.parent.mkdir(parents=True, exist_ok=True)
        with gzip.open(html_path, "wb") as f:
            f.write(r.content)

        rows = parse_headlines(r.content, original, outlet.get("headline_selector"))
        if not rows:
            log_coverage({**base, "status": "parse_empty", "snapshot_ts": ts.isoformat(),
                          "n_headlines": 0})
            continue

        df = pd.DataFrame(rows)
        df.insert(0, "outlet", name)
        df.insert(1, "date", day.isoformat())
        df.insert(2, "snapshot_ts", ts)
        out = FP_DIR / f"outlet={name}" / f"date={day.isoformat()}" / "part.parquet"
        out.parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(out, index=False)
        log_coverage({**base, "status": "ok", "snapshot_ts": ts.isoformat(),
                      "n_headlines": len(df)})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--outlets", nargs="*", help="outlet names (default: all in config)")
    ap.add_argument("--start", help="YYYY-MM-DD inclusive")
    ap.add_argument("--end", help="YYYY-MM-DD exclusive")
    args = ap.parse_args()

    run = load_yaml("run.yaml")
    outlets = load_yaml("target_outlets.yaml")["outlets"]
    if args.outlets:
        outlets = [o for o in outlets if o["name"] in args.outlets]
    days = list(daterange(as_date(args.start or run["start_date"]),
                          as_date(args.end or run["end_date"])))

    session = requests.Session()
    session.headers["User-Agent"] = run["user_agent"]
    done = load_done()

    for outlet in outlets:
        process_outlet(session, outlet, days, run, done)
    consolidate_coverage()


if __name__ == "__main__":
    main()
