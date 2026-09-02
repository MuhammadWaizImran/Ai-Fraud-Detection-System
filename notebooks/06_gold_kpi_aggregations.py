# Databricks Notebook: 06_gold_kpi_aggregations.py
# Reads from gold.fraud_alerts → computes 6 Gold tables optimised for
# Power BI DirectQuery / Import mode via Databricks SQL Warehouse.

# ─── Cell 1: Config ───────────────────────────────────────────────────────────
from pyspark.sql.functions import (
    col, count, avg, sum as _sum, max as _max, min as _min,
    round as _round, lit, date_trunc, current_timestamp,
    countDistinct, when, window, to_timestamp, date_format,
    hour as _hour, dayofweek
)
from pyspark.sql import Row
from datetime import datetime

storage_account = dbutils.secrets.get(scope="fraud-kv-scope", key="storage-account-name")
storage_key     = dbutils.secrets.get(scope="fraud-kv-scope", key="storage-account-key")

spark.conf.set(
    f"fs.azure.account.key.{storage_account}.dfs.core.windows.net",
    storage_key
)

CATALOG     = "fraud_detection_catalog"
GOLD        = f"{CATALOG}.gold"
ALERTS_TBL  = f"{GOLD}.fraud_alerts"

# Power BI target tables (Gold layer)
PBI_SUMMARY     = f"{GOLD}.pbi_summary_kpis"
PBI_TIMESERIES  = f"{GOLD}.pbi_fraud_timeseries"
PBI_BY_SYMBOL   = f"{GOLD}.pbi_fraud_by_symbol"
PBI_BY_PATTERN  = f"{GOLD}.pbi_fraud_by_pattern"
PBI_TRADERS     = f"{GOLD}.pbi_trader_risk_profiles"
PBI_HOURLY      = f"{GOLD}.pbi_hourly_trends"

print("=" * 60)
print(" Gold KPI Aggregations → Power BI Tables")
print("=" * 60)
print(f"Source  : {ALERTS_TBL}")
print(f"Targets : {GOLD}.pbi_*")

alerts_df = spark.table(ALERTS_TBL).cache()
total_rows = alerts_df.count()
print(f"\nTotal alerts loaded: {total_rows:,}")

# ─── Cell 2: Summary KPIs (single-row card metrics for Power BI) ──────────────
total          = total_rows
fraud_count    = alerts_df.filter(col("decision") == "FRAUD").count()
suspicious     = alerts_df.filter(col("decision") == "SUSPICIOUS").count()
safe_count     = alerts_df.filter(col("decision") == "SAFE").count()
avg_risk       = alerts_df.agg(avg("risk_score")).collect()[0][0] or 0.0
max_risk       = alerts_df.agg(_max("risk_score")).collect()[0][0] or 0.0
fraud_rate_pct = round((fraud_count / max(total, 1)) * 100, 2)

# Last 1-hour window stats
from pyspark.sql.functions import expr
recent_df = alerts_df.filter(
    col("window_start") >= expr("current_timestamp() - INTERVAL 1 HOUR")
)
recent_fraud = recent_df.filter(col("decision") == "FRAUD").count()

summary_df = spark.createDataFrame([Row(
    computed_at          = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
    total_predictions    = int(total),
    fraud_count          = int(fraud_count),
    suspicious_count     = int(suspicious),
    safe_count           = int(safe_count),
    fraud_rate_pct       = float(fraud_rate_pct),
    avg_risk_score       = round(float(avg_risk), 4),
    max_risk_score       = round(float(max_risk), 4),
    fraud_last_1h        = int(recent_fraud),
)])

(summary_df.write.format("delta").mode("overwrite")
    .option("overwriteSchema", "true")
    .saveAsTable(PBI_SUMMARY))
print(f"\n✅ {PBI_SUMMARY}")
summary_df.show(truncate=False)

