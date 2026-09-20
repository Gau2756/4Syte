import gzip, re
import pandas as pd
from bs4 import BeautifulSoup

cov = pd.read_parquet("data/interim/coverage.parquet")
print(cov.groupby(["outlet", "status"]).size())
print(cov[cov.status == "ok"]["n_headlines"].describe())
print()

html = gzip.open("data/raw/wayback_html/nytimes/2026-08-27.html.gz").read()
soup = BeautifulSoup(html, "lxml")
print("html bytes:", len(html))
print("heading tags:", {t: len(soup.find_all(t)) for t in ("h1", "h2", "h3", "h4")})

pat = re.compile(r"/\d{4}/\d{2}/\d{2}/")
links = soup.find_all("a", href=pat)
print("date-pattern links:", len(links), "| unique:", len({a["href"] for a in links}))
print()
for a in links[:15]:
    kids = [c.name for c in a.find_all(True, recursive=False)]
    print(a["href"][:75])
    print("   text:", a.get_text(" ", strip=True)[:90])
    print("   children:", kids, "| parent:", a.parent.name, a.parent.get("class"))
