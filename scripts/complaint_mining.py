import os
import pandas as pd
from dotenv import load_dotenv
import pymysql
from sklearn.feature_extraction.text import CountVectorizer
load_dotenv()
c = pymysql.connect(host=os.getenv("MYSQL_HOST"), port=int(os.getenv("MYSQL_PORT")),
    user=os.getenv("MYSQL_USER"), password=os.getenv("MYSQL_PASSWORD"),
    database=os.getenv("MYSQL_DATABASE"), charset="utf8mb4")
cur = c.cursor()
cur.execute("""
    SELECT d.year, CONCAT_WS(' ', t.review_title, t.review_body) AS txt
    FROM fact_reviews f
    JOIN dim_date d ON f.date_key = d.date_key
    JOIN review_text t ON f.review_id = t.review_id
    WHERE f.rating = 1 AND f.has_text = 1 AND d.year IN (2015, 2021)
""")
df = pd.DataFrame(cur.fetchall(), columns=["year", "txt"])
c.close()
df["txt"] = df["txt"].fillna("").str.lower()
a, b = df[df.year == 2015], df[df.year == 2021]
print("1-star reviews with text: 2015 =", len(a), "| 2021 =", len(b))
# 1) Phrases: share of reviews containing each word or phrase, per year
vec = CountVectorizer(ngram_range=(1, 2), stop_words="english", min_df=30, binary=True)
X = vec.fit_transform(df["txt"])
terms = vec.get_feature_names_out()
s15 = pd.Series(X[(df.year == 2015).values].mean(axis=0).A1, index=terms)
s21 = pd.Series(X[(df.year == 2021).values].mean(axis=0).A1, index=terms)
out = pd.DataFrame({"share_2015_%": s15 * 100, "share_2021_%": s21 * 100})
out["change_pts"] = out["share_2021_%"] - out["share_2015_%"]
out = out.round(2)
os.makedirs("reports", exist_ok=True)
out.sort_values("change_pts", ascending=False).to_csv("reports/complaint_phrases.csv")
print("\nPhrases most over-represented in 2021 complaints:")
print(out.sort_values("change_pts", ascending=False).head(25).to_string())
print("\nPhrases most over-represented in 2015 complaints:")
print(out.sort_values("change_pts").head(15).to_string())
# 2) Themes: % of 1-star reviews mentioning each theme (a review can hit several)
themes = {
    "shipping/delivery": r"ship|deliver|arrive|late|never came|didn.t come|package|packag",
    "quality/defect": r"broke|broken|cheap|stopped working|defect|poor quality|flimsy|damaged|leak",
    "fake/counterfeit": r"fake|counterfeit|knock.?off|not authentic|not genuine|imitation",
    "price/value": r"price|expensive|overpriced|waste of money|not worth|rip.?off",
    "skin reaction": r"rash|break.?out|irritat|burn|allerg|itch|acne",
    "scent/texture": r"smell|scent|odor|sticky|greasy|texture",
    "refund/service": r"refund|return|customer service|seller|replace|money back",
    "used/expired": r"expired|used|open(ed)?\b|tamper|dried out|old",
}
rows = []
for name, pat in themes.items():
    rows.append((name,
                 round(a.txt.str.contains(pat, regex=True).mean() * 100, 1),
                 round(b.txt.str.contains(pat, regex=True).mean() * 100, 1)))
tdf = pd.DataFrame(rows, columns=["theme", "2015_%", "2021_%"])
tdf["change_pts"] = (tdf["2021_%"] - tdf["2015_%"]).round(1)
tdf.to_csv("reports/complaint_themes.csv", index=False)
print("\nTheme share of 1-star reviews:")
print(tdf.sort_values("change_pts", ascending=False).to_string(index=False))