# ─── Cell 3: Fraud Time-Series (minute granularity for line charts) ───────────
timeseries_df = (
    alerts_df
    .withColumn("minute_bucket", date_trunc("minute", col("window_start")))
    .groupBy("minute_bucket")
    .agg(
        count("*").alias("total_events"),
        _sum(when(col("decision") == "FRAUD",      lit(1)).otherwise(lit(0))).alias("fraud_count"),
        _sum(when(col("decision") == "SUSPICIOUS", lit(1)).otherwise(lit(0))).alias("suspicious_count"),
        _sum(when(col("decision") == "SAFE",       lit(1)).otherwise(lit(0))).alias("safe_count"),
        _round(avg("risk_score"),          4).alias("avg_risk_score"),
        _round(_max("risk_score"),         4).alias("max_risk_score"),
        _round(avg("volume_spike_ratio"),  2).alias("avg_volume_spike"),
        _round(_sum("total_volume_10m"),   2).alias("total_volume"),
    )
    .withColumn("fraud_rate_pct", _round(col("fraud_count") / col("total_events") * 100, 2))
    .withColumn("hour_of_day", _hour(col("minute_bucket")))
    .withColumn("day_of_week", dayofweek(col("minute_bucket")))
    .orderBy("minute_bucket")
)

(timeseries_df.write.format("delta").mode("overwrite")
    .option("overwriteSchema", "true")
    .saveAsTable(PBI_TIMESERIES))
print(f"✅ {PBI_TIMESERIES}  ({timeseries_df.count()} rows)")

# ─── Cell 4: Fraud by Symbol (bar chart + map) ────────────────────────────────
by_symbol_df = (
    alerts_df
    .groupBy("symbol")
    .agg(
        count("*").alias("total_events"),
        _sum(when(col("decision") == "FRAUD",      lit(1)).otherwise(lit(0))).alias("fraud_count"),
        _sum(when(col("decision") == "SUSPICIOUS", lit(1)).otherwise(lit(0))).alias("suspicious_count"),
        _round(avg("risk_score"),      4).alias("avg_risk_score"),
        _round(_max("risk_score"),     4).alias("max_risk_score"),
        _round(_sum("total_volume_10m"), 2).alias("total_volume"),
        _round(avg("volume_spike_ratio"), 2).alias("avg_volume_spike"),
    )
    .withColumn("fraud_rate_pct", _round(col("fraud_count") / col("total_events") * 100, 2))
    .withColumn(
        "risk_tier",
        when(col("avg_risk_score") >= 0.85, lit("HIGH"))
        .when(col("avg_risk_score") >= 0.60, lit("MEDIUM"))
        .otherwise(lit("LOW"))
    )
    .orderBy(col("fraud_count").desc())
)

(by_symbol_df.write.format("delta").mode("overwrite")
    .option("overwriteSchema", "true")
    .saveAsTable(PBI_BY_SYMBOL))
print(f"✅ {PBI_BY_SYMBOL}  ({by_symbol_df.count()} rows)")

# ─── Cell 5: Fraud by Pattern Type (donut / treemap) ─────────────────────────
by_pattern_df = (
    alerts_df
    .filter(col("decision").isin(["FRAUD", "SUSPICIOUS"]))
    .groupBy("fraud_type_predicted")
    .agg(
        count("*").alias("event_count"),
        _sum(when(col("decision") == "FRAUD",      lit(1)).otherwise(lit(0))).alias("fraud_count"),
        _sum(when(col("decision") == "SUSPICIOUS", lit(1)).otherwise(lit(0))).alias("suspicious_count"),
        _round(avg("risk_score"),      4).alias("avg_risk_score"),
        _round(_max("risk_score"),     4).alias("max_risk_score"),
        countDistinct("trader_id").alias("distinct_traders_affected"),
        countDistinct("symbol").alias("distinct_symbols_affected"),
    )
    .withColumn("pct_of_total",
        _round(col("event_count") / lit(max(fraud_count + suspicious, 1)) * 100, 2))
    .orderBy(col("event_count").desc())
)

(by_pattern_df.write.format("delta").mode("overwrite")
    .option("overwriteSchema", "true")
    .saveAsTable(PBI_BY_PATTERN))
print(f"✅ {PBI_BY_PATTERN}  ({by_pattern_df.count()} rows)")

