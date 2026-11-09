import os
import pandas as pd
from dotenv import load_dotenv
import pymysql
load_dotenv()
c = pymysql.connect(host=os.getenv("MYSQL_HOST"), port=int(os.getenv("MYSQL_PORT")),
    user=os.getenv("MYSQL_USER"), password=os.getenv("MYSQL_PASSWORD"),
    database=os.getenv("MYSQL_DATABASE"), charset="utf8mb4")
cur = c.cursor()
# Check 1: same products, 2015 vs 2021
cur.execute("""
    SELECT d.year, f.product_key, COUNT(*) AS n, SUM(f.rating = 1) AS one_star
    FROM fact_reviews f JOIN dim_date d ON f.date_key = d.date_key
    WHERE d.year IN (2015, 2021)
    GROUP BY d.year, f.product_key
""")
p = pd.DataFrame(cur.fetchall(), columns=["year", "product_key", "n", "one_star"])
p[["n", "one_star"]] = p[["n", "one_star"]].astype(int)
a = p[p.year == 2015].set_index("product_key")[["n", "one_star"]]
b = p[p.year == 2021].set_index("product_key")[["n", "one_star"]]
both = a.join(b, lsuffix="_15", rsuffix="_21", how="inner")
both = both[(both.n_15 >= 10) & (both.n_21 >= 10)]
r15 = both.one_star_15 / both.n_15 * 100
r21 = both.one_star_21 / both.n_21 * 100
print("Products with 10+ reviews in both years:", len(both))
print("Pooled 1-star %: 2015 =", round(both.one_star_15.sum() / both.n_15.sum() * 100, 1),
      "| 2021 =", round(both.one_star_21.sum() / both.n_21.sum() * 100, 1))
print("Average per-product 1-star %: 2015 =", round(r15.mean(), 1), "| 2021 =", round(r21.mean(), 1))
print("Products whose 1-star % rose:", int((r21 > r15).sum()), "of", len(both))
# Check 2: verified purchase share and 1-star rate by year
cur.execute("""
    SELECT d.year, f.verified_purchase, COUNT(*) AS n, SUM(f.rating = 1) AS one_star
    FROM fact_reviews f JOIN dim_date d ON f.date_key = d.date_key
    WHERE d.year BETWEEN 2015 AND 2022
    GROUP BY d.year, f.verified_purchase
""")
v = pd.DataFrame(cur.fetchall(), columns=["year", "verified", "n", "one_star"])
c.close()
v[["verified", "n", "one_star"]] = v[["verified", "n", "one_star"]].astype(int)
tot = v.groupby("year").n.sum()
ver = v[v.verified == 1].set_index("year")
unv = v[v.verified == 0].set_index("year")
res = pd.DataFrame({
    "verified_share_%": (ver.n / tot * 100).round(1),
    "1star_%_verified": (ver.one_star / ver.n * 100).round(1),
    "1star_%_unverified": (unv.one_star / unv.n * 100).round(1),
})
print("\nVerified purchase check:")
print(res.to_string())
