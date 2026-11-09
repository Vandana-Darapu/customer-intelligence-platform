import os
from dotenv import load_dotenv
import pymysql
load_dotenv()
c = pymysql.connect(host=os.getenv("MYSQL_HOST"), port=int(os.getenv("MYSQL_PORT")),
    user=os.getenv("MYSQL_USER"), password=os.getenv("MYSQL_PASSWORD"),
    database=os.getenv("MYSQL_DATABASE"))
cur = c.cursor()
cur.execute("""
    SELECT table_name, GROUP_CONCAT(column_name ORDER BY ordinal_position SEPARATOR ', ')
    FROM information_schema.columns
    WHERE table_schema = DATABASE()
    GROUP BY table_name
""")
for name, cols in cur.fetchall():
    print(name, "->", cols)
c.close()
