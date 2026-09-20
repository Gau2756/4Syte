import glob
import sys
import pyarrow.parquet as pq

tables = sys.argv[1:] or ["gkg", "events", "mentions"]
for t in tables:
    files = sorted(glob.glob(f"data/raw/{t}/date=*/part.parquet"))
    rows, bad, empty = 0, [], []
    for f in files:
        try:
            n = pq.ParquetFile(f).metadata.num_rows
        except Exception:
            bad.append(f)
            continue
        rows += n
        if n == 0:
            empty.append(f.split("date=")[1].split("/")[0])
    print(f"{t}: {len(files)} files, {rows:,} rows, {len(bad)} unreadable, {len(empty)} empty days")
    for f in bad:
        print("  BAD:", f)
    if empty:
        print("  EMPTY:", ", ".join(empty))
