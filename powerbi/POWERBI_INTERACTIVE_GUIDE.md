# Power BI Interactive Dashboard - Complete Build Guide
## FINRA AI Fraud Detection Platform

> [!IMPORTANT]
> This guide walks you through creating a **5-page interactive Power BI dashboard** step by step.
> Each page has **filters that update all charts dynamically** — exactly like you wanted.

---

## Step 1: Connect Your Data

### Option A: CSV Import (Services OFF — Use This Now)

1. Open **Power BI Desktop** (Free download from [powerbi.microsoft.com/desktop](https://powerbi.microsoft.com/desktop))
2. Click **Home** → **Get Data** → **Text/CSV**
3. Navigate to `Finra Project/powerbi/data/`
4. Import **ALL 6 CSV files** one by one:

| File | Purpose | Rows |
|---|---|---|
| `pbi_summary_kpis.csv` | Executive KPI cards | 1 |
| `pbi_fraud_timeseries.csv` | Fraud trend charts | ~1,008 |
| `pbi_fraud_by_symbol.csv` | Symbol analysis | 11 |
| `pbi_fraud_by_pattern.csv` | Pattern breakdown | 5 |
| `pbi_trader_risk_profiles.csv` | Trader investigation | 100 |
| `pbi_hourly_trends.csv` | Hourly heatmaps | 168 |

5. For each file: Click **Load** (not Transform Data)

### Option B: Live Databricks Connection (When Azure Services ON)

1. **Home** → **Get Data** → Search `Databricks` → **Azure Databricks**
2. Server: `<your-workspace-url>` (from `azure_config.json`)
3. HTTP Path: `/sql/1.0/warehouses/<warehouse-id>`
4. Auth: **Azure Active Directory** → Sign in
5. Navigate: `fraud_detection_catalog → gold` → Select all 6 `pbi_*` tables
6. Choose **DirectQuery** for real-time data → **Load**

---

## Step 2: Apply the Custom Theme

1. Go to **View** → **Themes** → **Browse for themes**
2. Select `Finra Project/powerbi/FraudDetection_Theme.json`
3. This applies our dark blue + red + green color palette

---

## Step 3: Create Relationships (Data Model)

Go to **Model View** (left sidebar icon):

```
pbi_fraud_timeseries.hour_of_day  →  pbi_hourly_trends.hour_of_day
```

> [!TIP]
> Most tables are pre-aggregated (star schema), so they don't need many relationships.
> Each table is designed to be used independently on its own page.

---

## Step 4: Create DAX Measures

Go to **Modeling** → **New Measure** and create these measures one at a time.
All DAX formulas are also in `powerbi/DAX_MEASURES.dax`.

### Essential Measures:

```dax
Fraud Rate % = 
DIVIDE(
    SUM(pbi_summary_kpis[fraud_count]),
    SUM(pbi_summary_kpis[total_predictions]),
    0
) * 100
```

```dax
Fraud Rate Color = 
SWITCH(
    TRUE(),
    [Fraud Rate %] >= 10, "#FF4D6D",
    [Fraud Rate %] >= 5,  "#F0A500",
    "#2DBA4E"
)
```

```dax
Total Fraud Cases = SUM(pbi_summary_kpis[fraud_count])
Total Transactions = SUM(pbi_summary_kpis[total_predictions])
Avg Risk Score = AVERAGE(pbi_summary_kpis[avg_risk_score])
High Risk Traders = CALCULATE(COUNTROWS(pbi_trader_risk_profiles), pbi_trader_risk_profiles[risk_tier] = "HIGH")
```

> [!NOTE]
> Full list of 30+ DAX measures is in `powerbi/DAX_MEASURES.dax`. Copy them all.

---

## Step 5: Build the 5 Pages

### PAGE 1: Executive Overview

**Right-click** the page tab at bottom → **Rename** → `Executive Overview`

#### Top Section: KPI Cards (6 Cards in a Row)
| Card | Value Field | Format |
|---|---|---|
| Total Scanned | `pbi_summary_kpis[total_predictions]` | Number, No decimals |
| Fraud Detected | `pbi_summary_kpis[fraud_count]` | Number, Red font |
| Suspicious | `pbi_summary_kpis[suspicious_count]` | Number, Amber font |
| Safe Cleared | `pbi_summary_kpis[safe_count]` | Number, Green font |
| Avg Risk Score | `pbi_summary_kpis[avg_risk_score]` | 4 decimals |
| Fraud Rate | `[Fraud Rate %]` measure | Percentage |

**How to create each KPI Card:**
1. Click **Visualizations** → **Card** visual
2. Drag the field into **Fields** area
3. Resize to fit 6 across the top
4. Format → **Callout value** → Size: 28, Bold, Color by risk level
5. Format → **Category label** → Size: 10, UPPERCASE

#### Middle Section: Fraud Timeline (Combo Chart)
1. Add **Clustered Column + Line** chart (combo chart)
2. **X-axis**: `pbi_fraud_timeseries[minute_bucket]`
3. **Column Y-axis**: `pbi_fraud_timeseries[fraud_count]` (color: Red)
4. **Column Y-axis**: `pbi_fraud_timeseries[suspicious_count]` (color: Amber)
5. **Line Y-axis**: `pbi_fraud_timeseries[avg_risk_score]` (color: Blue, secondary axis)
6. Turn ON **Data labels** for the line

#### Middle Right: Risk Classification Donut
1. Add **Donut Chart** visual
2. **Legend**: Create a calculated column or use 3 separate values
3. **Values**: fraud_count, suspicious_count, safe_count from `pbi_summary_kpis`
4. Colors: Red, Amber, Green
5. **Detail labels**: Show value + percentage

#### Bottom: Filters
1. Add **Slicer** visual → `pbi_fraud_timeseries[hour_of_day]` → Format as **Between** slider
2. Add **Slicer** visual → `pbi_fraud_timeseries[minute_bucket]` → Format as **Date Range**
3. Add **Slicer** → `pbi_fraud_by_symbol[symbol]` → Format as **Dropdown**

> [!IMPORTANT]
> **Make Slicers affect ALL visuals on the page:** By default, slicers affect all visuals on the same page. That's exactly what we want — when you change the time filter, ALL charts update!

---

### PAGE 2: Fraud Analysis & Patterns

**Add new page** → Rename → `Fraud Analysis`

#### Left: Fraud by Attack Pattern (Horizontal Bar Chart)
1. Add **Bar Chart** visual
2. **Y-axis**: `pbi_fraud_by_pattern[fraud_type_predicted]`
3. **X-axis**: `pbi_fraud_by_pattern[fraud_count]`
4. **Conditional formatting**: Format → Data colors → Based on `fraud_count` (gradient Red)
5. **Data labels**: ON, Outside end

#### Right: Fraud by Crypto Symbol (Donut/Pie Chart)
1. Add **Donut Chart**
2. **Legend**: `pbi_fraud_by_symbol[symbol]`
3. **Values**: `pbi_fraud_by_symbol[fraud_count]`
4. **Detail labels**: Symbol name + Count

#### Bottom Left: Risk Score Histogram
1. Add **Clustered Column Chart**
2. Create a **histogram bin** calculated column:
```dax
Risk Bin = 
SWITCH(
    TRUE(),
    pbi_trader_risk_profiles[max_risk_score] >= 0.9, "0.9-1.0",
    pbi_trader_risk_profiles[max_risk_score] >= 0.8, "0.8-0.9",
    pbi_trader_risk_profiles[max_risk_score] >= 0.7, "0.7-0.8",
    pbi_trader_risk_profiles[max_risk_score] >= 0.6, "0.6-0.7",
    pbi_trader_risk_profiles[max_risk_score] >= 0.5, "0.5-0.6",
    pbi_trader_risk_profiles[max_risk_score] >= 0.4, "0.4-0.5",
    "Below 0.4"
)
```
3. **X-axis**: Risk Bin, **Y-axis**: Count of trader_id

#### Bottom Right: Volume vs Risk Scatter
1. Add **Scatter Chart**
2. **X-axis**: `avg_volume_spike`
3. **Y-axis**: `max_risk_score`
4. **Size**: `total_volume_traded`
5. **Legend/Color**: `risk_tier` (Red=HIGH, Amber=MEDIUM, Green=LOW)
6. **Details**: `trader_id`

#### Filters for this page:
1. **Slicer**: `pbi_fraud_by_pattern[fraud_type_predicted]` → Dropdown
2. **Slicer**: `pbi_fraud_by_symbol[symbol]` → Dropdown multi-select

---

### PAGE 3: Crypto Market Terminal

**Add new page** → Rename → `Crypto Market`

> [!NOTE]
> Since Power BI cannot do real-time crypto API calls like Streamlit, this page focuses on which crypto symbols are most targeted by fraud.

#### Top KPIs (4 Cards):
| Card | Value |
|---|---|
| Total Symbols Monitored | `DISTINCTCOUNT(pbi_fraud_by_symbol[symbol])` |
| Highest Risk Symbol | `[Top Fraud Symbol]` measure |
| Total Market Volume | `SUM(pbi_fraud_by_symbol[total_volume])` |
| Avg Symbol Risk | `AVERAGE(pbi_fraud_by_symbol[avg_risk_score])` |

#### Main Visual: Symbol Comparison Table (Matrix)
1. Add **Matrix** visual
2. **Rows**: `pbi_fraud_by_symbol[symbol]`
3. **Values**: fraud_count, suspicious_count, avg_risk_score, total_volume, fraud_rate_pct
4. **Conditional formatting** on each column:
   - `fraud_count`: Data bars (Red gradient)
   - `avg_risk_score`: Background color (Green → Red scale)
   - `fraud_rate_pct`: Icons (traffic light)

#### Right: Symbol Risk Treemap
1. Add **Treemap** visual
2. **Category**: `symbol`
3. **Values**: `fraud_count`
4. **Conditional formatting**: By `avg_risk_score` (Green → Red)

#### Bottom: Fraud Volume by Symbol (Stacked Bar)
1. Add **Stacked Bar Chart**
2. **Y-axis**: `symbol`
3. **X-axis**: `total_volume`
4. **Legend**: `risk_tier`

#### Drill-Down (Click to See Details):
1. **Enable Drill Through**: 
   - Create a new hidden page called `Symbol Detail`
   - On that page, add a **Drill Through** filter: `pbi_fraud_by_symbol[symbol]`
   - Add all detail visuals for that symbol
   - Now when user **right-clicks any symbol → Drill Through → Symbol Detail**, they see full info!

> [!TIP]
> **Drill Through** is Power BI's equivalent of "click to see details". Right-click any data point → Drill through → Detail page.

---

### PAGE 4: Trader Risk Profiles

**Add new page** → Rename → `Trader Investigation`

#### Top KPIs:
| Card | Measure/Field |
|---|---|
| Total Traders | `COUNTROWS(pbi_trader_risk_profiles)` |
| HIGH Risk Traders | `[High Risk Traders]` measure |
| FLAGGED Traders | `[Flagged Traders]` measure |
| Avg Trader Risk | `[Avg Trader Risk]` measure |

#### Left: Trader Risk Scatter
1. Add **Scatter Chart**
2. **X-axis**: `fraud_rate_pct`
3. **Y-axis**: `max_risk_score`
4. **Size**: `total_volume_traded`
5. **Color**: `risk_tier`
6. **Details**: `trader_id`

#### Right: Top 10 Riskiest Traders (Horizontal Bar)
1. Add **Bar Chart**
2. **Y-axis**: `trader_id`
3. **X-axis**: `max_risk_score`
4. Apply **TopN filter**: Top 10 by max_risk_score
5. **Conditional formatting**: Data bars Red gradient

#### Bottom: Full Investigation Table
1. Add **Table** visual
2. Columns: trader_id, total_windows, fraud_windows, fraud_rate_pct, avg_risk_score, max_risk_score, total_volume_traded, risk_tier, trader_status
3. **Conditional formatting**:
   - `risk_tier`: Background colors (RED/AMBER/GREEN)
   - `trader_status`: Background colors (RED for FLAGGED, AMBER for WATCH)
   - `max_risk_score`: Data bars
4. Enable **sorting** by clicking column headers

#### Filters:
1. **Slicer**: `risk_tier` → Buttons (ALL, HIGH, MEDIUM, LOW)
2. **Slicer**: `trader_status` → Buttons (ALL, FLAGGED, WATCH, NORMAL)
3. **Slicer**: `max_risk_score` → Numeric range slider

---

### PAGE 5: AI Model Performance

**Add new page** → Rename → `AI Model Performance`

#### Top KPIs:
| Card | Value | Format |
|---|---|---|
| XGBoost Accuracy | 88.2% | Fixed text (Card) |
| ROC-AUC | 0.954 | Fixed text |
| Precision | 77.9% | Fixed text |
| Recall | 86.1% | Fixed text |
| F1 Score | 0.818 | Fixed text |
| Inference Latency | 1.8ms | Fixed text |

> [!NOTE]
> These are static model metrics from training. Create them as **Card** visuals with static text or as a small table.

#### Model Comparison Cards (3 Side by Side):
Create 3 **Card groups** using text boxes + shapes:
- **XGBoost** — 60% weight, 88.2% precision, 0.954 AUC
- **Isolation Forest** — 20% weight, 42.6% precision
- **Autoencoder** — 20% weight, 63.5% precision

#### Bottom: Weekly TPR/FPR Trend (Line Chart)
1. Add **Line Chart**
2. Create a small table in Power BI: **Enter Data** →

| Week | TPR | FPR |
|---|---|---|
| W1 | 86 | 6.4 |
| W2 | 88 | 5.9 |
| W3 | 89 | 5.2 |
| W4 | 90 | 4.7 |
| W5 | 91 | 4.1 |
| W6 | 92 | 3.8 |
| W7 | 93 | 3.4 |
| W8 | 94.8 | 2.9 |

3. **X-axis**: Week, **Y-axis**: TPR (Blue) + FPR (Red)
4. Show both lines with data labels

---

## Step 6: Making Everything Interactive

> [!IMPORTANT]
> This is the KEY section — this is what makes your dashboard interactive!

### Cross-Filtering (Automatic)
By default, Power BI enables **cross-highlighting** — when you click any bar/pie slice/data point, ALL other visuals on the same page filter to show only that selection. This is already interactive!

### Slicers (Filter Controls)
Every page should have slicers at the top:
1. **Date Range Slicer**: Drag `minute_bucket` or `hour_bucket` → Format as "Between"
2. **Symbol Dropdown**: Drag `symbol` → Format as "Dropdown"
3. **Risk Tier Buttons**: Drag `risk_tier` → Format as "List" or "Tile"
4. **Pattern Dropdown**: Drag `fraud_type_predicted` → Format as "Dropdown"

### Sync Slicers Across Pages
To make a filter work across ALL pages:
1. Click the slicer
2. **View** → **Sync slicers** (or Format → Sync slicers)
3. Check the pages you want the slicer to sync with
4. This way, if you select "BTC" on Page 1, it filters BTC data on ALL pages!

### Drill Through (Click for Details)
1. Create a hidden detail page
2. Add a **Drill Through** field (e.g., `symbol` or `trader_id`)
3. Design the detail page with full info for that entity
4. Users can then **right-click** any symbol/trader → **Drill Through** → See full details

### Bookmarks (Pre-Set Views)
1. **View** → **Bookmarks** pane
2. Set filters for "Last 24 Hours + FRAUD only" → Add Bookmark → Name: "Critical Alerts"
3. Set filters for "All Data + All Risk" → Add Bookmark → Name: "Full Overview"
4. Add bookmark buttons to the report for one-click views

---

## Step 7: Visual Formatting Tips (Premium Look)

### Card Formatting:
- Background: White (`#FFFFFF`)
- Border: Light gray (`#E2E8F0`), rounded 12px
- Shadow: ON, Preset: Custom, Offset: 2px, Blur: 8px
- Callout: Inter/Segoe UI, Bold, Size 28-36
- Category: ALL CAPS, Size 10, Gray (`#64748B`)

### Charts:
- Remove chart titles if using text boxes above
- Grid lines: Light gray only horizontal
- Legend: Bottom, Horizontal
- Colors: Use our palette — Blue `#1D63ED`, Red `#DC2626`, Green `#16A34A`, Amber `#D97706`, Teal `#0D9488`

### Page Background:
- Color: Light gray (`#F0F4F8`)
- Transparency: 0%

---

## Step 8: Publish (Optional)

1. **Home** → **Publish** → Select your Power BI Service workspace
2. In Power BI Service: Set up **Scheduled Refresh** every 30 min
3. Share the dashboard link with your team

---

## Troubleshooting

| Problem | Solution |
|---|---|
| CSV columns don't appear | Click **Transform Data**, verify column types (Date, Number, Text) |
| Slicers don't filter charts | Ensure both visual and slicer use same table or have a relationship |
| Drill Through not working | The drill-through field must exist in the source visual's data |
| Charts look plain | Apply the theme file, use conditional formatting on every visual |
| Want real-time data | Switch from CSV to Databricks DirectQuery (Step 1, Option B) |
