"""Clean raw Amazon review and product files with PySpark; write Parquet."""
import logging
import os
import sys
import time
from pathlib import Path
from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import (
    BooleanType,
    DoubleType,
    LongType,
    StringType,
    StructField,
    StructType,
)
os.environ["PYSPARK_PYTHON"] = sys.executable
os.environ["PYSPARK_DRIVER_PYTHON"] = sys.executable
PROJECT_ROOT = Path(__file__).resolve().parents[3]
log = logging.getLogger("clean_data")
REVIEW_SCHEMA = StructType([
    StructField("rating", DoubleType()),
    StructField("title", StringType()),
    StructField("text", StringType()),
    StructField("parent_asin", StringType()),
    StructField("user_id", StringType()),
    StructField("timestamp", LongType()),
    StructField("verified_purchase", BooleanType()),
    StructField("helpful_vote", LongType()),
])
META_SCHEMA = StructType([
    StructField("parent_asin", StringType()),
    StructField("main_category", StringType()),
    StructField("title", StringType()),
    StructField("average_rating", DoubleType()),
    StructField("rating_number", LongType()),
    StructField("price", DoubleType()),
    StructField("store", StringType()),
])
def pct(part, whole):
    return f"{part / whole:.2%}" if whole else "n/a"
def build_spark():
    tmp = PROJECT_ROOT / "data" / "interim" / "spark_tmp"
    tmp.mkdir(parents=True, exist_ok=True)
    return (
        SparkSession.builder.master("local[4]")
        .appName("clean_data")
        .config("spark.driver.memory", "4g")
        .config("spark.local.dir", str(tmp))
        .config("spark.sql.shuffle.partitions", "8")
        .config("spark.sql.session.timeZone", "UTC")
        .config("spark.sql.sources.partitionOverwriteMode", "dynamic")
        .getOrCreate()
    )
def clean_reviews(spark, category):
    raw_path = PROJECT_ROOT / "data" / "raw" / f"{category}.jsonl.gz"
    raw = spark.read.schema(REVIEW_SCHEMA).json(str(raw_path)).cache()
    raw_count = raw.count()
    log.info("Reviews read: %s", f"{raw_count:,}")
    bad = raw.filter(
        F.col("rating").isNull()
        | F.col("timestamp").isNull()
        | F.col("parent_asin").isNull()
    ).count()
    log.info("Rows missing rating, timestamp or product id: %s", f"{bad:,}")
    keys = ["user_id", "parent_asin", "timestamp", "rating", "title", "text"]
    deduped = raw.dropna(subset=["rating", "timestamp", "parent_asin"]).dropDuplicates(keys).cache()
    kept = deduped.count()
    log.info(
        "Exact duplicates removed: %s -> %s rows remain",
        f"{raw_count - bad - kept:,}",
        f"{kept:,}",
    )
    clean = (
        deduped.withColumnRenamed("timestamp", "timestamp_ms")
        .withColumn("review_ts", (F.col("timestamp_ms") / 1000).cast("timestamp"))
        .withColumn("review_date", F.to_date("review_ts"))
        .withColumn("review_year", F.year("review_ts"))
        .withColumn(
            "has_text",
            F.coalesce(F.length(F.trim(F.col("text"))) > 0, F.lit(False)),
        )
        .withColumn("text_length", F.length("text"))
        .withColumn(
            "sentiment_label",
            F.when(F.col("rating") <= 2, "negative")
            .when(F.col("rating") == 3, "neutral")
            .when(F.col("rating") >= 4, "positive"),
        )
        .withColumn("source_category", F.lit(category))
    )
    out = PROJECT_ROOT / "data" / "processed" / "reviews"
    clean.write.mode("overwrite").partitionBy("source_category").parquet(str(out))
    written = spark.read.parquet(str(out / f"source_category={category}")).count()
    level = logging.INFO if written == kept else logging.WARNING
    log.log(level, "Rows read back from Parquet: %s (expected %s)", f"{written:,}", f"{kept:,}")
    no_text = clean.filter(~F.col("has_text")).count()
    log.info("Reviews without text: %s (%s)", f"{no_text:,}", pct(no_text, kept))
    for row in clean.groupBy("sentiment_label").count().orderBy("sentiment_label").collect():
        log.info("Sentiment %s: %s (%s)", row["sentiment_label"], f"{row['count']:,}", pct(row["count"], kept))
    return clean
def clean_products(spark, category):
    raw_path = PROJECT_ROOT / "data" / "raw" / f"meta_{category}.jsonl.gz"
    raw = spark.read.schema(META_SCHEMA).json(str(raw_path))
    raw_count = raw.count()
    deduped = raw.dropDuplicates(["parent_asin"])
    kept = deduped.count()
    log.info("Products read: %s, after removing duplicate ids: %s", f"{raw_count:,}", f"{kept:,}")
    quantiles = deduped.approxQuantile("price", [0.25, 0.75], 0.001)
    fence = None
    if len(quantiles) == 2:
        q1, q3 = quantiles
        fence = q3 + 1.5 * (q3 - q1)
        log.info("Price outlier fence (Q3 + 1.5 x IQR): %.2f", fence)
    outlier = (
        F.coalesce(F.col("price") > F.lit(fence), F.lit(False))
        if fence is not None
        else F.lit(False)
    )
    clean = (
        deduped.withColumnRenamed("title", "product_title")
        .withColumnRenamed("average_rating", "listing_avg_rating")
        .withColumnRenamed("rating_number", "listing_rating_count")
        .withColumn(
            "store",
            F.when(F.trim(F.col("store")) == "", F.lit(None).cast("string")).otherwise(F.col("store")),
        )
        .withColumn("has_price", F.col("price").isNotNull())
        .withColumn("price_outlier", outlier)
        .withColumn("source_category", F.lit(category))
    )
    out = PROJECT_ROOT / "data" / "processed" / "products"
    clean.write.mode("overwrite").partitionBy("source_category").parquet(str(out))
    written = spark.read.parquet(str(out / f"source_category={category}")).count()
    level = logging.INFO if written == kept else logging.WARNING
    log.log(level, "Products read back from Parquet: %s (expected %s)", f"{written:,}", f"{kept:,}")
    with_price = clean.filter(F.col("has_price")).count()
    outliers = clean.filter(F.col("price_outlier")).count()
    log.info("Products with a price: %s (%s)", f"{with_price:,}", pct(with_price, kept))
    log.info("Products flagged as price outliers: %s", f"{outliers:,}")
    return clean
def main():
    category = sys.argv[1] if len(sys.argv) > 1 else "All_Beauty"
    (PROJECT_ROOT / "reports").mkdir(exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(PROJECT_ROOT / "reports" / f"clean_{category}.log", mode="w", encoding="utf-8"),
        ],
        force=True,
    )
    for name in (f"{category}.jsonl.gz", f"meta_{category}.jsonl.gz"):
        if not (PROJECT_ROOT / "data" / "raw" / name).exists():
            log.error("Missing raw file: %s. Run scripts/download_data.py first.", name)
            sys.exit(1)
    start = time.perf_counter()
    log.info("Cleaning category: %s", category)
    spark = build_spark()
    spark.sparkContext.setLogLevel("ERROR")
    reviews = clean_reviews(spark, category)
    products = clean_products(spark, category)
    unmatched = reviews.join(products.select("parent_asin"), "parent_asin", "left_anti").count()
    log.info("Cleaned reviews with no matching product: %s (expected 0)", f"{unmatched:,}")
    log.info("Finished in %.0f seconds", time.perf_counter() - start)
    spark.stop()
if __name__ == "__main__":
    main()
