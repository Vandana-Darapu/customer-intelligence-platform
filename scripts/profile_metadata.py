"""Profile the metadata file and its join coverage to reviews. Read-only."""
import gzip
import json
import sys
from collections import Counter
from pathlib import Path
import pandas as pd
PROJECT_ROOT = Path(__file__).resolve().parents[1]
category = sys.argv[1] if len(sys.argv) > 1 else "All_Beauty"
raw = PROJECT_ROOT / "data" / "raw"
pd.set_option("display.width", 120)
meta_rows = []
price_types = Counter()
with gzip.open(raw / f"meta_{category}.jsonl.gz", "rt", encoding="utf-8") as f:
    for line in f:
        rec = json.loads(line)
        price_types[type(rec.get("price")).__name__] += 1
        meta_rows.append({
            "parent_asin": rec.get("parent_asin"),
            "main_category": rec.get("main_category"),
            "title": rec.get("title"),
            "average_rating": rec.get("average_rating"),
            "rating_number": rec.get("rating_number"),
            "price": rec.get("price"),
            "store": rec.get("store"),
            "category_levels": len(rec.get("categories") or []),
        })
meta = pd.DataFrame(meta_rows)
print(f"\n=== Metadata profile: {category} ===")
print(f"Metadata rows: {len(meta):,}")
print(f"Unique parent_asin: {meta['parent_asin'].nunique():,}")
print(f"Duplicate parent_asin rows: {meta['parent_asin'].duplicated().sum():,}")
print("\nMissing values per column:")
print(meta.isna().sum())
print(f"\nEmpty store text: {(meta['store'].fillna('').str.strip() == '').sum():,}")
print("\nPython types found in price field:", dict(price_types))
price = pd.to_numeric(meta["price"], errors="coerce")
print(f"Numeric prices: {price.notna().sum():,}")
print(f"Non-null but not numeric prices: {meta['price'].notna().sum() - price.notna().sum():,}")
print("\nPrice summary (numeric only):")
print(price.describe())
print("\nAverage rating summary:")
print(pd.to_numeric(meta["average_rating"], errors="coerce").describe())
print("\nTop main_category values:")
print(meta["main_category"].value_counts(dropna=False).head(10))
print("\nCategory depth (levels in categories list):")
print(meta["category_levels"].value_counts().sort_index())
review_asins = []
with gzip.open(raw / f"{category}.jsonl.gz", "rt", encoding="utf-8") as f:
    for line in f:
        review_asins.append(json.loads(line).get("parent_asin"))
reviews = pd.Series(review_asins)
covered = reviews.isin(set(meta["parent_asin"]))
print("\n=== Join coverage ===")
print(f"Review rows with matching metadata: {covered.sum():,} of {len(reviews):,} ({covered.mean():.2%})")
print(f"Reviewed products with metadata: {reviews[covered].nunique():,} of {reviews.nunique():,}")
