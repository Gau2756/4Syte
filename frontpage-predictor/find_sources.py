from google.cloud import bigquery
from extract.common import load_yaml

client = bigquery.Client(project=load_yaml("run.yaml")["gcp_project"])
sql = r"""
SELECT SourceCommonName, COUNT(*) AS n
FROM `gdelt-bq.gdeltv2.gkg_partitioned`
WHERE _PARTITIONTIME >= TIMESTAMP('2025-09-02')
  AND _PARTITIONTIME <  TIMESTAMP('2025-09-03')
  AND REGEXP_CONTAINS(SourceCommonName,
      r'wsj|washingtonpost|apnews|bloomberg|abcnews|usatoday|politico|(^|\.)ft\.com')
GROUP BY 1 ORDER BY n DESC
"""
for row in client.query(sql).result():
    print(row.SourceCommonName, row.n)
