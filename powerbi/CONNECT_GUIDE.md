# Power BI Quick Connect Guide

## Step 1 — Wait for Databricks to finish provisioning (auto)

Once `terraform apply` completes, you will receive the workspace URL.
Then `post_terraform_setup.py` runs automatically to upload notebooks and create jobs.

---

## Step 2 — Create a Databricks SQL Warehouse

1. Open your Databricks workspace URL
2. Click **SQL** in the left sidebar → **SQL Warehouses** → **Create SQL Warehouse**
3. Configure:
   - Name: `fraud-detection-warehouse`
   - Cluster Size: `Small` (2 DBUs)
   - Auto Stop: `10 minutes`
4. Click **Create**
5. Once running, click on it → **Connection Details** → copy the **HTTP Path**
   - Format: `/sql/1.0/warehouses/abc123def456`

---

## Step 3 — Connect Power BI Desktop

1. **Download**: [Power BI Desktop](https://powerbi.microsoft.com/desktop) (free)
2. Open Power BI Desktop
3. **Home** → **Get Data** → Search: `Databricks` → Select **Azure Databricks**
4. Enter connection details:

```
Server Hostname:  <your-workspace-url>   (from azure_config.json → DATABRICKS_HOST)
HTTP Path:        /sql/1.0/warehouses/<warehouse-id>
```

5. Authentication: **Azure Active Directory (OAuth 2)**
6. Click **Sign In** → login with `waizimran75@hotmail.com`

---

## Step 4 — Load the 6 Gold Tables

In the Navigator, expand:
```
fraud_detection_catalog → gold
```

Select these 6 tables:
- ✅ `pbi_summary_kpis`
- ✅ `pbi_fraud_timeseries`
- ✅ `pbi_fraud_by_symbol`
- ✅ `pbi_fraud_by_pattern`
- ✅ `pbi_trader_risk_profiles`
- ✅ `pbi_hourly_trends`

Select mode: **DirectQuery** → Click **Load**

---

## Step 5 — Build the Report

See **REPORT_LAYOUT.md** for the complete 4-page report design:
- Page 1: Executive Overview (KPI cards + trend line)
- Page 2: Market & Symbol Analysis
- Page 3: Trader Risk Profiling
- Page 4: Time Intelligence & Heatmaps

---

## Step 6 — Publish to Power BI Service

1. **Home** → **Publish** → Select workspace
2. In Power BI Service: **Dataset** → **Settings** → **Scheduled Refresh**
3. Set refresh: **Every 30 minutes**

---

## Step 7 — (Optional) Real-Time Streaming

For live tiles that update every 60 seconds:

1. In Power BI Service: **New** → **Streaming Dataset** → **API**
2. Configure the schema with these fields:
   ```json
   {
     "timestamp": "DateTime",
     "trader_id": "Text",
     "symbol": "Text",
     "risk_score": "Number",
     "decision": "Text",
     "fraud_type": "Text"
   }
   ```
3. Copy the **Push URL**
4. In Databricks Key Vault: Add secret `powerbi-push-url` = the URL
5. Run notebook `07_powerbi_realtime_push` in Databricks

---

## Troubleshooting

| Error | Fix |
|---|---|
| `Connection refused` | Make sure SQL Warehouse is Running (not stopped) |
| `Catalog not found` | Run notebook `04_ml_training_registry` first to create catalog |
| `Table not found` | Run notebook `06_gold_kpi_aggregations` first |
| `Auth failed` | Re-sign in with Azure AD in Power BI Desktop |
| Slow refresh | Switch to Import mode instead of DirectQuery |
