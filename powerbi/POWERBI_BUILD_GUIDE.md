# ╔══════════════════════════════════════════════════════════════════════╗
# ║   POWER BI DASHBOARD - COMPLETE BUILD GUIDE                         ║
# ║   Fraud Detection Platform - 3 Page Report                          ║
# ║   Style: Dark Theme + Gold/Amber Accents (matching references)      ║
# ╚══════════════════════════════════════════════════════════════════════╝

## STEP 1 — CONNECT TO DATABRICKS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. Open Power BI Desktop
2. Home → Get Data → More → Azure → Azure Databricks → Connect
3. Server Hostname: adb-7405612400876785.5.azuredatabricks.net
4. HTTP Path: /sql/1.0/warehouses/<your-warehouse-id>
   (Create SQL Warehouse in Databricks: SQL → Warehouses → Create)
5. Authentication: Azure Active Directory
6. Sign in with: waizimran75@hotmail.com

## STEP 2 — LOAD THE 6 GOLD TABLES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
In Navigator, expand: fraud_detection_catalog → gold
Select ALL of these (tick all 6):
  ✅ pbi_summary_kpis
  ✅ pbi_fraud_timeseries
  ✅ pbi_fraud_by_symbol
  ✅ pbi_fraud_by_pattern
  ✅ pbi_trader_risk_profiles
  ✅ pbi_hourly_trends
Click "Load" → Select: DirectQuery mode

## STEP 3 — APPLY DARK THEME
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
View → Themes → Browse for themes → Select:
  powerbi/FraudDetection_Theme.json

## STEP 4 — SET PAGE BACKGROUND (do for ALL pages)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Format Page → Page background:
  Color: #0D1117    Transparency: 0%
Format Page → Canvas background:
  Color: #0D1117    Transparency: 0%

## STEP 5 — ADD ALL DAX MEASURES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Modeling → New Measure → copy each measure from DAX_MEASURES.dax

══════════════════════════════════════════════════════════════════════
PAGE 1: EXECUTIVE OVERVIEW (Fraud Command Center)
══════════════════════════════════════════════════════════════════════

Canvas size: 1600 x 900 px

─── ROW 1: PAGE TITLE ─────────────────────────────────────────────
Insert → Text Box:
  Text: "FRAUD DETECTION COMMAND CENTER"
  Font: Segoe UI  Size: 22  Bold  Color: #F0A500
  Position: x=20, y=15, Width=900, Height=50

Insert → Text Box (subtitle):
  Text: "Real-Time Monitoring | FINRA Compliance Platform"
  Font: Segoe UI  Size: 11  Color: #8B949E
  Position: x=20, y=55, Width=600, Height=30

─── ROW 2: 4 KPI CARDS ────────────────────────────────────────────
Card Visual x4 (side by side):

Card 1 - Total Transactions:
  Field: [Total Transactions]
  Position: x=20,  y=100, W=360, H=130
  Title: "TOTAL TRANSACTIONS"  Font size: 11
  Value font: 36  Color: #F0A500  Bold
  Background: #1C2128
  Border: ON, Color: #F0A500, Radius: 8px

Card 2 - Fraud Cases:
  Field: [Total Fraud Cases]
  Position: x=400, y=100, W=360, H=130
  Title: "FRAUD CASES"
  Value Color: #FF4D6D
  Background: #1C2128
  Border: ON, Color: #FF4D6D

Card 3 - Fraud Rate %:
  Field: [Fraud Rate %]
  Format: 0.0%
  Position: x=780, y=100, W=360, H=130
  Title: "FRAUD RATE"
  Value Color: (Conditional: red if >5%, amber if >2%, green)
  Background: #1C2128
  Border: ON, Color: #FF4D6D

Card 4 - Avg Risk Score:
  Field: [Avg Risk Score]
  Format: 0.00
  Position: x=1160, y=100, W=360, H=130
  Title: "AVG RISK SCORE"
  Value Color: #F0A500
  Background: #1C2128
  Border: ON, Color: #F0A500

