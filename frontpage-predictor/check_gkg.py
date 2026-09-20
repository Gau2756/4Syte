import pandas as pd
df = pd.read_parquet("data/raw/gkg/date=2025-09-01/part.parquet")
print(len(df))
print(df["source"].value_counts())
print("null titles:", df["title"].isna().mean())
print(df.head(3).T)
