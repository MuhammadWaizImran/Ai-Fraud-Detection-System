"""
powerbi/setup_powerbi.py
Auto-publishes the Fraud Detection Power BI dataset to Power BI Service
using the Power BI REST API with Azure AD authentication.

Requirements:
  pip install requests msal

Steps performed:
  1. Authenticate via MSAL (Azure AD - requires Power BI licence)
  2. Create / update a workspace dataset with the 6 Gold tables schema
  3. Print connection instructions for Power BI Desktop
"""

import json
import os
import sys
import requests

# ── Config ─────────────────────────────────────────────────────────────────────
BASE_DIR   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CFG_FILE   = os.path.join(BASE_DIR, "azure_config.json")

def load_config():
    if not os.path.exists(CFG_FILE):
        print("[ERR] azure_config.json not found. Run post_terraform_setup.py first.")
        sys.exit(1)
    with open(CFG_FILE) as f:
        return json.load(f)

cfg = load_config()

TENANT_ID     = cfg.get("TENANT_ID", "")
DBW_HOST      = cfg.get("DATABRICKS_HOST", "")
DBW_URL       = cfg.get("DATABRICKS_URL", f"https://{DBW_HOST}")

# Power BI workspace (group) — "My Workspace" = empty string
PBI_WORKSPACE = ""   # Set to your Power BI Group ID if not using My Workspace

DATASET_NAME  = "FraudDetectionLive"

# ── Dataset schema (matches Gold Delta tables) ─────────────────────────────────
DATASET_SCHEMA = {
    "name": DATASET_NAME,
    "defaultMode": "Push",
    "tables": [
        {
            "name": "SummaryKPIs",
            "columns": [
                {"name": "computed_at",       "dataType": "DateTime"},
                {"name": "total_predictions", "dataType": "Int64"},
                {"name": "fraud_count",       "dataType": "Int64"},
                {"name": "suspicious_count",  "dataType": "Int64"},
                {"name": "safe_count",        "dataType": "Int64"},
                {"name": "fraud_rate_pct",    "dataType": "Double"},
                {"name": "avg_risk_score",    "dataType": "Double"},
                {"name": "max_risk_score",    "dataType": "Double"},
                {"name": "fraud_last_1h",     "dataType": "Int64"},
            ]
        },
        {
            "name": "FraudTimeSeries",
            "columns": [
                {"name": "minute_bucket",     "dataType": "DateTime"},
                {"name": "total_events",      "dataType": "Int64"},
                {"name": "fraud_count",       "dataType": "Int64"},
                {"name": "suspicious_count",  "dataType": "Int64"},
                {"name": "safe_count",        "dataType": "Int64"},
                {"name": "avg_risk_score",    "dataType": "Double"},
                {"name": "max_risk_score",    "dataType": "Double"},
                {"name": "fraud_rate_pct",    "dataType": "Double"},
                {"name": "total_volume",      "dataType": "Double"},
                {"name": "hour_of_day",       "dataType": "Int64"},
                {"name": "day_of_week",       "dataType": "Int64"},
            ]
        },
        {
            "name": "FraudBySymbol",
            "columns": [
                {"name": "symbol",            "dataType": "String"},
                {"name": "total_events",      "dataType": "Int64"},
                {"name": "fraud_count",       "dataType": "Int64"},
                {"name": "suspicious_count",  "dataType": "Int64"},
                {"name": "avg_risk_score",    "dataType": "Double"},
                {"name": "max_risk_score",    "dataType": "Double"},
                {"name": "total_volume",      "dataType": "Double"},
                {"name": "fraud_rate_pct",    "dataType": "Double"},
                {"name": "risk_tier",         "dataType": "String"},
            ]
        },
        {
            "name": "FraudByPattern",
            "columns": [
                {"name": "fraud_type_predicted",       "dataType": "String"},
                {"name": "event_count",                "dataType": "Int64"},
                {"name": "fraud_count",                "dataType": "Int64"},
                {"name": "suspicious_count",           "dataType": "Int64"},
                {"name": "avg_risk_score",             "dataType": "Double"},
                {"name": "max_risk_score",             "dataType": "Double"},
                {"name": "distinct_traders_affected",  "dataType": "Int64"},
                {"name": "distinct_symbols_affected",  "dataType": "Int64"},
                {"name": "pct_of_total",               "dataType": "Double"},
            ]
        },
        {
            "name": "TraderRiskProfiles",
            "columns": [
                {"name": "trader_id",          "dataType": "String"},
                {"name": "total_windows",      "dataType": "Int64"},
                {"name": "fraud_windows",      "dataType": "Int64"},
                {"name": "suspicious_windows", "dataType": "Int64"},
                {"name": "avg_risk_score",     "dataType": "Double"},
                {"name": "max_risk_score",     "dataType": "Double"},
                {"name": "fraud_rate_pct",     "dataType": "Double"},
                {"name": "avg_volume_spike",   "dataType": "Double"},
                {"name": "wash_trade_rate",    "dataType": "Double"},
                {"name": "layering_rate",      "dataType": "Double"},
                {"name": "risk_tier",          "dataType": "String"},
                {"name": "trader_status",      "dataType": "String"},
                {"name": "total_volume_traded","dataType": "Double"},
            ]
        },
        {
            "name": "HourlyTrends",
            "columns": [
                {"name": "hour_bucket",       "dataType": "DateTime"},
                {"name": "hour_label",        "dataType": "String"},
                {"name": "total_events",      "dataType": "Int64"},
                {"name": "fraud_count",       "dataType": "Int64"},
                {"name": "suspicious_count",  "dataType": "Int64"},
                {"name": "avg_risk_score",    "dataType": "Double"},
                {"name": "fraud_rate_pct",    "dataType": "Double"},
                {"name": "total_volume",      "dataType": "Double"},
                {"name": "active_traders",    "dataType": "Int64"},
                {"name": "active_symbols",    "dataType": "Int64"},
                {"name": "hour_of_day",       "dataType": "Int64"},
                {"name": "day_of_week",       "dataType": "Int64"},
            ]
        }
    ]
}