─── ROW 3: FRAUD TREND LINE CHART (WIDE) ──────────────────────────
Visual: Line Chart
  Position: x=20, y=250, W=1540, H=280
  X-axis: pbi_fraud_timeseries[minute_bucket]
  Y-axis (Primary): [Total Fraud Cases]   Line color: #F0A500  Width: 2.5
  Y-axis (Secondary): [Avg Risk Score]    Line color: #00D4AA  Width: 2
  Title: "FRAUD TRENDS OVER TIME"  Color: #C9D1D9
  Background: #1C2128
  Border: ON, Color: #30363D, Radius: 8
  Grid lines: #21262D
  Legend: ON, position: Top Right
  Shade area under primary line: ON, color: #F0A500, opacity: 15%

─── ROW 4: DONUT + BAR CHART ──────────────────────────────────────
Visual 1: Donut Chart
  Position: x=20, y=550, W=500, H=330
  Values: pbi_fraud_by_pattern[event_count]
  Legend: pbi_fraud_by_pattern[fraud_type_predicted]
  Colors: WASH_TRADE=#F0A500, LAYERING=#E85D04, SPOOFING=#FF4D6D, OTHER=#484F58
  Title: "FRAUD BY PATTERN"  Color: #C9D1D9
  Inner radius: 55%  (donut style)
  Background: #1C2128
  Border: ON, Color: #30363D

Visual 2: Clustered Bar Chart (Horizontal)
  Position: x=540, y=550, W=760, H=330
  Y-axis: pbi_fraud_by_symbol[symbol]
  X-axis: pbi_fraud_by_symbol[fraud_count]
  Bar color: #F0A500
  Data labels: ON, Color: #C9D1D9
  Title: "FRAUD BY SYMBOL"  Color: #C9D1D9
  Background: #1C2128
  Border: ON, Color: #30363D
  Sort: Descending by fraud_count

Visual 3: Card (Fraud Last Hour)
  Position: x=1320, y=550, W=240, H=155
  Field: [Fraud Last 1H]
  Title: "FRAUD LAST 1H"
  Value Color: #FF4D6D  Size: 32
  Background: #1C2128
  Border: Color: #FF4D6D

Visual 4: Card (Top Fraud Symbol)
  Position: x=1320, y=725, W=240, H=155
  Field: [Top Fraud Symbol]
  Title: "TOP FRAUD SYMBOL"
  Value Color: #F0A500  Size: 28
  Background: #1C2128
  Border: Color: #F0A500

══════════════════════════════════════════════════════════════════════
PAGE 2: TRADER RISK PROFILING
══════════════════════════════════════════════════════════════════════

─── ROW 1: PAGE TITLE ─────────────────────────────────────────────
Text: "TRADER RISK PROFILING"  Color: #F0A500  Size: 22  Bold

─── ROW 2: 3 KPI CARDS ────────────────────────────────────────────
Card 1: [High Risk Traders]   Border: #FF4D6D  Value: Red
Card 2: [Flagged Traders]     Border: #FF4D6D  Value: Red
Card 3: [Under Watch]         Border: #F0A500  Value: Amber

─── ROW 3: TABLE + SCATTER + RADAR ───────────────────────────────
Table Visual (Left):
  Position: x=20, y=250, W=480, H=520
  Columns:
    trader_id         → rename "Trader ID"
    risk_tier         → rename "Risk"   (Conditional format: HIGH=red bg, MEDIUM=amber bg)
    fraud_rate_pct    → rename "Fraud %" (format: 0.0%)
    max_risk_score    → rename "Max Risk"
    trader_status     → rename "Status" (FLAGGED=red chip, WATCH=amber chip)
  Background: #1C2128
  Header background: #21262D  Header color: #F0A500
  Row alternating: #1C2128 / #21262D
  Font color: #C9D1D9
  Border: #30363D

Scatter Chart (Center):
  Position: x=520, y=250, W=650, H=520
  X-axis: total_volume_traded   Label: "Volume Traded"
  Y-axis: avg_risk_score        Label: "Risk Score"
  Size:   fraud_windows
  Legend: risk_tier
  Colors: HIGH=#FF4D6D, MEDIUM=#F0A500, LOW=#2DBA4E
  Title: "RISK SCORE vs VOLUME TRADED"
  Background: #1C2128

Slicer (Right Top):
  Position: x=1190, y=250, W=380, H=140
  Field: pbi_trader_risk_profiles[risk_tier]
  Style: Buttons  Orientation: Horizontal
  Selected color: #F0A500  Unselected: #30363D
  Title: "FILTER BY RISK TIER"

