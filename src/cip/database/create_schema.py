"""Create the star-schema tables in MySQL from sql/01_create_schema.sql."""
import logging
import os
import sys
from pathlib import Path
import pymysql
from dotenv import load_dotenv
PROJECT_ROOT = Path(__file__).resolve().parents[3]
SCHEMA_FILE = PROJECT_ROOT / "sql" / "01_create_schema.sql"
log = logging.getLogger("create_schema")
def split_statements(sql_text):
    """Split a SQL file into statements, dropping -- comments."""
    lines = [ln.split("--")[0] for ln in sql_text.splitlines()]
    return [s.strip() for s in "\n".join(lines).split(";") if s.strip()]
def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    load_dotenv(PROJECT_ROOT / ".env")
    if not SCHEMA_FILE.exists():
        log.error("Missing schema file: %s", SCHEMA_FILE)
        sys.exit(1)
    statements = split_statements(SCHEMA_FILE.read_text(encoding="utf-8"))
    conn = pymysql.connect(
        host=os.getenv("MYSQL_HOST", "localhost"),
        port=int(os.getenv("MYSQL_PORT", "3306")),
        user=os.getenv("MYSQL_USER"),
        password=os.getenv("MYSQL_PASSWORD"),
        database=os.getenv("MYSQL_DATABASE"),
        charset="utf8mb4",
    )
    try:
        with conn.cursor() as cur:
            for stmt in statements:
                cur.execute(stmt)
            cur.execute("SHOW TABLES")
            tables = [row[0] for row in cur.fetchall()]
        conn.commit()
    finally:
        conn.close()
    log.info("Ran %d statements. Tables now in database: %s", len(statements), ", ".join(tables))
if __name__ == "__main__":
    main()
