"""
Pull GDELT 2.0 GKG / Events / Mentions from BigQuery, one day-partition at a time,
and write Parquet to data/raw/<table>/date=YYYY-MM-DD/part.parquet.

Features
  * Resumable: days that already have a parquet file are skipped.
  * Cost-safe: --dry-run estimates bytes scanned; every query has a hard
    maximum_bytes_billed cap from config/run.yaml.
  * Partition = GDELT ingestion day (_PARTITIONTIME), NOT the event day.
    Downstream, apply your prediction cutoff using added_ts / mention_ts.

Usage
  python -m extract.gdelt_bigquery --dry-run
  python -m extract.gdelt_bigquery --tables gkg mentions events
  python -m extract.gdelt_bigquery --tables gkg --start 2026-06-01 --end 2026-06-08
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import time

from google.cloud import bigquery
from tqdm import tqdm

from .common import DATA, as_date, daterange, load_yaml

PART = (
    "_PARTITIONTIME >= TIMESTAMP(@day) "
    "AND _PARTITIONTIME < TIMESTAMP_ADD(TIMESTAMP(@day), INTERVAL 1 DAY)"
)

# NOTE: verify column names against the live schema before a big run:
#   bq show --schema --format=prettyjson gdelt-bq:gdeltv2.gkg_partitioned
SQL = {
    "gkg": f"""
        SELECT
          GKGRECORDID,
          PARSE_TIMESTAMP('%Y%m%d%H%M%S', CAST(DATE AS STRING)) AS added_ts,
          SourceCommonName AS source,
          DocumentIdentifier AS url,
          V2Themes, V2Persons, V2Organizations, V2Locations, V2Tone,
          REGEXP_EXTRACT(Extras, r'<PAGE_TITLE>(.*?)</PAGE_TITLE>') AS title
        FROM `gdelt-bq.gdeltv2.gkg_partitioned`
        WHERE {PART}
          AND SourceCommonName IN UNNEST(@sources)
    """,
    "events": f"""
        SELECT
          GLOBALEVENTID, SQLDATE,
          PARSE_TIMESTAMP('%Y%m%d%H%M%S', CAST(DATEADDED AS STRING)) AS added_ts,
          Actor1Code, Actor1Name, Actor1CountryCode,
          Actor2Code, Actor2Name, Actor2CountryCode,
          EventRootCode, EventCode, GoldsteinScale,
          NumMentions, NumSources, NumArticles, AvgTone,
          ActionGeo_FullName, ActionGeo_CountryCode, ActionGeo_Lat, ActionGeo_Long,
          SOURCEURL
        FROM `gdelt-bq.gdeltv2.events_partitioned`
        WHERE {PART}
          AND NumMentions >= @min_mentions
    """,
    "mentions": f"""
        SELECT
          GLOBALEVENTID,
          PARSE_TIMESTAMP('%Y%m%d%H%M%S', CAST(EventTimeDate AS STRING)) AS event_ts,
          PARSE_TIMESTAMP('%Y%m%d%H%M%S', CAST(MentionTimeDate AS STRING)) AS mention_ts,
          MentionSourceName AS source,
          MentionIdentifier AS url,
          Confidence, MentionDocTone
        FROM `gdelt-bq.gdeltv2.eventmentions_partitioned`
        WHERE {PART}
          AND MentionSourceName IN UNNEST(@sources)
    """,
}


def make_params(table: str, day: dt.date, sources: list[str], min_mentions: int):
    params = [bigquery.ScalarQueryParameter("day", "DATE", day)]
    if table in ("gkg", "mentions"):
        params.append(bigquery.ArrayQueryParameter("sources", "STRING", sources))
    if table == "events":
        params.append(bigquery.ScalarQueryParameter("min_mentions", "INT64", min_mentions))
    return params


def dry_run_bytes(client, table, day, sources, min_mentions) -> int:
    cfg = bigquery.QueryJobConfig(
        query_parameters=make_params(table, day, sources, min_mentions),
        dry_run=True,
        use_query_cache=False,
    )
    return client.query(SQL[table], job_config=cfg).total_bytes_processed


def pull_day(client, table, day, sources, min_mentions, max_bytes):
    cfg = bigquery.QueryJobConfig(
        query_parameters=make_params(table, day, sources, min_mentions),
        maximum_bytes_billed=max_bytes,
    )
    job = client.query(SQL[table], job_config=cfg)
    df = job.to_dataframe()
    return df, job.total_bytes_billed or 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tables", nargs="+", default=["gkg", "events", "mentions"],
                    choices=list(SQL))
    ap.add_argument("--start", help="YYYY-MM-DD (inclusive); default from run.yaml")
    ap.add_argument("--end", help="YYYY-MM-DD (exclusive); default from run.yaml")
    ap.add_argument("--dry-run", action="store_true",
                    help="estimate bytes scanned for the full range and exit")
    args = ap.parse_args()

    run = load_yaml("run.yaml")
    sources = load_yaml("sources.yaml")["sources"]
    start = as_date(args.start or run["start_date"])
    end = as_date(args.end or run["end_date"])
    days = list(daterange(start, end))
    max_bytes = int(run["max_bytes_billed_gb"] * 1024**3)
    min_mentions = int(run["min_event_mentions"])

    client = bigquery.Client(project=run["gcp_project"])

    if args.dry_run:
        # Estimate from the first day of the range and extrapolate.
        print(f"Range {start} -> {end} ({len(days)} days), {len(sources)} sources")
        total = 0
        for t in args.tables:
            b = dry_run_bytes(client, t, days[0], sources, min_mentions)
            est = b * len(days)
            total += est
            print(f"  {t:9s} {b / 1e9:8.2f} GB/day  ~{est / 1e12:6.3f} TB for range")
        print(f"  TOTAL     ~{total / 1e12:.3f} TB scanned "
              "(1 TB/month is free; day-to-day size varies)")
        return

    manifest = {"started": dt.datetime.utcnow().isoformat(), "tables": {}}
    for t in args.tables:
        stats = {"days_pulled": 0, "days_skipped": 0, "rows": 0, "bytes_billed": 0}
        for day in tqdm(days, desc=t):
            out = DATA / "raw" / t / f"date={day.isoformat()}" / "part.parquet"
            if out.exists():
                stats["days_skipped"] += 1
                continue
            df, billed = pull_day(client, t, day, sources, min_mentions, max_bytes)
            out.parent.mkdir(parents=True, exist_ok=True)
            df.to_parquet(out, index=False)
            stats["days_pulled"] += 1
            stats["rows"] += len(df)
            stats["bytes_billed"] += billed
            time.sleep(0.2)
        manifest["tables"][t] = stats
        print(t, stats)

    manifest.update(start=str(start), end=str(end), sources=sources,
                    min_event_mentions=min_mentions,
                    finished=dt.datetime.utcnow().isoformat())
    mdir = DATA / "raw" / "_manifests"
    mdir.mkdir(parents=True, exist_ok=True)
    (mdir / f"gdelt_{dt.datetime.utcnow():%Y%m%dT%H%M%S}.json").write_text(
        json.dumps(manifest, indent=2, default=str))


if __name__ == "__main__":
    main()
