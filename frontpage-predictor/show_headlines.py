import glob
import pandas as pd
files = sorted(glob.glob("data/raw/frontpage/outlet=nytimes/date=*/part.parquet"))
df = pd.concat(pd.read_parquet(f) for f in files)
print(df.groupby("date").size().describe().round(1))
last = df[df["date"] == df["date"].max()]
pd.set_option("display.width", 200, "display.max_colwidth", 90)
print(last[["position_rank", "headline", "section", "kind", "url_date"]].to_string(index=False))
