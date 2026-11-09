"""Load cleaned Parquet into the MySQL star schema. Safe to re-run."""
import calendar
import datetime as dt
import os
from pathlib import Path
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.dataset as ds
import pymysql
from dotenv import load_dotenv
ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")
BATCH = 5_000
def connect():
    return pymysql.connect(
        host=os.getenv("MYSQL_HOST", "localhost"),
        port=int(os.getenv("MYSQL_PORT", "3306")),
        user=os.getenv("MYSQL_USER"),
        password=os.getenv("MYSQL_PASSWORD"),
        database=os.getenv("MYSQL_DATABASE"),
        charset="utf8mb4",
    )
def dataset(name):
    return ds.dataset(str(ROOT / "data" / "processed" / name), format="parquet", partitioning="hive")
def cut(s, n):
    return s[:n] if isinstance(s, str) else s
def num(x):
    return None if x is None or x != x else x
def load_products(conn):
    cols = ["parent_asin", "source_category", "main_category", "product_title", "store",
            "price", "has_price", "price_outlier", "listing_avg_rating", "listing_rating_count"]
    sql = ("INSERT IGNORE INTO dim_product (parent_asin, source_category, main_category, "
           "product_title, store, price, has_price, price_outlier, listing_avg_rating, "
           "listing_rating_count) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)")
    total = 0
    with conn.cursor() as cur:
        for batch in dataset("products").to_batches(columns=cols, batch_size=BATCH, use_threads=False):
            d = batch.to_pydict()
            rows = []
            for i in range(batch.num_rows):
                price = num(d["price"][i])
                if price is not None and abs(price) >= 1e8:
                    price = None
                rows.append((
                    d["parent_asin"][i], d["source_category"][i],
                    cut(d["main_category"][i], 100), cut(d["product_title"][i], 1000),
                    cut(d["store"][i], 255), price,
                    int(bool(d["has_price"][i])), int(bool(d["price_outlier"][i])),
                    num(d["listing_avg_rating"][i]), d["listing_rating_count"][i],
                ))
            cur.executemany(sql, rows)
            conn.commit()
            total += len(rows)
            print(f"\rdim_product: {total:,} rows read", end="")
    print()
def load_dates(conn):
    col = dataset("reviews").to_table(columns=["review_date"]).column("review_date")
    mm = pc.min_max(col)
    lo, hi = mm["min"].as_py(), mm["max"].as_py()
    rows, d = [], lo
    while d <= hi:
        rows.append((d.year * 10000 + d.month * 100 + d.day, d, d.year,
                     (d.month - 1) // 3 + 1, d.month, calendar.month_name[d.month]))
        d += dt.timedelta(days=1)
    sql = ("INSERT IGNORE INTO dim_date (date_key, full_date, year, quarter, month, month_name) "
           "VALUES (%s,%s,%s,%s,%s,%s)")
    with conn.cursor() as cur:
        cur.executemany(sql, rows)
    conn.commit()
    print(f"dim_date: {len(rows):,} days ({lo} to {hi})")
def product_keys(conn):
    with conn.cursor() as cur:
        cur.execute("SELECT parent_asin, product_key FROM dim_product")
        return dict(cur.fetchall())
def load_reviews(conn, pmap):
    cols = ["parent_asin", "user_id", "rating", "sentiment_label", "verified_purchase",
            "helpful_vote", "has_text", "text_length", "review_ts", "review_date",
            "title", "text"]
    fact_sql = ("INSERT IGNORE INTO fact_reviews (review_id, product_key, date_key, user_id, "
                "rating, sentiment_label, verified_purchase, helpful_vote, has_text, "
                "text_length, review_ts) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)")
    text_sql = ("INSERT IGNORE INTO review_text (review_id, review_title, review_body) "
                "VALUES (%s,%s,%s)")
    with conn.cursor() as cur:
        cur.execute("SELECT COALESCE(MAX(review_id), 0) FROM fact_reviews")
        done = cur.fetchone()[0]
    if done:
        print(f"Resuming after review_id {done:,}")
    offset = loaded = skipped = 0
    scan = dataset("reviews").to_batches(columns=cols, batch_size=BATCH, use_threads=False)
    with conn.cursor() as cur:
        for batch in scan:
            n = batch.num_rows
            if offset + n <= done:          # this batch is already loaded
                offset += n
                continue
            idx = {name: batch.schema.get_field_index(name) for name in cols}
            col = lambda name: batch.column(idx[name]).to_pylist()
            ts = batch.column(idx["review_ts"]).cast(pa.timestamp("us"), safe=False).to_pylist()
            asin, user, rating = col("parent_asin"), col("user_id"), col("rating")
            sent, vp, hv = col("sentiment_label"), col("verified_purchase"), col("helpful_vote")
            has_text, tlen, rdate = col("has_text"), col("text_length"), col("review_date")
            title, text = col("title"), col("text")
            facts, texts = [], []
            for i in range(n):
                rid = offset + i + 1
                pk, r, d = pmap.get(asin[i]), num(rating[i]), rdate[i]
                if pk is None or r is None or d is None or ts[i] is None or user[i] is None or sent[i] is None:
                    skipped += 1
                    continue
                facts.append((rid, pk, d.year * 10000 + d.month * 100 + d.day, user[i],
                              int(round(r)), sent[i],
                              None if vp[i] is None else int(bool(vp[i])), hv[i],
                              int(bool(has_text[i])), tlen[i], ts[i]))
                if title[i] or text[i]:
                    texts.append((rid, cut(title[i], 1000), text[i]))
            cur.executemany(fact_sql, facts)
            if texts:
                cur.executemany(text_sql, texts)
            conn.commit()
            offset += n
            loaded += len(facts)
            print(f"\rfact_reviews: {offset:,} rows processed", end="")
    print(f"\nLoaded this run: {loaded:,} | skipped (missing key/value): {skipped:,}")
def verify(conn):
    print("\n=== Row counts in MySQL ===")
    with conn.cursor() as cur:
        for t in ["dim_product", "dim_date", "fact_reviews", "review_text"]:
            cur.execute(f"SELECT COUNT(*) FROM {t}")
            print(f"{t:14s} {cur.fetchone()[0]:>10,}")
    print("Expected: dim_product 112,590 | fact_reviews 694,252")
def main():
    conn = connect()
    try:
        load_products(conn)
        load_dates(conn)
        load_reviews(conn, product_keys(conn))
        verify(conn)
    finally:
        conn.close()
if __name__ == "__main__":
    main()