Slicer (Right Bottom):
  Position: x=1190, y=410, W=380, H=140
  Field: pbi_trader_risk_profiles[trader_status]
  Style: Buttons
  Selected: #FF4D6D  for FLAGGED, #F0A500 for WATCH, #2DBA4E for NORMAL
  Title: "FILTER BY STATUS"

─── ROW 4: BOTTOM BAR CHART ──────────────────────────────────────
Clustered Bar Chart (Bottom):
  Position: x=520, y=790, W=650, H=90
  (Add extra bar chart showing wash_trade_rate vs layering_rate by trader)

══════════════════════════════════════════════════════════════════════
PAGE 3: TIME INTELLIGENCE
══════════════════════════════════════════════════════════════════════

─── LEFT: FRAUD HEATMAP ───────────────────────────────────────────
Matrix Visual:
  Position: x=20, y=90, W=750, H=530
  Rows: pbi_hourly_trends[hour_of_day]     (rename "Hour")
  Columns: pbi_hourly_trends[day_of_week]  (rename Mon/Tue/Wed/Thu/Fri/Sat/Sun)
  Values: SUM(fraud_count)
  Conditional formatting (Background color):
    Lowest:  #21262D  (dark - low fraud)
    Middle:  #F0A500  (amber - medium)
    Highest: #FF4D6D  (red - high fraud)
  Title: "FRAUD HEATMAP - HOUR vs DAY"  Color: #C9D1D9
  Background: #1C2128
  Header color: #F0A500

─── RIGHT: 24H AREA CHART ─────────────────────────────────────────
Area Chart:
  Position: x=790, y=90, W=790, H=300
  X-axis: pbi_hourly_trends[hour_bucket]
  Y-axis: pbi_hourly_trends[fraud_rate_pct]
  Line color: #F0A500  Width: 2.5
  Fill: #F0A500  Opacity: 20%
  Add constant line at Y=5 (5% threshold):
    Color: #FF4D6D  Style: Dashed  Label: "Alert Threshold"
  Title: "24-HOUR FRAUD TREND"
  Background: #1C2128

─── BOTTOM LEFT: PEAK HOURS BAR ──────────────────────────────────
Clustered Column Chart:
  Position: x=20, y=640, W=490, H=240
  X-axis: pbi_hourly_trends[hour_of_day]
  Y-axis: SUM(fraud_count)
  Color rule: Top 3 hours = #FF4D6D, Rest = #F0A500
  Title: "PEAK FRAUD HOURS"
  Background: #1C2128

─── BOTTOM CENTER: ACTIVE TRADERS LINE ───────────────────────────
Line Chart:
  Position: x=530, y=640, W=490, H=240
  X-axis: hour_bucket
  Y-axis: active_traders
  Line color: #00D4AA  Width: 2.5
  Fill: #00D4AA  Opacity: 15%
  Title: "ACTIVE TRADERS BY HOUR"
  Background: #1C2128

─── BOTTOM RIGHT: 4 MINI KPI CARDS ───────────────────────────────
Card 1: [Peak Fraud Hour]      "PEAK HOUR"     Color: #F0A500
Card 2: [Fraud This Hour]      "THIS HOUR"     Color: #FF4D6D
Card 3: [Fraud Rate This Hour] "HOURLY RATE"   Color: #F0A500
Card 4: [Active Traders Now]   "ACTIVE TRADERS" Color: #00D4AA
Position: x=1040, y=640, W=530, H=240 (2x2 grid)

══════════════════════════════════════════════════════════════════════
FINAL STEPS
══════════════════════════════════════════════════════════════════════

1. Add navigation buttons between pages:
   Insert → Buttons → Blank
   Set Action: Page Navigation → Target page
   Style the button with gold background, dark text

2. Add page names in bottom tabs:
   Page 1: "Command Center"
   Page 2: "Trader Risk"
   Page 3: "Time Intelligence"

3. Publish to Power BI Service:
   Home → Publish → Select workspace

4. Set Scheduled Refresh:
   Power BI Service → Dataset → Settings → Scheduled Refresh
   Frequency: Every 30 minutes

5. Set Data Alerts on Cards:
   Fraud Rate % > 5%  → Email alert
   Fraud Last 1H > 50 → Push notification
