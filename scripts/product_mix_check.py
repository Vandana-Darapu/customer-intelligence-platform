import os
import pandas as pd
from dotenv import load_dotenv
import pymysql
load_dotenv()
c = pymysql.connect(host=os.getenv("MYSQL_HOST"), port=int(os.getenv("MYSQL_PORT")),
    user=os.getenv("MYSQL_USER"), password=os.getenv("MYSQL_PASSWORD"),
    database=os.getenv("MYSQL_DATABASE"), charset="utf8mb4")
cur = c.cursor()
pat = "wig|toupee|hair extension|human hair|lace front|clip in|clip-in|lashes"
cur.execute("""
    SELECT d.year,
           CASE WHEN p.product_title REGEXP %s THEN 'hairpiece_lash' ELSE 'other' END AS grp,
           COUNT(*) AS n,
           SUM(f.rating = 1) AS one_star
    FROM fact_reviews f
    JOIN dim_date d ON f.date_key = d.date_key
    JOIN dim_product p ON f.product_key = p.product_key
    WHERE d.year BETWEEN 2015 AND 2022
    GROUP BY d.year, grp
""", (pat,))
df = pd.DataFrame(cur.fetchall(), columns=["year", "grp", "n", "one_star"])
c.close()
df[["n", "one_star"]] = df[["n", "one_star"]].astype(int)
t = df.pivot(index="year", columns="grp", values=["n", "one_star"]).fillna(0)
res = pd.DataFrame(index=t.index)
res["reviews_total"] = t["n"].sum(axis=1)
res["hairpiece_share_%"] = (t["n"]["hairpiece_lash"] / res["reviews_total"] * 100).round(1)
res["1star_%_hairpiece"] = (t["one_star"]["hairpiece_lash"] / t["n"]["hairpiece_lash"] * 100).round(1)
res["1star_%_other"] = (t["one_star"]["other"] / t["n"]["other"] * 100).round(1)
res["1star_%_overall"] = (t["one_star"].sum(axis=1) / res["reviews_total"] * 100).round(1)
print(res.to_string())
res.to_csv("reports/product_mix_check.csv")
