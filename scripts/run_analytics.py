import os
from pathlib import Path
from dotenv import load_dotenv
import pymysql
load_dotenv(Path(__file__).resolve().parents[1] / ".env")
conn = pymysql.connect(host=os.getenv("MYSQL_HOST"), port=int(os.getenv("MYSQL_PORT")),
    user=os.getenv("MYSQL_USER"), password=os.getenv("MYSQL_PASSWORD"),
    database=os.getenv("MYSQL_DATABASE"), charset="utf8mb4")
QUERIES = [
("Worst products by 1-star RATE (min 100 reviews)", """
SELECT LEFT(p.product_title, 60) AS product, COUNT(*) AS reviews,
       ROUND(100 * AVG(f.rating = 1), 1) AS pct_1star,
       ROUND(AVG(f.rating), 2) AS avg_rating
FROM fact_reviews f JOIN dim_product p ON p.product_key = f.product_key
GROUP BY p.product_key, p.product_title
HAVING COUNT(*) >= 100
ORDER BY pct_1star DESC LIMIT 10"""),
("Reviews and average rating per year (2023 is partial, ends Sep 9)", """
SELECT d.year, COUNT(*) AS reviews, ROUND(AVG(f.rating), 2) AS avg_rating,
       ROUND(100 * AVG(f.rating = 1), 1) AS pct_1star
FROM fact_reviews f JOIN dim_date d ON d.date_key = f.date_key
GROUP BY d.year ORDER BY d.year"""),
("Verified vs unverified purchases", """
SELECT verified_purchase, COUNT(*) AS reviews,
       ROUND(AVG(rating), 2) AS avg_rating,
       ROUND(100 * AVG(rating = 1), 1) AS pct_1star
FROM fact_reviews GROUP BY verified_purchase"""),
]
with conn.cursor() as cur:
    for title, sql in QUERIES:
        print(f"\n=== {title} ===")
        cur.execute(sql)
        print(" | ".join(c[0] for c in cur.description))
        for row in cur.fetchall():
            print(" | ".join(str(v) for v in row))
conn.close()
