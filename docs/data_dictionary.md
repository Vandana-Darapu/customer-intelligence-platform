# Data dictionary: Amazon Reviews 2023 (All_Beauty)
Sources: field descriptions from the official dataset page (McAuley Lab, UC San Diego); counts from this project's own profiling reports in `reports/`. Figures are for the All_Beauty category only and will be re-measured for each new category.
## Reviews (kept columns)
| Column | Type | Observed in All_Beauty |
|---|---|---|
| rating | float | 1.0 to 5.0, no missing. 5 stars: 59.97%, 1 star: 14.55% |
| title | string | No missing, no empty titles |
| text | string | 720 empty (0.10%). Median length 102 characters, maximum 14,989 |
| parent_asin | string | Product ID, join key to metadata. 112,565 unique. 100% of reviews match a metadata row |
| user_id | string | Reviewer ID. 631,986 unique |
| timestamp | integer | Unix time in milliseconds. 2000-11-01 to 2023-09-09. Timezone not documented, treated as UTC |
| verified_purchase | boolean | True for 634,969 of 701,528 reviews (90.5%) |
| helpful_vote | integer | Median 0, 75th percentile 1, maximum 646 |
Dropped columns: `images` (large, not needed) and `asin` (the page says to use `parent_asin` to find product metadata).
Total reviews: 701,528. Exact duplicate reviews (same user, product, timestamp, rating, title and text): 7,276.
## Product metadata (kept columns)
| Column | Type | Observed in All_Beauty |
|---|---|---|
| parent_asin | string | 112,590 rows, all unique |
| main_category | string | No missing. Differs from the file category (for example "Premium Beauty") |
| title | string | No missing |
| average_rating | float | Product-page rating, 1.0 to 5.0, mean 3.88. May differ from the average of our review table |
| rating_number | integer | No missing |
| price | float | Missing for 94,886 of 112,590 (84.3%). Range 0.01 to 2,548.98, median 16.99 |
| store | string | Missing for 11,331 (10.1%) |
Not used: `categories` (empty list for all 112,590 products).
## Known limitations
- Price exists for only 15.7% of products, so price analysis covers a minority of products.
- 2023 reviews stop on 2023-09-09, so 2023 is a partial year.
- Star-rating sentiment labels are weak labels, not human-annotated sentiment.
