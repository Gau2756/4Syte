"""Re-parse saved Wayback HTML into headline parquet files. No network needed.

Finds article links by URL pattern (a /YYYY/MM/DD/ date in the path), drops
related-link labels (too few words) and live-blog updates (#fragment), and
dedupes by URL. Run from the project root:

    python reparse_frontpages.py                  # all outlets in config
    python reparse_frontpages.py nytimes          # one outlet
"""
import gzip
import json
import re
import sys
from urllib.parse import urljoin, urlparse

import pandas as pd
from bs4 import BeautifulSoup

from extract.common import DATA, load_yaml
from extract.wayback_frontpages import (FP_DIR, HTML_DIR, COVERAGE_LOG,
                                        consolidate_coverage, log_coverage)

DEFAULT_RE = r"/(\d{4})/(\d{2})/(\d{2})/"
KINDS = {"live", "interactive", "video", "podcasts", "athletic"}


def parse(html, base_url, link_re, min_words):
    soup = BeautifulSoup(html, "lxml")
    rows, seen = [], set()
    for a in soup.find_all("a", href=True):
        if "#" in a["href"]:
            continue  # live-blog updates and in-page anchors
        url = urljoin(base_url, a["href"])
        m = link_re.search(url)
        if not m or url in seen:
            continue
        text = a.get_text(" ", strip=True)
        if len(text.split()) < min_words:
            continue  # "Obituary", "Photos and Videos", ...
        seen.add(url)
        parts = urlparse(url).path.strip("/").split("/")
        after = url[m.end():].split("/")[0] if m.re.groups >= 3 else None
        rows.append({
            "position_rank": len(rows) + 1,
            "headline": text,
            "subhead": None,
            "url": url,
            "section": after,
            "is_lead_story": len(rows) == 0,
            "url_date": "-".join(m.groups()[:3]) if m.re.groups >= 3 else None,
            "kind": parts[0] if parts and parts[0] in KINDS else "article",
        })
    return rows


def latest_snapshot_ts():
    out = {}
    if COVERAGE_LOG.exists():
        for line in COVERAGE_LOG.read_text().splitlines():
            r = json.loads(line)
            if r.get("snapshot_ts"):
                out[(r["outlet"], r["date"])] = r["snapshot_ts"]
    return out


def main():
    wanted = set(sys.argv[1:])
    outlets = load_yaml("target_outlets.yaml")["outlets"]
    snaps = latest_snapshot_ts()
    for o in outlets:
        if wanted and o["name"] not in wanted:
            continue
        link_re = re.compile(o.get("link_regex", DEFAULT_RE))
        min_words = o.get("min_words", 4)
        files = sorted((HTML_DIR / o["name"]).glob("*.html.gz"))
        print(f"{o['name']}: re-parsing {len(files)} saved pages")
        counts = []
        for f in files:
            day = f.name.replace(".html.gz", "")
            rows = parse(gzip.open(f).read(), o["url"], link_re, min_words)
            ts = snaps.get((o["name"], day))
            rec = {"outlet": o["name"], "date": day, "snapshot_ts": ts,
                   "n_headlines": len(rows)}
            if not rows:
                log_coverage({**rec, "status": "parse_empty"})
                continue
            df = pd.DataFrame(rows)
            df.insert(0, "outlet", o["name"])
            df.insert(1, "date", day)
            df.insert(2, "snapshot_ts", pd.to_datetime(ts))
            out = FP_DIR / f"outlet={o['name']}" / f"date={day}" / "part.parquet"
            out.parent.mkdir(parents=True, exist_ok=True)
            df.to_parquet(out, index=False)
            log_coverage({**rec, "status": "ok"})
            counts.append(len(rows))
        if counts:
            print(pd.Series(counts).describe().round(1).to_string())
    consolidate_coverage()


if __name__ == "__main__":
    main()
