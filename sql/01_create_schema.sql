-- Star schema for the Customer Intelligence Platform
-- Safe to re-run: uses IF NOT EXISTS and never drops tables.
CREATE TABLE IF NOT EXISTS dim_product (
    product_key          INT AUTO_INCREMENT PRIMARY KEY,
    parent_asin          VARCHAR(20)   NOT NULL,
    source_category      VARCHAR(50)   NOT NULL,
    main_category        VARCHAR(100)  NULL,
    product_title        VARCHAR(1000) NULL,
    store                VARCHAR(255)  NULL,
    price                DECIMAL(10,2) NULL,
    has_price            BOOLEAN       NOT NULL,
    price_outlier        BOOLEAN       NOT NULL,
    listing_avg_rating   DECIMAL(3,2)  NULL,
    listing_rating_count INT           NULL,
    UNIQUE KEY uq_product_asin (parent_asin)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
CREATE TABLE IF NOT EXISTS dim_date (
    date_key   INT          PRIMARY KEY,  -- format YYYYMMDD
    full_date  DATE         NOT NULL,
    year       SMALLINT     NOT NULL,
    quarter    TINYINT      NOT NULL,
    month      TINYINT      NOT NULL,
    month_name VARCHAR(10)  NOT NULL,
    UNIQUE KEY uq_date_full (full_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
CREATE TABLE IF NOT EXISTS fact_reviews (
    review_id         BIGINT      PRIMARY KEY,  -- assigned by the loader
    product_key       INT         NOT NULL,
    date_key          INT         NOT NULL,
    user_id           VARCHAR(64) NOT NULL,
    rating            TINYINT     NOT NULL,
    sentiment_label   VARCHAR(8)  NOT NULL,
    verified_purchase BOOLEAN     NULL,
    helpful_vote      INT         NULL,
    has_text          BOOLEAN     NOT NULL,
    text_length       INT         NULL,
    review_ts         DATETIME    NOT NULL,
    KEY idx_fact_product (product_key),
    KEY idx_fact_date (date_key),
    KEY idx_fact_sentiment (sentiment_label),
    CONSTRAINT fk_fact_product FOREIGN KEY (product_key) REFERENCES dim_product (product_key),
    CONSTRAINT fk_fact_date FOREIGN KEY (date_key) REFERENCES dim_date (date_key)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
CREATE TABLE IF NOT EXISTS review_text (
    review_id    BIGINT        PRIMARY KEY,
    review_title VARCHAR(1000) NULL,
    review_body  MEDIUMTEXT    NULL,
    CONSTRAINT fk_text_review FOREIGN KEY (review_id) REFERENCES fact_reviews (review_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
