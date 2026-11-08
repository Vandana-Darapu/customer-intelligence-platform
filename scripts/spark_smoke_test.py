import os
import sys
from pathlib import Path
from pyspark.sql import SparkSession
os.environ["PYSPARK_PYTHON"] = sys.executable
os.environ["PYSPARK_DRIVER_PYTHON"] = sys.executable
root = Path(__file__).resolve().parents[1]
tmp = root / "data" / "interim" / "spark_tmp"
tmp.mkdir(parents=True, exist_ok=True)
spark = (
    SparkSession.builder.master("local[4]")
    .appName("smoke_test")
    .config("spark.driver.memory", "4g")
    .config("spark.local.dir", str(tmp))
    .config("spark.sql.shuffle.partitions", "8")
    .getOrCreate()
)
print("Spark version:", spark.version)
df = spark.createDataFrame([(1, "a"), (2, "b"), (3, "c")], ["id", "letter"])
out = root / "data" / "interim" / "smoke_test.parquet"
df.write.mode("overwrite").parquet(str(out))
print("Rows read back:", spark.read.parquet(str(out)).count())
spark.stop()
