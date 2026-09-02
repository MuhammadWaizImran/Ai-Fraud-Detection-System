# Power BI Report Layout Guide — Fraud Detection Platform
# ═══════════════════════════════════════════════════════════

## Overview
This guide defines all 4 report pages, their visuals, and DAX measures
for the **FraudDetectionLive** Power BI report connected to Azure Databricks.

---

## Data Sources (Gold Layer — DirectQuery)

| Power BI Table | Databricks Table | Refresh |
|---|---|---|
| SummaryKPIs | `gold.pbi_summary_kpis` | Every 30 min |
| FraudTimeSeries | `gold.pbi_fraud_timeseries` | Every 30 min |
| FraudBySymbol | `gold.pbi_fraud_by_symbol` | Every 30 min |
| FraudByPattern | `gold.pbi_fraud_by_pattern` | Every 30 min |
| TraderRiskProfiles | `gold.pbi_trader_risk_profiles` | Every 30 min |
| HourlyTrends | `gold.pbi_hourly_trends` | Every 30 min |

---

## DAX Measures (add these in Power BI Desktop)

```dax
-- Overall Fraud Rate
Fraud Rate % = 
DIVIDE(SUM(SummaryKPIs[fraud_count]), SUM(SummaryKPIs[total_predictions]), 0) * 100

-- High Risk Trader Count
High Risk Traders = 
CALCULATE(COUNTROWS(TraderRiskProfiles), TraderRiskProfiles[risk_tier] = "HIGH")

-- Flagged Traders
Flagged Traders = 
CALCULATE(COUNTROWS(TraderRiskProfiles), TraderRiskProfiles[trader_status] = "FLAGGED")

-- Rolling 24h Fraud Count
Fraud Last 24H = 
CALCULATE(
    SUM(HourlyTrends[fraud_count]),
    DATESINPERIOD(HourlyTrends[hour_bucket], MAX(HourlyTrends[hour_bucket]), -24, HOUR)
)

-- Avg Risk Score (formatted)
Avg Risk Score = FORMAT(AVERAGE(TraderRiskProfiles[avg_risk_score]), "0.00%")

-- Top Fraud Symbol
Top Fraud Symbol = 
CALCULATE(
    SELECTEDVALUE(FraudBySymbol[symbol]),
    TOPN(1, FraudBySymbol, FraudBySymbol[fraud_count], DESC)
)

-- Volume Spike Alert
Volume Spike Alert = 
IF(MAX(FraudTimeSeries[avg_volume_spike]) > 3.0, "🔴 SPIKE DETECTED", "🟢 NORMAL")
```

---

## Page 1 — Executive Overview

**Theme**: Dark (Background: #0D1117, Text: #FFFFFF)

| Visual | Type | Fields | Position |
|---|---|---|---|
| Total Predictions | Card | `SummaryKPIs[total_predictions]` | Top-left |
| Fraud Count | Card | `SummaryKPIs[fraud_count]` | Top-center-left |
| Fraud Rate % | Card | `SummaryKPIs[fraud_rate_pct]` | Top-center-right |
| Avg Risk Score | Card | `SummaryKPIs[avg_risk_score]` | Top-right |
| Fraud Over Time | Line Chart | X: `minute_bucket`, Y: `fraud_count`, secondary: `avg_risk_score` | Center-wide |
| Fraud by Pattern | Donut Chart | Values: `event_count`, Legend: `fraud_type_predicted` | Bottom-left |
| Suspicious vs Fraud | Stacked Bar | X: `symbol`, Y: fraud + suspicious stacked | Bottom-right |

**Conditional Formatting on Cards**:
- `fraud_rate_pct > 5%` → Red background
- `avg_risk_score > 0.7` → Orange background

---

## Page 2 — Market & Symbol Analysis

| Visual | Type | Fields | Notes |
|---|---|---|---|
| Symbol Risk Heatmap | Matrix | Rows: `symbol`, Values: `fraud_rate_pct` | Color scale: green→red |
| Volume vs Fraud | Scatter Plot | X: `total_volume`, Y: `fraud_rate_pct`, Size: `avg_risk_score`, Color: `risk_tier` | |
| Symbol Comparison | Clustered Bar | X: `symbol`, Y1: `fraud_count`, Y2: `suspicious_count` | |
| Symbol Table | Table | All columns sorted by `fraud_rate_pct` desc | Enable drill-through |
| Symbol Slicer | Slicer | `symbol` | Multi-select |
| Risk Tier Slicer | Slicer | `risk_tier` | Buttons style |

---

## Page 3 — Trader Risk Profiling

| Visual | Type | Fields | Notes |
|---|---|---|---|
| HIGH Risk Traders | Card | `[High Risk Traders]` measure | Red text |
| Flagged Traders | Card | `[Flagged Traders]` measure | Red background |
| Trader Risk Table | Table | `trader_id`, `risk_tier`, `trader_status`, `fraud_rate_pct`, `max_risk_score`, `total_volume_traded` | Sort by `max_risk_score` |
| Risk vs Volume | Scatter | X: `total_volume_traded`, Y: `max_risk_score`, Size: `fraud_windows`, Color: `risk_tier` | |
| Wash Trade Radar | Radar/Spider | Fields: `wash_trade_rate`, `layering_rate`, `avg_cancel_ratio`, `avg_volume_spike` | |
| Status Filter | Slicer | `trader_status`: FLAGGED / WATCH / NORMAL | |

**Row-Level Security** (set in Power BI Service):
```dax
-- Compliance role: only sees FLAGGED + WATCH traders
[trader_status] IN {"FLAGGED", "WATCH"}
```

---

## Page 4 — Time Intelligence & Trends

| Visual | Type | Fields | Notes |
|---|---|---|---|
| Fraud Heatmap | Matrix | Rows: `hour_of_day`, Cols: `day_of_week`, Values: `fraud_count` | Conditional color |
| 24h Trend | Area Chart | X: `hour_bucket`, Y: `fraud_rate_pct` | With reference line at 5% |
| Peak Hours | Bar Chart | X: `hour_of_day`, Y: `fraud_count` | Show top 5 |
| Active Traders Timeline | Line Chart | X: `hour_bucket`, Y: `active_traders` | |
| Day of Week Summary | Bar Chart | X: `day_of_week`, Y: `fraud_count` | Rename 1-7 to Mon-Sun |

---

## Scheduled Refresh Configuration

1. Publish report to **Power BI Service**
2. Go to: Dataset → Settings → Scheduled Refresh
3. Configure:
   - **Frequency**: Every 30 minutes
   - **Gateway**: Azure Databricks (requires on-premises gateway or cloud connection)
   - **Credentials**: OAuth2 with `waizimran75@hotmail.com`

**OR use DirectQuery** (no refresh needed — queries run live against Databricks SQL Warehouse)

---

## Alerts (Power BI Service)

Set data-driven alerts on these cards:
| Metric | Alert Threshold | Action |
|---|---|---|
| Fraud Rate % | > 5% | Email notification |
| Fraud Last 1H | > 50 | Push notification |
| High Risk Traders | > 10 | Email notification |

---

## Sharing & Export

- Publish to: `app.powerbi.com` → Workspace: **Fraud Detection Platform**
- Create an **App** to share with compliance/risk teams
- Enable **PDF Export** for daily fraud reports
- Set **Row-Level Security** for multi-tenant compliance views
