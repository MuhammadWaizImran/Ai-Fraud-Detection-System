# 🧠 Complete Feature Engineering Catalog & Data Dictionary
## FINRA AI Real-Time Fraud Detection Platform

Humare poore pipeline mein **Total 28 Features** create hote hain jo **3 Tiers** mein categorized hain:

```text
┌──────────────────────────────────────────────────────────────────────────────────┐
│ TOTAL 28 ENGINEERED FEATURES & METRICS                                           │
├──────────────────────────────────────────────────────────────────────────────────┤
│ 1. TIER 1: Core AI Model Inference Features   (10 Features) ➔ Feeds ML Ensemble │
│ 2. TIER 2: Gold Rolling Window Aggregations   (16 Features) ➔ Feeds Feature Store│
│ 3. TIER 3: Entity Profiling & Risk Badges     (8 Features)  ➔ Feeds Power BI     │
└──────────────────────────────────────────────────────────────────────────────────┘
```

---

## 🎯 TIER 1: 10 Core AI Model Inference Features
Yeh 10 features **XGBoost, Isolation Forest, aur Autoencoder** ko direct feed hote hain real-time prediction (<2ms) ke liye:

| # | Feature Name | Data Type | Formula / Logic | Target Fraud Pattern | SHAP Rank |
|---|---|---|---|---|---|
| **1** | `volume_spike_ratio` | `DOUBLE` | $\text{Vol}_{\text{order}} / \text{AvgVol}_{\text{10m}}$ | **Pump & Dump / Volume Spikes** | 🥇 Rank 1 (42%) |
| **2** | `cancel_to_trade_ratio` | `DOUBLE` | $\text{Cancels}_{\text{trader}} / \text{TotalOrders}_{\text{trader}}$ | **Spoofing / Fake Phantom Bids** | 🥈 Rank 2 (34%) |
| **3** | `orders_per_minute` | `BIGINT` | $\sum \text{Orders in last 60 seconds}$ | **HFT Bot Flood / High Velocity** | 🥉 Rank 3 (26%) |
| **4** | `buy_sell_imbalance` | `DOUBLE` | $\|\text{Buys} - \text{Sells}\| / (\text{Buys} + \text{Sells})$ | **Directional Order Book Skew** | Rank 4 (19%) |
| **5** | `wash_trade_flag` | `DOUBLE` | Cancel $> 0.60$ AND VolumeSpike $> 4.0$ | **Wash Trading / Circular Trades** | Rank 5 (15%) |
| **6** | `layering_flag` | `DOUBLE` | Orders/Min $> 12$ AND Cancel $> 0.50$ | **Multi-Level Order Book Layering** | Rank 6 (12%) |
| **7** | `price_deviation_pct` | `DOUBLE` | $\|\text{Price} - \text{AvgPrice}_{\text{10m}}\| / \text{AvgPrice} \times 100$ | **Price Manipulation / Off-Market** | Rank 7 (8%) |
| **8** | `price_range_pct` | `DOUBLE` | $24\text{h Price Change Volatility \%}$ | **Market Macro Volatility Regime** | Rank 8 (5%) |
| **9** | `volume` | `DOUBLE` | Raw order size in coins | **Absolute Scale Magnitude** | Rank 9 (4%) |
| **10** | `price` | `DOUBLE` | Raw order price in USD | **Absolute Nominal Asset Price** | Rank 10 (3%) |

---

## 🏛️ TIER 2: 16 Gold Rolling Window Aggregations (`gold.trade_features`)
Notebook `03_gold_feature_engineering.py` har 10-minute tumbling window par Spark SQL ke through yeh statistical features calculate karta hai:

| # | Feature Name | Data Type | Description |
|---|---|---|---|
| **11** | `order_count_10m` | `BIGINT` | Total orders in 10-minute window |
| **12** | `total_volume_10m` | `DOUBLE` | Cumulative traded volume in window |
| **13** | `avg_volume_10m` | `DOUBLE` | Average transaction size |
| **14** | `max_volume_10m` | `DOUBLE` | Peak order size in window |
| **15** | `avg_price_10m` | `DOUBLE` | Volume-weighted average price (VWAP) |
| **16** | `stddev_price_10m` | `DOUBLE` | Price standard deviation (Intra-window volatility) |
| **17** | `max_price_10m` | `DOUBLE` | Highest price in 10-minute window |
| **18** | `min_price_10m` | `DOUBLE` | Lowest price in 10-minute window |
| **19** | `buy_count_10m` | `BIGINT` | Total Buy orders in window |
| **20** | `sell_count_10m` | `BIGINT` | Total Sell orders in window |
| **21** | `cancel_count_10m` | `BIGINT` | Total Cancelled orders in window |
| **22** | `executed_count_10m` | `BIGINT` | Total Executed orders in window |
| **23** | `avg_market_cap` | `DOUBLE` | Asset baseline market capitalization |
| **24** | `avg_price_change_24h_pct` | `DOUBLE` | Macro 24-hour price momentum |
| **25** | `window_start` | `TIMESTAMP` | Tumbling window start time |
| **26** | `window_end` | `TIMESTAMP` | Tumbling window end time |

---

## 👤 TIER 3: Entity Profiling & Risk Badges (`gold.pbi_trader_risk_profiles`)
Notebook `06_gold_kpi_aggregations.py` traders aur assets ke historical risk scores compile karta hai:

| # | Feature / Metric | Data Type | Description |
|---|---|---|---|
| **27** | `trader_fraud_rate_pct` | `DOUBLE` | Percentage of windows flagged as fraud per trader |
| **28** | `risk_tier` | `STRING` | Categorical badge: `HIGH`, `MEDIUM`, `LOW` |
| **29** | `trader_status` | `STRING` | Regulatory action status: `FLAGGED`, `WATCH`, `NORMAL` |
| **30** | `max_risk_score` | `DOUBLE` | Peak lifetime AI risk score recorded |
| **31** | `total_volume_traded` | `DOUBLE` | Cumulative lifetime USD volume |
| **32** | `fraud_type_predicted` | `STRING` | Specific attack classification (e.g. `wash_trading`, `spoofing`) |

---

## 🎯 Summary: ML Model vs Feature Store
* **AI Models (XGBoost/Autoencoder)**: Sirf **Top 10 mathematically normalized signals (Tier 1)** lete hain taake prediction latency **`< 2ms`** rahe.
* **Feature Store & Power BI**: Saare **28+ Features (Tiers 1, 2, 3)** store karte hain taake compliance officers poori deep-dive investigation kar saken.
