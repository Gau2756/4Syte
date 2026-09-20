from google.cloud import bigquery
from extract.common import load_yaml

CANDIDATES = [
    "independent.co.uk", "thehill.com", "cbc.ca", "nypost.com", "businessinsider.com",
    "time.com", "newsweek.com", "theatlantic.com", "vox.com", "axios.com", "slate.com",
    "thetimes.co.uk", "telegraph.co.uk", "news.sky.com", "dailymail.co.uk", "mirror.co.uk",
    "forbes.com", "cnbc.com", "huffpost.com", "msn.com", "pbs.org", "foxbusiness.com",
    "chicagotribune.com", "bostonglobe.com", "nydailynews.com", "sfchronicle.com",
    "seattletimes.com", "miamiherald.com", "usnews.com", "economist.com",
    "theconversation.com", "france24.com", "abc.net.au", "smh.com.au",
    "theglobeandmail.com", "euronews.com", "dw.com", "hindustantimes.com",
    "thehindu.com", "politico.eu", "bloomberg.com", "nytimes.com", "washingtonpost.com",
]

client = bigquery.Client(project=load_yaml("run.yaml")["gcp_project"])
sql = """
SELECT SourceCommonName AS source,
       COUNT(*) AS n,
       COUNT(DISTINCT DATE(_PARTITIONTIME)) AS days_present
FROM `gdelt-bq.gdeltv2.gkg_partitioned`
WHERE _PARTITIONTIME >= TIMESTAMP('2025-09-02')
  AND _PARTITIONTIME <  TIMESTAMP('2025-09-09')
  AND SourceCommonName IN UNNEST(@c)
GROUP BY 1 ORDER BY n DESC
"""
cfg = bigquery.QueryJobConfig(
    query_parameters=[bigquery.ArrayQueryParameter("c", "STRING", CANDIDATES)]
)
found = {}
for r in client.query(sql, job_config=cfg).result():
    found[r.source] = (r.n, r.days_present)
    print(f"{r.n:6d} rows  {r.days_present}/7 days  {r.source}")
print("\nNOT FOUND:", ", ".join(c for c in CANDIDATES if c not in found))
