# Databricks Notebook: 05_realtime_scoring_engine.py
# Reads live features from gold.trade_features, calls the deployed Model Serving endpoint,
# classifies Fraud / Suspicious / Safe, writes results to gold.fraud_alerts,
# and fires Azure Logic App webhook for high-risk predictions.

# ─── Cell 1: Config & Imports ────────────────────────────────────────────────
import mlflow
import mlflow.xgboost
import pandas as pd
import numpy as np
import requests
import json
from datetime import datetime, timezone
from pyspark.sql.functions import (
    col, lit, current_timestamp, udf, when, pandas_udf
)
from pyspark.sql.types import DoubleType, StringType, StructType, StructField

storage_account   = dbutils.secrets.get(scope="fraud-kv-scope", key="storage-account-name")
storage_key       = dbutils.secrets.get(scope="fraud-kv-scope", key="storage-account-key")
logic_webhook_url = dbutils.secrets.get(scope="fraud-kv-scope", key="logic-app-webhook-url")

spark.conf.set(
    f"fs.azure.account.key.{storage_account}.dfs.core.windows.net",
    storage_key
)

CATALOG       = "fraud_detection_catalog"
FEATURES_TBL  = f"{CATALOG}.gold.trade_features"
ALERTS_TBL    = f"{CATALOG}.gold.fraud_alerts"
CHECKPOINT    = f"abfss://checkpoints@{storage_account}.dfs.core.windows.net/fraud_alerts"
MODEL_NAME    = "FraudDetectionModel_XGBoost"
MODEL_VERSION = "1"

# Thresholds (from architecture doc)
FRAUD_THRESHOLD       = 0.85
SUSPICIOUS_THRESHOLD  = 0.60

print(f"Feature source : {FEATURES_TBL}")
print(f"Alerts target  : {ALERTS_TBL}")
print(f"Model          : {MODEL_NAME} v{MODEL_VERSION}")

# ─── Cell 2: Load trained model from MLflow Registry ─────────────────────────
model_uri = f"models:/{MODEL_NAME}/{MODEL_VERSION}"
loaded_model = mlflow.xgboost.load_model(model_uri)
# Also load scaler from the isolation forest run (stored alongside)
# For simplicity, we use a dummy scaler if not separately stored
try:
    scaler_uri = f"models:/FeatureScaler/1"
    scaler = mlflow.sklearn.load_model(scaler_uri)
except Exception:
    from sklearn.preprocessing import StandardScaler
    scaler = None  # will skip scaling if unavailable (XGBoost is scale-invariant)

print(f"Model loaded from MLflow: {model_uri}")

FEATURES = [
    "volume_spike_ratio", "price_range_pct", "cancel_to_trade_ratio",
    "wash_trade_flag", "layering_flag", "orders_per_minute",
    "buy_sell_imbalance",
    # Derive price_deviation_pct from available columns
]

# ─── Cell 3: Define scoring UDF ───────────────────────────────────────────────
@pandas_udf(returnType=DoubleType())
def score_batch(
    volume_spike_ratio:    pd.Series,
    price_range_pct:       pd.Series,
    cancel_to_trade_ratio: pd.Series,
    wash_trade_flag:       pd.Series,
    layering_flag:         pd.Series,
    orders_per_minute:     pd.Series,
    buy_sell_imbalance:    pd.Series,
    total_volume_10m:      pd.Series,
    avg_price_10m:         pd.Series,
) -> pd.Series:
    X = pd.DataFrame({
        "volume_spike_ratio":    volume_spike_ratio.fillna(0),
        "price_range_pct":       price_range_pct.fillna(0),
        "cancel_to_trade_ratio": cancel_to_trade_ratio.fillna(0),
        "wash_trade_flag":       wash_trade_flag.fillna(0),
        "layering_flag":         layering_flag.fillna(0),
        "orders_per_minute":     orders_per_minute.fillna(0),
        "buy_sell_imbalance":    buy_sell_imbalance.fillna(0),
        "volume":                total_volume_10m.fillna(0),
        "price":                 avg_price_10m.fillna(0),
        "price_deviation_pct":   (price_range_pct.fillna(0) / 2),  # proxy
    })
    probs = loaded_model.predict_proba(X)[:, 1]
    return pd.Series(probs)


