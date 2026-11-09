import os
from pathlib import Path
from dotenv import load_dotenv
import pymysql
load_dotenv(Path(__file__).resolve().parents[1] / ".env")
c = pymysql.connect(host=os.getenv("MYSQL_HOST"), port=int(os.getenv("MYSQL_PORT")),
    user=os.getenv("MYSQL_USER"), password=os.getenv("MYSQL_PASSWORD"),
    database=os.getenv("MYSQL_DATABASE"), charset="utf8mb4")
cur = c.cursor()
cur.execute("""SELECT p.product_title, COUNT(*) AS one_star
FROM fact_reviews f JOIN dim_product p ON p.product_key = f.product_key
WHERE f.rating = 1 GROUP BY p.product_key, p.product_title
ORDER BY one_star DESC LIMIT 10""")
for title, n in cur.fetchall():
    print(f"{n:>6,}  {(title or '')[:80]}")
