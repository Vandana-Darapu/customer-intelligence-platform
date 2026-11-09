-- Analytics queries for the Customer Intelligence Platform (MySQL, database: customer_intelligence)
-- Notes: ratings are 1 to 5. 2023 is a partial year (data ends 2023-09-09).
-- Q1: Worst products by 1-star rate (minimum 100 reviews)
SELECT LEFT(p.product_title, 60) AS product,
       COUNT(*) AS reviews,
       ROUND(100 * AVG(f.rating = 1), 1) AS pct_1star,
       ROUND(AVG(f.rating), 2) AS avg_rating
FROM fact_reviews f
JOIN dim_product p ON p.product_key = f.product_key
GROUP BY p.product_key, p.product_title
HAVING COUNT(*) >= 100
ORDER BY pct_1star DESC
LIMIT 10;
-- Q2: Reviews, average rating and 1-star share per year
SELECT d.year,
       COUNT(*) AS reviews,
       ROUND(AVG(f.rating), 2) AS avg_rating,
       ROUND(100 * AVG(f.rating = 1), 1) AS pct_1star
FROM fact_reviews f
JOIN dim_date d ON d.date_key = f.date_key
GROUP BY d.year
ORDER BY d.year;
-- Q3: Verified vs unverified purchases
SELECT verified_purchase,
       COUNT(*) AS reviews,
       ROUND(AVG(rating), 2) AS avg_rating,
       ROUND(100 * AVG(rating = 1), 1) AS pct_1star
FROM fact_reviews
GROUP BY verified_purchase;
