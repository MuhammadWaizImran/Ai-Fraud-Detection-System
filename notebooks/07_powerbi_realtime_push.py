# Databricks Notebook: 07_powerbi_realtime_push.py
# Pushes live fraud alerts to Power BI Streaming Dataset API.
# This notebook runs continuously alongside 05_realtime_scoring_engine.
# It enables REAL-TIME tiles in Power BI (no import/refresh needed).

# ─── Cell 1: Config ───────────────────────────────────────────────────────────
import time
import json
import urllib.request
import urllib.error
from pyspark.sql.functions import col, desc
from datetime import datetime, timezone

storage_account = dbutils.secrets.get(scope="fraud-kv-scope", key="storage-account-name")
storage_key     = dbutils.secrets.get(scope="fraud-kv-scope", key="storage-account-key")

spark.conf.set(
    f"fs.azure.account.key.{storage_account}.dfs.core.windows.net",
    storage_key
)

# Power BI Streaming Dataset Push URL
# Get this from: Power BI Service → Dataset → ... → Streaming API
# Format: https://api.powerbi.com/beta/<tenant>/datasets/<id>/rows?...
POWERBI_PUSH_URL = dbutils.secrets.get(
    scope="fraud-kv-scope", key="powerbi-push-url"  # Set this after creating streaming dataset
)

CATALOG  = "fraud_detection_catalog"
GOLD     = f"{CATALOG}.gold"

print("Power BI Real-Time Push Notebook")
print(f"Storage: {storage_account}")
print(f"Catalog : {CATALOG}")

# ─── Cell 2: Push function ────────────────────────────────────────────────────
def push_to_powerbi(rows_json: list, push_url: str) -> bool:
    """Push rows to Power BI streaming dataset."""
    if not push_url or push_url == "":
        print("[SKIP] No Power BI push URL configured.")
        return False

    payload = json.dumps(rows_json).encode("utf-8")
    req = urllib.request.Request(
        push_url,
        data=payload,
        method="POST",
        headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status == 200
    except urllib.error.HTTPError as e:
        print(f"[WARN] Power BI push error: HTTP {e.code}: {e.read().decode()[:200]}")
        return False
    except Exception as e:
        print(f"[WARN] Power BI push failed: {e}")
        return False


# ─── Cell 3: Continuous push loop ────────────────────────────────────────────
POLL_INTERVAL_SECONDS = 60  # Push every 60 seconds
MAX_ROWS_PER_PUSH     = 100  # Power BI streaming limit

print(f"\nStarting real-time push loop (interval={POLL_INTERVAL_SECONDS}s)")
print("Press 'Stop' in Databricks to terminate.\n")

iteration = 0
while True:
    iteration += 1
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

    try:
        # ── Read latest fraud alerts (last 5 minutes) ──────────────────────
        alerts_df = spark.table(f"{GOLD}.fraud_alerts")
        recent_df = (
            alerts_df
            .filter(col("window_start") >= f"current_timestamp() - INTERVAL 5 MINUTE")
            .orderBy(desc("risk_score"))
            .limit(MAX_ROWS_PER_PUSH)
        )

        rows = [
            {
                "timestamp":      r.window_start.strftime("%Y-%m-%dT%H:%M:%S") if r.window_start else now,
                "trader_id":      str(r.trader_id),
                "symbol":         str(r.symbol),
                "risk_score":     float(r.risk_score),
                "decision":       str(r.decision),
                "fraud_type":     str(r.fraud_type_predicted),
                "volume_spike":   float(r.volume_spike_ratio) if r.volume_spike_ratio else 0.0,
            }
            for r in recent_df.collect()
        ]

        if rows:
            ok = push_to_powerbi(rows, POWERBI_PUSH_URL)
            status = "✅" if ok else "⚠️"
            print(f"[{now}] Iter={iteration} | Pushed {len(rows)} rows | {status}")
        else:
            print(f"[{now}] Iter={iteration} | No new alerts in last 5 min")

        # ── Also push summary KPIs ──────────────────────────────────────────
        kpi_df = spark.table(f"{GOLD}.pbi_summary_kpis").limit(1)
        kpi_rows = [
            {
                "computed_at":       now,
                "total_predictions": int(r.total_predictions),
                "fraud_count":       int(r.fraud_count),
                "fraud_rate_pct":    float(r.fraud_rate_pct),
                "avg_risk_score":    float(r.avg_risk_score),
                "fraud_last_1h":     int(r.fraud_last_1h),
            }
            for r in kpi_df.collect()
        ]
        if kpi_rows:
            push_to_powerbi(kpi_rows, POWERBI_PUSH_URL.replace("alerts", "kpis"))

    except Exception as e:
        print(f"[{now}] ERROR in iteration {iteration}: {e}")

    time.sleep(POLL_INTERVAL_SECONDS)
