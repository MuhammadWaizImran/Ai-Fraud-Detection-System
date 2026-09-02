# Databricks Notebook: 03_gold_feature_engineering.py
# Reads from Silver clean_trades, computes all fraud-detection feature signals
# using Spark windowed aggregations, writes to Feature Store + gold.trade_features

# ─── Cell 1: Config ───────────────────────────────────────────────────────────
storage_account = dbutils.secrets.get(scope="fraud-kv-scope", key="storage-account-name")
storage_key     = dbutils.secrets.get(scope="fraud-kv-scope", key="storage-account-key")

spark.conf.set(
    f"fs.azure.account.key.{storage_account}.dfs.core.windows.net",
    storage_key
)

CATALOG     = "fraud_detection_catalog"
SILVER_TBL  = f"{CATALOG}.silver.clean_trades"
GOLD_TBL    = f"{CATALOG}.gold.trade_features"
FEATURE_TBL = f"{CATALOG}.features.trade_features"
CHECKPOINT  = f"abfss://checkpoints@{storage_account}.dfs.core.windows.net/gold_features"

print(f"Source      : {SILVER_TBL}")
print(f"Gold target : {GOLD_TBL}")
print(f"Feature tbl : {FEATURE_TBL}")

# ─── Cell 2: Import dependencies ─────────────────────────────────────────────
from pyspark.sql.functions import (
    col, count, sum as _sum, avg, stddev, max as _max, min as _min,
    when, lit, abs as _abs, window, current_timestamp,
    countDistinct, collect_list, size
)
from pyspark.sql.window import Window
import pyspark.sql.functions as F

# ─── Cell 3: Read Silver as streaming ─────────────────────────────────────────
silver_stream = (
    spark.readStream
    .format("delta")
    .table(SILVER_TBL)
)

# ─── Cell 4: Compute windowed fraud features ──────────────────────────────────
# Window: 10-minute tumbling window keyed on symbol + trader_id
windowed_features = (
    silver_stream
    .withWatermark("event_timestamp", "10 minutes")
    .groupBy(
        window(col("event_timestamp"), "10 minutes"),
        col("symbol"),
        col("trader_id"),
    )
    .agg(
        # Basic counts
        count("*").alias("order_count_10m"),
        _sum("volume").alias("total_volume_10m"),
        avg("volume").alias("avg_volume_10m"),
        _max("volume").alias("max_volume_10m"),

        # Price stats for price manipulation detection
        avg("price").alias("avg_price_10m"),
        stddev("price").alias("stddev_price_10m"),
        _max("price").alias("max_price_10m"),
        _min("price").alias("min_price_10m"),

        # Order type counts for wash trading detection
        _sum(when(col("order_type") == "buy",  lit(1)).otherwise(lit(0))).alias("buy_count_10m"),
        _sum(when(col("order_type") == "sell", lit(1)).otherwise(lit(0))).alias("sell_count_10m"),

        # Cancel count for spoofing/layering detection
        _sum(when(col("order_status") == "cancelled", lit(1)).otherwise(lit(0))).alias("cancel_count_10m"),
        _sum(when(col("order_status") == "executed",  lit(1)).otherwise(lit(0))).alias("executed_count_10m"),

        # Market cap reference
        avg("market_cap").alias("avg_market_cap"),
        avg("price_change_24h_pct").alias("avg_price_change_24h_pct"),

        # Processing metadata
        current_timestamp().alias("feature_computed_at"),
    )
    .select(
        col("window.start").alias("window_start"),
        col("window.end").alias("window_end"),
        col("symbol"),
        col("trader_id"),
        col("order_count_10m"),
        col("total_volume_10m"),
        col("avg_volume_10m"),
        col("max_volume_10m"),
        col("avg_price_10m"),
        col("stddev_price_10m"),
        col("max_price_10m"),
        col("min_price_10m"),
        col("buy_count_10m"),
        col("sell_count_10m"),
        col("cancel_count_10m"),
        col("executed_count_10m"),
        col("avg_market_cap"),
        col("avg_price_change_24h_pct"),

        # ── Derived fraud-signal features ──────────────────────────────────────

        # 1. Volume ratio: how many times above average volume
        (col("max_volume_10m") / (col("avg_volume_10m") + lit(1e-9))).alias("volume_spike_ratio"),

        # 2. Price range percent: (max-min)/avg - high = price manipulation signal
        ((_abs(col("max_price_10m") - col("min_price_10m"))) / (col("avg_price_10m") + lit(1e-9)) * 100)
            .alias("price_range_pct"),

        # 3. Cancel-to-total ratio: high = spoofing/layering signal
        (col("cancel_count_10m") / (col("order_count_10m") + lit(1e-9))).alias("cancel_to_trade_ratio"),

        # 4. Wash trading indicator: same trader with both buy & sell in window
        when(
            (col("buy_count_10m") > 0) & (col("sell_count_10m") > 0),
            lit(1)
        ).otherwise(lit(0)).alias("wash_trade_flag"),

        # 5. Layering indicator: many orders in short window by same trader
        when(col("order_count_10m") >= 5, lit(1)).otherwise(lit(0)).alias("layering_flag"),

        # 6. Trade velocity: orders per minute in the window
        (col("order_count_10m") / lit(10.0)).alias("orders_per_minute"),

        # 7. Buy-sell imbalance ratio
        (_abs(col("buy_count_10m") - col("sell_count_10m")) / (col("order_count_10m") + lit(1e-9)))
            .alias("buy_sell_imbalance"),

        col("feature_computed_at"),
    )
)

# ─── Cell 5: Write to Gold Delta table (features) ────────────────────────────
(
    windowed_features.writeStream
    .format("delta")
    .outputMode("append")
    .option("checkpointLocation", CHECKPOINT + "_gold")
    .trigger(availableNow=True)
    .toTable(GOLD_TBL)
)

print(f"Gold feature table written -> {GOLD_TBL}")

# ─── Cell 6: Write same features to Feature Store table ──────────────────────
# (Feature Store table = same schema, used for offline training lookup & online serving)
(
    windowed_features.writeStream
    .format("delta")
    .outputMode("append")
    .option("checkpointLocation", CHECKPOINT + "_features")
    .trigger(availableNow=True)
    .toTable(FEATURE_TBL)
)

print(f"Feature Store table written -> {FEATURE_TBL}")

# ─── Cell 7: Validate ─────────────────────────────────────────────────────────
spark.sql(f"SELECT COUNT(*) AS rows FROM {GOLD_TBL}").show()
spark.sql(f"""
    SELECT symbol, COUNT(*) AS windows,
           AVG(volume_spike_ratio) AS avg_vol_spike,
           AVG(cancel_to_trade_ratio) AS avg_cancel_ratio,
           SUM(wash_trade_flag) AS wash_trades,
           SUM(layering_flag) AS layering_events
    FROM {GOLD_TBL}
    GROUP BY symbol
    ORDER BY avg_vol_spike DESC
    LIMIT 15
""").show()
