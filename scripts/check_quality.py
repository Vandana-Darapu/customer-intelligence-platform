"""Check empty text/title and duplicate reviews. Read-only."""
import gzip
import json
import sys
from pathlib import Path
import pandas as pd
PROJECT_ROOT = Path(__file__).resolve().parents[1]
category = sys.argv[1] if len(sys.argv) > 1 else "All_Beauty"
path = PROJECT_ROOT / "data" / "raw" / f"{category}.jsonl.gz"
rows = []
with gzip.open(path, "rt", encoding="utf-8") as f:
    for line in f:
        rec = json.loads(line)
        rows.append({
            "rating": rec.get("rating"),
            "title": rec.get("title"),
            "text": rec.get("text"),
            "parent_asin": rec.get("parent_asin"),
            "user_id": rec.get("user_id"),
            "timestamp": rec.get("timestamp"),
        })
df = pd.DataFrame(rows)
total = len(df)
empty_text = df["text"].fillna("").str.strip().eq("")
empty_title = df["title"].fillna("").str.strip().eq("")
print(f"Rows: {total:,}")
print(f"Empty text:  {empty_text.sum():,} ({empty_text.mean():.2%})")
print(f"Empty title: {empty_title.sum():,} ({empty_title.mean():.2%})")
print(f"Empty text AND empty title: {(empty_text & empty_title).sum():,}")
print("\nRating split among empty-text reviews:")
print(df.loc[empty_text, "rating"].value_counts(normalize=True).sort_index().round(4))
key = ["user_id", "parent_asin", "timestamp"]
full_key = key + ["rating", "title", "text"]
print(f"\nExtra copies sharing user+product+timestamp: {df.duplicated(subset=key).sum():,}")
print(f"Extra copies that are exact duplicates:      {df.duplicated(subset=full_key).sum():,}")