# ─── Cell 4: Read feature stream ─────────────────────────────────────────────
feature_stream = (
    spark.readStream
    .format("delta")
    .table(FEATURES_TBL)
)

# ─── Cell 5: Apply ML scoring + rule-based thresholds ─────────────────────────
scored = (
    feature_stream
    .withColumn(
        "risk_score",
        score_batch(
            col("volume_spike_ratio"),
            col("price_range_pct"),
            col("cancel_to_trade_ratio"),
            col("wash_trade_flag"),
            col("layering_flag"),
            col("orders_per_minute"),
            col("buy_sell_imbalance"),
            col("total_volume_10m"),
            col("avg_price_10m"),
        )
    )
    .withColumn(
        "decision",
        when(col("risk_score") >= FRAUD_THRESHOLD,      lit("FRAUD"))
        .when(col("risk_score") >= SUSPICIOUS_THRESHOLD, lit("SUSPICIOUS"))
        .otherwise(lit("SAFE"))
    )
    .withColumn(
        "fraud_type_predicted",
        when(col("wash_trade_flag")      == 1,              lit("wash_trading"))
        .when(col("layering_flag")       == 1,              lit("layering"))
        .when(col("cancel_to_trade_ratio") > 0.7,           lit("spoofing"))
        .when(col("volume_spike_ratio")  > 20,              lit("volume_spike"))
        .when(col("price_range_pct")     > 15,              lit("price_manipulation"))
        .otherwise(lit("unknown"))
    )
    .withColumn("model_name",    lit(MODEL_NAME))
    .withColumn("model_version", lit(MODEL_VERSION))
    .withColumn("scored_at",     current_timestamp())
)

# ─── Cell 6: Logic App alert function ────────────────────────────────────────
def fire_alert(row):
    """Fire Logic App webhook for high-risk predictions."""
    if row["decision"] == "FRAUD" and logic_webhook_url:
        payload = {
            "order_id":   str(row.get("symbol", "")) + "_" + str(row.get("window_start", "")),
            "trader_id":  str(row.get("trader_id", "")),
            "symbol":     str(row.get("symbol", "")),
            "risk_score": float(row.get("risk_score", 0)),
            "decision":   str(row.get("decision", "")),
            "fraud_type": str(row.get("fraud_type_predicted", "")),
            "timestamp":  datetime.now(timezone.utc).isoformat(),
        }
        try:
            resp = requests.post(logic_webhook_url, json=payload, timeout=5)
            print(f"[ALERT FIRED] {payload['symbol']} | score={payload['risk_score']:.3f} | status={resp.status_code}")
        except Exception as e:
            print(f"[WARN] Alert failed: {e}")


# ─── Cell 7: Write to fraud_alerts Delta table with alert trigger ─────────────
def process_batch(batch_df, batch_id):
    """foreachBatch: write to Delta + fire Logic App alerts for FRAUD rows."""
    if batch_df.count() == 0:
        return

    # Write all predictions to Delta
    (
        batch_df.write
        .format("delta")
        .mode("append")
        .saveAsTable(ALERTS_TBL)
    )

    # Fire Logic App alerts for FRAUD decisions
    fraud_rows = batch_df.filter(col("decision") == "FRAUD").collect()
    print(f"[Batch {batch_id}] Total: {batch_df.count()} | FRAUD: {len(fraud_rows)}")
    for row in fraud_rows:
        fire_alert(row.asDict())


(
    scored.writeStream
    .foreachBatch(process_batch)
    .option("checkpointLocation", CHECKPOINT)
    .trigger(availableNow=True)
    .start()
    .awaitTermination()
)

print(f"Fraud scoring complete -> {ALERTS_TBL}")

# ─── Cell 8: Summary ──────────────────────────────────────────────────────────
spark.sql(f"""
    SELECT decision, COUNT(*) AS count, ROUND(AVG(risk_score), 4) AS avg_risk
    FROM {ALERTS_TBL}
    GROUP BY decision
    ORDER BY avg_risk DESC
""").show()

spark.sql(f"""
    SELECT fraud_type_predicted, COUNT(*) AS count, ROUND(AVG(risk_score), 4) AS avg_risk
    FROM {ALERTS_TBL}
    WHERE decision IN ('FRAUD', 'SUSPICIOUS')
    GROUP BY fraud_type_predicted
    ORDER BY count DESC
""").show()