def get_pbi_token():
    """Get Power BI access token using device code flow (interactive)."""
    try:
        import msal
    except ImportError:
        print("[ERR] msal not installed. Run: pip install msal")
        return None

    app = msal.PublicClientApplication(
        client_id="04b07795-8ddb-461a-bbee-02f9e1bf7b46",  # Azure CLI app
        authority=f"https://login.microsoftonline.com/{TENANT_ID}"
    )

    scopes = ["https://analysis.windows.net/powerbi/api/.default"]
    result = app.acquire_token_interactive(scopes=scopes)
    if "access_token" in result:
        print("[*] Power BI token acquired.")
        return result["access_token"]
    else:
        print(f"[ERR] Token error: {result.get('error_description', result)}")
        return None


def pbi_request(token, method, path, body=None):
    """Make a Power BI REST API call."""
    base = "https://api.powerbi.com/v1.0/myorg"
    if PBI_WORKSPACE:
        base = f"https://api.powerbi.com/v1.0/myorg/groups/{PBI_WORKSPACE}"

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    url = f"{base}{path}"
    resp = requests.request(method, url, headers=headers,
                            json=body, timeout=30)
    if resp.status_code not in (200, 201, 204):
        print(f"[WARN] {method} {path} → {resp.status_code}: {resp.text[:300]}")
        return None
    return resp.json() if resp.content else {}