# ─── Cell 6: Trader Risk Profiles (table + scatter) ──────────────────────────
trader_df = (
    alerts_df
    .groupBy("trader_id")
    .agg(
        count("*").alias("total_windows"),
        _sum(when(col("decision") == "FRAUD",      lit(1)).otherwise(lit(0))).alias("fraud_windows"),
        _sum(when(col("decision") == "SUSPICIOUS", lit(1)).otherwise(lit(0))).alias("suspicious_windows"),
        _sum(when(col("decision") == "SAFE",       lit(1)).otherwise(lit(0))).alias("safe_windows"),
        _round(avg("risk_score"),            4).alias("avg_risk_score"),
        _round(_max("risk_score"),           4).alias("max_risk_score"),
        _round(avg("volume_spike_ratio"),    2).alias("avg_volume_spike"),
        _round(avg("cancel_to_trade_ratio"), 4).alias("avg_cancel_ratio"),
        _round(avg("wash_trade_flag"),       4).alias("wash_trade_rate"),
        _round(avg("layering_flag"),         4).alias("layering_rate"),
        _round(_sum("total_volume_10m"),     2).alias("total_volume_traded"),
    )
    .withColumn("fraud_rate_pct", _round(col("fraud_windows") / col("total_windows") * 100, 2))
    .withColumn(
        "risk_tier",
        when(col("max_risk_score") >= 0.85, lit("HIGH"))
        .when(col("max_risk_score") >= 0.60, lit("MEDIUM"))
        .otherwise(lit("LOW"))
    )
    .withColumn(
        "trader_status",
        when(col("fraud_rate_pct") >= 30, lit("FLAGGED"))
        .when(col("fraud_rate_pct") >= 10, lit("WATCH"))
        .otherwise(lit("NORMAL"))
    )
    .orderBy(col("max_risk_score").desc())
)

(trader_df.write.format("delta").mode("overwrite")
    .option("overwriteSchema", "true")
    .saveAsTable(PBI_TRADERS))
print(f"✅ {PBI_TRADERS}  ({trader_df.count()} rows)")

# ─── Cell 7: Hourly Trends (time intelligence in Power BI) ────────────────────
hourly_df = (
    alerts_df
    .withColumn("hour_bucket", date_trunc("hour", col("window_start")))
    .groupBy("hour_bucket")
    .agg(
        count("*").alias("total_events"),
        _sum(when(col("decision") == "FRAUD",      lit(1)).otherwise(lit(0))).alias("fraud_count"),
        _sum(when(col("decision") == "SUSPICIOUS", lit(1)).otherwise(lit(0))).alias("suspicious_count"),
        _round(avg("risk_score"),          4).alias("avg_risk_score"),
        _round(_max("risk_score"),         4).alias("max_risk_score"),
        _round(avg("volume_spike_ratio"),  2).alias("avg_volume_spike"),
        _round(_sum("total_volume_10m"),   2).alias("total_volume"),
        countDistinct("trader_id").alias("active_traders"),
        countDistinct("symbol").alias("active_symbols"),
    )
    .withColumn("fraud_rate_pct", _round(col("fraud_count") / col("total_events") * 100, 2))
    .withColumn("hour_of_day",  _hour(col("hour_bucket")))
    .withColumn("day_of_week",  dayofweek(col("hour_bucket")))
    .withColumn("hour_label",   date_format(col("hour_bucket"), "yyyy-MM-dd HH:mm"))
    .orderBy("hour_bucket")
)

(hourly_df.write.format("delta").mode("overwrite")
    .option("overwriteSchema", "true")
    .saveAsTable(PBI_HOURLY))
print(f"✅ {PBI_HOURLY}  ({hourly_df.count()} rows)")

# ─── Cell 8: Print Power BI connection info ────────────────────────────────────
jdbc_host = spark.conf.get("spark.databricks.workspaceUrl", "your-workspace.azuredatabricks.net")

print("\n" + "=" * 60)
print(" POWER BI CONNECTION DETAILS")
print("=" * 60)
print(f"\n Server  : {jdbc_host}")
print(f" HTTP Path: /sql/1.0/warehouses/<sql-warehouse-id>")
print(f"\n Tables ready for Power BI DirectQuery:")
print(f"   • {PBI_SUMMARY}      ← Card KPIs")
print(f"   • {PBI_TIMESERIES}   ← Line charts (time series)")
print(f"   • {PBI_BY_SYMBOL}    ← Bar chart by crypto symbol")
print(f"   • {PBI_BY_PATTERN}   ← Donut by fraud pattern")
print(f"   • {PBI_TRADERS}      ← Trader risk table")
print(f"   • {PBI_HOURLY}       ← Hourly trend analysis")
print("\n✅ All Power BI Gold tables refreshed successfully.")
