import glob
import pandas as pd

watch = ["thehill.com", "bloomberg.com"]
days, present = [], {k: [] for k in watch}
for f in sorted(glob.glob("data/raw/gkg/date=*/part.parquet")):
    try:
        s = set(pd.read_parquet(f, columns=["source"])["source"])
    except Exception:
        continue  # file still being written
    day = f.split("date=")[1].split("/")[0]
    days.append(day)
    for k in watch:
        if k in s:
            present[k].append(day)

for k in watch:
    miss = pd.to_datetime([d for d in days if d not in present[k]])
    print(k, "missing on", len(miss), "of", len(days), "days")
    if len(miss):
        span = (miss.max() - miss.min()).days + 1
        print("  first/last missing:", miss.min().date(), miss.max().date())
        print("  one contiguous block:", span == len(miss))
