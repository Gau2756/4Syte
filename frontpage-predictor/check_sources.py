import glob, os
import pandas as pd
import yaml

rows = []
for f in sorted(glob.glob("data/raw/gkg/date=*/part.parquet")):
    try:
        s = pd.read_parquet(f, columns=["source"])["source"].value_counts()
    except Exception:
        continue  # file still being written
    day = os.path.basename(os.path.dirname(f)).split("=")[1]
    rows.append(pd.DataFrame({"day": day, "source": s.index, "n": s.values}))

d = pd.concat(rows)
n_days = d["day"].nunique()
t = d.groupby("source").agg(rows=("n", "sum"), days=("day", "nunique"))
t["pct_days"] = (100 * t["days"] / n_days).round(0)
print(n_days, "days read")
print(t.sort_values("rows", ascending=False).to_string())

want = yaml.safe_load(open("config/sources.yaml"))["sources"]
print("\nMISSING ENTIRELY:", [w for w in want if w not in t.index])
