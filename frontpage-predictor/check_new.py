import pandas as pd
df = pd.read_parquet("data/raw/gkg/date=2025-09-02/part.parquet")
print(len(df), "rows,", df["source"].nunique(), "sources")
print(df["source"].value_counts())