def main():
    print("\n" + "="*60)
    print("  Power BI Dataset Publisher — Fraud Detection Platform")
    print("="*60)
    print(f"\n  Databricks  : {DBW_URL}")
    print(f"  Dataset     : {DATASET_NAME}")

    print("\n[*] Acquiring Power BI access token (browser will open)...")
    token = get_pbi_token()
    if not token:
        print_manual_instructions()
        return

    # Check existing datasets
    existing = pbi_request(token, "GET", "/datasets") or {}
    datasets = existing.get("value", [])
    existing_id = next(
        (d["id"] for d in datasets if d["name"] == DATASET_NAME), None
    )

    if existing_id:
        print(f"[*] Dataset '{DATASET_NAME}' already exists (id={existing_id})")
        print("[*] Deleting and recreating with latest schema...")
        pbi_request(token, "DELETE", f"/datasets/{existing_id}")

    # Create dataset
    print(f"[*] Creating dataset '{DATASET_NAME}'...")
    result = pbi_request(token, "POST", "/datasets", DATASET_SCHEMA)
    if not result:
        print("[ERR] Failed to create dataset.")
        print_manual_instructions()
        return

    dataset_id = result.get("id", "")
    print(f"[*] Dataset created: {dataset_id}")

    # Save dataset ID to config
    cfg["POWERBI_DATASET_ID"] = dataset_id
    with open(CFG_FILE, "w") as f:
        json.dump(cfg, f, indent=2)
    print(f"[*] Dataset ID saved to azure_config.json")

    print("\n" + "="*60)
    print("  ✅ Power BI Dataset Published Successfully!")
    print("="*60)
    print(f"\n  Dataset ID   : {dataset_id}")
    print(f"  Dataset Name : {DATASET_NAME}")
    print_manual_instructions(dataset_id)


def print_manual_instructions(dataset_id=""):
    print("\n" + "="*60)
    print("  POWER BI DESKTOP — CONNECTION INSTRUCTIONS")
    print("="*60)
    print(f"""
1. CONNECT POWER BI DESKTOP TO DATABRICKS
   ─────────────────────────────────────────
   a. Open Power BI Desktop
   b. Click: Home → Get Data → Azure Databricks
   c. Enter:
      Server Hostname : {DBW_HOST or '<your-workspace>.azuredatabricks.net'}
      HTTP Path       : /sql/1.0/warehouses/<sql-warehouse-id>
      (Find HTTP Path in Databricks → SQL Warehouses → Connection Details)

2. AUTHENTICATE
   ─────────────
   Select: Azure Active Directory (OAuth 2)
   Sign in with: waizimran75@hotmail.com

3. SELECT GOLD TABLES
   ───────────────────
   Navigate to: fraud_detection_catalog → gold
   Select all 6 tables:
   ✅ pbi_summary_kpis          → Card KPIs (fraud rate, total events)
   ✅ pbi_fraud_timeseries      → Line chart (fraud over time)
   ✅ pbi_fraud_by_symbol       → Bar chart (by crypto symbol)
   ✅ pbi_fraud_by_pattern      → Donut chart (by fraud type)
   ✅ pbi_trader_risk_profiles  → Table (risky traders)
   ✅ pbi_hourly_trends         → Heatmap (fraud by hour)

4. SET IMPORT / DIRECTQUERY MODE
   ────────────────────────────────
   Recommended: DirectQuery
   (Gives real-time data — refreshes automatically with each report open)

5. BUILD VISUALS (see powerbi/REPORT_LAYOUT.md for full guide)
   ──────────────────────────────────────────────────────────────
   Page 1 — Executive Overview:
     • Card: fraud_rate_pct, fraud_count, avg_risk_score, fraud_last_1h
     • Line chart: pbi_fraud_timeseries → minute_bucket vs fraud_count
     • Donut: pbi_fraud_by_pattern → event_count by fraud_type_predicted

   Page 2 — Market Analysis:
     • Bar chart: pbi_fraud_by_symbol → fraud_count by symbol
     • Scatter: pbi_fraud_by_symbol → avg_risk_score vs total_volume
     • Table: all columns, sorted by fraud_rate_pct desc

   Page 3 — Trader Risk Profiling:
     • Table: pbi_trader_risk_profiles filtered by risk_tier = 'HIGH'
     • Scatter: avg_risk_score vs fraud_windows (size = total_volume)
     • Slicer: risk_tier, trader_status

   Page 4 — Time Intelligence:
     • Matrix: pbi_hourly_trends → hour_of_day (rows) vs day_of_week (cols), values = fraud_count
     • Line: hour_bucket vs fraud_rate_pct

6. SCHEDULE AUTO-REFRESH
   ───────────────────────
   Publish to Power BI Service → Dataset → Settings → Scheduled Refresh
   Set frequency: Every 30 minutes (matches Databricks job schedule)
""")
    if dataset_id:
        print(f"  Power BI Dataset URL:")
        print(f"  https://app.powerbi.com/datasets/{dataset_id}")


if __name__ == "__main__":
    main()
