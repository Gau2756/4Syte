from google.cloud import bigquery
from extract.common import load_yaml

client = bigquery.Client(project=load_yaml("run.yaml")["gcp_project"])
sql = """
SELECT SourceCommonName, COUNT(*) AS n
FROM `gdelt-bq.gdeltv2.gkg_partitioned`
WHERE _PARTITIONTIME >= TIMESTAMP('2025-09-02')
  AND _PARTITIONTIME <  TIMESTAMP('2025-09-03')
GROUP BY 1 ORDER BY n DESC LIMIT 150
"""
for row in client.query(sql).result():
    print(f"{row.n:6d}  {row.SourceCommonName}")
