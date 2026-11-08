import os
import pymysql
from dotenv import load_dotenv
load_dotenv()
connection = pymysql.connect(
    host=os.getenv("MYSQL_HOST"),
    port=int(os.getenv("MYSQL_PORT")),
    user=os.getenv("MYSQL_USER"),
    password=os.getenv("MYSQL_PASSWORD"),
    database=os.getenv("MYSQL_DATABASE"),
)
with connection.cursor() as cursor:
    cursor.execute("SELECT DATABASE(), VERSION()")
    print("Connected:", cursor.fetchone())
connection.close()
