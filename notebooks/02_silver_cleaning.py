# Databricks Notebook: 02_silver_cleaning.py
# Reads from Bronze raw_trades, parses JSON, deduplicates, validates schema,
# handles nulls, standardizes types, writes to Silver clean_trades Delta table.

# ─── Cell 1: Config ───────────────────────────────────────────────────────────
storage_account = dbutils.secrets.get(scope="fraud-kv-scope", key="storage-account-name")
storage_key     = dbutils.secrets.get(scope="fraud-kv-scope", key="storage-account-key")

spark.conf.set(
    f"fs.azure.account.key.{storage_account}.dfs.core.windows.net",
    storage_key
)

CATALOG     = "fraud_detection_catalog"
BRONZE_TBL  = f"{CATALOG}.bronze.raw_trades"
SILVER_TBL  = f"{CATALOG}.silver.clean_trades"
CHECKPOINT  = f"abfss://checkpoints@{storage_account}.dfs.core.windows.net/silver_clean_trades"

print(f"Source : {BRONZE_TBL}")
print(f"Target : {SILVER_TBL}")

# ─── Cell 2: Define target schema ─────────────────────────────────────────────
from pyspark.sql.types import (
    StructType, StructField, StringType, DoubleType, BooleanType, TimestampType, LongType
)

ORDER_SCHEMA = StructType([
    StructField("order_id",             StringType(),    True),
    StructField("trader_id",            StringType(),    True),
    StructField("symbol",               StringType(),    True),
    StructField("coin_name",            StringType(),    True),
    StructField("order_type",           StringType(),    True),
    StructField("order_status",         StringType(),    True),
    StructField("price",                DoubleType(),    True),
    StructField("volume",               DoubleType(),    True),
    StructField("market_cap",           DoubleType(),    True),
    StructField("price_change_24h_pct", DoubleType(),    True),
    StructField("timestamp",            StringType(),    True),
])

# ─── Cell 3: Read from Bronze, parse JSON ─────────────────────────────────────
from pyspark.sql.functions import (
    col, from_json, to_timestamp, current_timestamp, lower, trim,
    when, isnan, isnull, regexp_replace, lit
)

bronze_stream = (
    spark.readStream
    .format("delta")
    .table(BRONZE_TBL)
)

parsed = (
    bronze_stream
    .withColumn("parsed", from_json(col("json_str"), ORDER_SCHEMA))
    .select(
        col("parsed.order_id").alias("order_id"),
        col("parsed.trader_id").alias("trader_id"),
        trim(col("parsed.symbol")).alias("symbol"),
        trim(col("parsed.coin_name")).alias("coin_name"),
        lower(trim(col("parsed.order_type"))).alias("order_type"),
        lower(trim(col("parsed.order_status"))).alias("order_status"),
        col("parsed.price").alias("price"),
        col("parsed.volume").alias("volume"),
        col("parsed.market_cap").alias("market_cap"),
        col("parsed.price_change_24h_pct").alias("price_change_24h_pct"),
        to_timestamp(col("parsed.timestamp")).alias("event_timestamp"),
        col("kafka_enqueued_time").alias("enqueued_at"),
        current_timestamp().alias("silver_processed_at"),
    )
)

# ─── Cell 4: Data Quality — filter bad rows ───────────────────────────────────
VALID_ORDER_TYPES   = ["buy", "sell"]
VALID_ORDER_STATUSES = ["executed", "cancelled", "placed"]

clean = (
    parsed
    # Drop rows with null primary keys
    .filter(col("order_id").isNotNull())
    .filter(col("trader_id").isNotNull())
    .filter(col("symbol").isNotNull())
    # Validate enum columns
    .filter(col("order_type").isin(VALID_ORDER_TYPES))
    .filter(col("order_status").isin(VALID_ORDER_STATUSES))
    # Price and volume must be positive
    .filter(col("price") > 0)
    .filter(col("volume") > 0)
    # Drop nulls in critical numeric fields
    .filter(col("price").isNotNull())
    .filter(col("volume").isNotNull())
    # Add data quality pass flag
    .withColumn("dq_passed", lit(True))
)

# ─── Cell 5: Write deduplicated stream to Silver ──────────────────────────────
# Note: True streaming dedup uses watermark + dropDuplicatesWithinWatermark
# to handle late arrivals without unbounded state.
clean_deduped = (
    clean
    .withWatermark("event_timestamp", "10 minutes")
    .dropDuplicatesWithinWatermark(["order_id"])
)

(
    clean_deduped.writeStream
    .format("delta")
    .outputMode("append")
    .option("checkpointLocation", CHECKPOINT)
    .trigger(availableNow=True)
    .toTable(SILVER_TBL)
)

print(f"Silver cleaning complete -> {SILVER_TBL}")
spark.sql(f"SELECT COUNT(*) AS row_count FROM {SILVER_TBL}").show()
spark.sql(f"""
    SELECT order_type, order_status, COUNT(*) AS cnt
    FROM {SILVER_TBL}
    GROUP BY order_type, order_status
    ORDER BY cnt DESC
""").show()
