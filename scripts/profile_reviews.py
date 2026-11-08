"""Profile a raw Amazon reviews file. Read-only: changes nothing."""
import gzip
import json
import sys
from pathlib import Path
import pandas as pd
PROJECT_ROOT = Path(__file__).resolve().parents[1]
category = sys.argv[1] if len(sys.argv) > 1 else "All_Beauty"
path = PROJECT_ROOT / "data" / "raw" / f"{category}.jsonl.gz"
rows = []
first_keys = None
with gzip.open(path, "rt", encoding="utf-8") as f:
    for line in f:
        rec = json.loads(line)
        if first_keys is None:
            first_keys = list(rec.keys())
        rows.append({
            "rating": rec.get("rating"),
            "title": rec.get("title"),
            "text": rec.get("text"),
            "parent_asin": rec.get("parent_asin"),
            "user_id": rec.get("user_id"),
            "timestamp": rec.get("timestamp", rec.get("sort_timestamp")),
            "verified_purchase": rec.get("verified_purchase"),
            "helpful_vote": rec.get("helpful_vote", rec.get("helpful_votes")),
        })
df = pd.DataFrame(rows)
pd.set_option("display.width", 120)
print(f"\n=== Profile: {category} ===")
print("Field names in first record:", first_keys)
print(f"\nRows: {len(df):,}")
print("\nColumn types:")
print(df.dtypes)
print("\nMissing values per column:")
print(df.isna().sum())
print("\nRating distribution (share of reviews):")
print(df["rating"].value_counts(normalize=True).sort_index().round(4))
ts = df["timestamp"].dropna()
unit = "ms" if ts.max() > 1e12 else "s"
dates = pd.to_datetime(ts, unit=unit)
print(f"\nTimestamp unit detected: {unit}")
print("Earliest review:", dates.min())
print("Latest review:  ", dates.max())
print("\nReviews per year:")
print(dates.dt.year.value_counts().sort_index())
print("\nVerified purchase:")
print(df["verified_purchase"].value_counts(dropna=False))
print("\nHelpful votes:")
print(df["helpful_vote"].describe())
print("\nReview text length (characters):")
print(df["text"].fillna("").str.len().describe())
print(f"\nUnique products (parent_asin): {df['parent_asin'].nunique():,}")
print(f"Unique reviewers (user_id):    {df['user_id'].nunique():,}")
dupes = df.duplicated(subset=["user_id", "parent_asin", "timestamp"]).sum()
print(f"Possible duplicate reviews (same user, product, timestamp): {dupes:,}")
