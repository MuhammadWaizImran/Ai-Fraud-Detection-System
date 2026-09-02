# Real-Time Fraud Detection Platform — Complete Project Documentation

This document is a **complete handoff reference** for the Real-Time Fraud Detection Platform project. It contains the full architecture, all decisions made, all scripts written, current progress, known issues/fixes, and the remaining roadmap. Use this to brief any AI agent or team member so they can continue the project without needing prior context.

---

## 1. Project Overview

A cloud-native, real-time fraud detection system built on **Microsoft Azure** and **Azure Databricks**. It ingests live-ish market/crypto data, streams it through a medallion (Bronze/Silver/Gold) Delta Lake architecture, engineers fraud-relevant features, trains ML models (Isolation Forest, XGBoost, Autoencoder) to detect fraud patterns, deploys the trained model as a real-time scoring endpoint, and surfaces results via alerts and a dashboard.

**Key deviation from a "real" system**: This is a learning/portfolio project. Real stock exchange data (NYSE/NASDAQ/CBOE/Options/Broker Dealers) is **not used** — it has been replaced with:
- **CoinMarketCap API** — for real, live cryptocurrency prices (used as a realistic price baseline)
- **Custom Python simulators** — to generate fake but realistic order-level events (trader IDs, buy/sell orders, order lifecycle) with injected fraud patterns, since no public API provides real order-level trading data (that data is private/confidential to exchanges and brokers).

**Implementation philosophy**: Built manually via the Azure Portal UI (not CLI/Terraform) for hands-on learning. A parallel Terraform project exists but is explicitly a **fallback/reference only** — not used for actual deployment.

---

## 2. Fraud Patterns Being Detected

The project targets 5 well-known market-fraud patterns, plus normal trades as the baseline:

| Pattern | Description | Feature Signal |
|---|---|---|
| **Volume Spike** | A single order's volume is 20–100x the normal average | `volume / rolling_average_volume` ratio |
| **Price Manipulation** | Price jumps/drops 15–30% in one trade with no real market cause | `price_change_percent` vs recent average |
| **Wash Trading** | Same trader buys and sells the same symbol within a short window (round-trip trades to fake volume) | `same_trader_buy_sell_count_in_window` |
| **Spoofing** | A large order is placed then cancelled quickly, never meant to execute | `order_cancel_ratio`, `time_to_cancel` |
| **Layering** | Same trader places many orders (5–10) at different price levels in a short window to mislead the market | `order_count_per_trader_per_minute` |

Ratio used in simulated data: **~85% normal trades, ~15% fraud** (spread across the 5 fraud types) — this mirrors real-world rarity of fraud and avoids overfitting/unrealistic 50-50 splits.

---

## 3. Critical ML Concept: Two Separate Data Paths

This was a major point of clarification during the project and **must be preserved** in any handoff:

### Path A — Model Training (standalone, offline, NOT part of the live pipeline)
- A dedicated script (`generate_training_data.py`) generates **labeled** fake order data (`is_fraud`, `fraud_type` columns included) and writes it to a local CSV.
- This labeled dataset is loaded into Databricks, used for feature engineering, and used to **train** models:
  - **Isolation Forest** (unsupervised — learns what "normal" looks like, flags outliers; needs no labels)
  - **XGBoost** (supervised — learns from the `is_fraud` label directly)
  - **Autoencoder** (unsupervised — reconstruction-error-based anomaly detection)
- Models are evaluated (accuracy, precision, recall, confusion matrix), then registered in **MLflow** and deployed to a **Databricks Model Serving** endpoint.
- **This path has no connection to Event Hub or the live pipeline.** It is a one-time (or as-needed retrain) offline activity.

### Path B — Live/Production Pipeline (the actual running system)
- A second script (`live_order_simulator.py`) fetches **real live prices from CoinMarketCap**, uses them as a realistic baseline, and generates fake order events (same fraud patterns as training) — but **without** `is_fraud`/`fraud_type` labels, exactly like real production data where ground truth is unknown.
- This unlabeled data flows through: Event Hub → Databricks Structured Streaming → Bronze → Silver → Gold Delta tables → Feature Store → the **already-trained** Model Serving endpoint from Path A.
- The model predicts a risk score purely from the features, having never seen the label — this is the actual "fraud detection" moment.

**The two paths connect only at the Model Serving Endpoint**: Path A creates and deploys it; Path B calls it. Order matters — Path A must be completed (model trained + deployed) before Path B's scoring step is meaningful.

---

## 4. Final Architecture — Full Flow Diagram

```
┌──────────────────────────────────────────────────────────────────┐
│                         DATA SOURCES                              │
│   CoinMarketCap API (real crypto prices) + live_order_simulator.py│
└────────────────────────────┬───────────────────────────────────────┘
                             │ Live Order Events (NO fraud label)
                             ▼
┌──────────────────────────────────────────────────────────────────┐
│              PYTHON INGESTION / PRODUCER SERVICE                  │
│                  (live_order_simulator.py)                        │
└────────────────────────────┬───────────────────────────────────────┘
                             │ JSON Event Messages
                             ▼
┌──────────────────────────────────────────────────────────────────┐
│                    AZURE EVENT HUBS (Kafka-compatible)             │
│              (ehns-frauddetect / eh-trade-events)                  │
└────────────────────────────┬───────────────────────────────────────┘
                             ▼
┌──────────────────────────────────────────────────────────────────┐
│         DATABRICKS STRUCTURED STREAMING (Kafka connector)          │
└────────────────────────────┬───────────────────────────────────────┘
                             ▼
┌──────────────────────────────────────────────────────────────────┐
│                 BRONZE DELTA TABLE (raw data)                      │
└────────────────────────────┬───────────────────────────────────────┘
                             ▼
┌──────────────────────────────────────────────────────────────────┐
│    SPARK ETL (cleaning, dedup, schema validation, standardization) │
└────────────────────────────┬───────────────────────────────────────┘
                             ▼
┌──────────────────────────────────────────────────────────────────┐
│              SILVER DELTA TABLE (clean, validated data)            │
└────────────────────────────┬───────────────────────────────────────┘
                             ▼
┌──────────────────────────────────────────────────────────────────┐
│   SPARK FEATURE ENGINEERING (trade velocity, volume ratio,         │
│   cancel-to-trade ratio, price change %, order book imbalance,     │
│   trader order-count/min, same-trader buy-sell count)              │
└────────────────────────────┬───────────────────────────────────────┘
                             ▼
┌──────────────────────────────────────────────────────────────────┐
│                 DATABRICKS FEATURE STORE                           │
└─────────────────────────────┬──────────────────────────────────────┘
                              │ Real-Time Feature Input
                              ▼
                 ┌─────────────────────────────┐
                 │   DATABRICKS MODEL SERVING   │  ◄── model deployed
                 │            API               │      here by Path A
                 └──────────────┬───────────────┘
                                ▼
┌──────────────────────────────────────────────────────────────────┐
│     REAL-TIME FRAUD DETECTION ENGINE (risk score + thresholds)     │
│              Final Decision: Fraud / Suspicious / Safe             │
└───────────────────────┬────────────────────────┬───────────────────┘
              High-Risk / Fraud            All Predictions
                        ▼                        ▼
       ┌─────────────────────────┐   ┌──────────────────────────┐
       │    AZURE LOGIC APPS      │   │ PREDICTION RESULTS DELTA  │
       │  Email / Teams alerts    │   │ TABLE (order id, score,   │
       └──────────────┬───────────┘   │ prediction, model version,│
                      ▼                │ timestamp)                │
       ┌─────────────────────────┐    └─────────────┬──────────────┘
       │     BUSINESS USERS      │                  ▼
       └─────────────────────────┘    ┌──────────────────────────┐
                                       │  SPARK AGGREGATION JOBS   │
                                       └─────────────┬──────────────┘
                                                     ▼
                                       ┌──────────────────────────┐
                                       │     GOLD DELTA TABLE      │
                                       │  (business-ready KPIs)    │
                                       └─────────────┬──────────────┘
                                                     ▼
                                       ┌──────────────────────────┐
                                       │   POWER BI DASHBOARD      │
                                       └──────────────────────────┘
```

### Training Path (Path A — runs separately, before the pipeline above matters)

```
generate_training_data.py (local, labeled data)
        │  is_fraud, fraud_type included
        ▼
   training_data.csv
        ▼
   Databricks: Feature Engineering (on labeled data)
        ▼
   Model Training (Isolation Forest, XGBoost, Autoencoder)
        ▼
   Model Evaluation (accuracy, precision, recall)
        ▼
   MLflow Registry (register + approve best model)
        ▼
   Databricks Model Serving Endpoint (deployed, ready for Path B)
```

---

## 5. Azure Resources — Naming Convention Used

All resources live in a single resource group for easy cleanup.

| Resource Type | Name Used | Purpose |
|---|---|---|
| Resource Group | `rg-fraud-detection` | Container for everything |
| Entra ID App Registration | `fraud-detection-sp` | Service principal identity for automation/CI-CD |
| Key Vault | `kv-frauddetect0X` (unique suffix, e.g. `02`) | Stores all secrets |
| Event Hub Namespace | `ehns-frauddetect` | Kafka-compatible streaming namespace |
| Event Hub | `eh-trade-events` | The actual topic, 4 partitions, 1-day retention |
| Storage Account (ADLS Gen2) | `stfrauddetectlake` | Delta Lake storage, hierarchical namespace enabled |
| Storage Containers | `bronze`, `silver`, `gold`, `checkpoints`, `unity-catalog-metastore` | Medallion layers + streaming checkpoints |
| Access Connector for Databricks | `dbw-access-connector` | Managed identity linking Databricks to storage |
| Databricks Workspace | `dbw-frauddetection` | Premium SKU (required for Unity Catalog + KV-backed secret scopes) |
| Unity Catalog | `fraud_detection_catalog` | With schemas: `bronze`, `silver`, `gold`, `features` |
| Databricks Secret Scope | `fraud-kv-scope` | Key Vault–backed, lets notebooks call `dbutils.secrets.get()` |

### Key Vault Secrets Stored

| Secret Name | Value |
|---|---|
| `sp-client-id` | App Registration Application (client) ID |
| `sp-tenant-id` | Directory (tenant) ID |
| `sp-client-secret` | App Registration client secret value |
| `cmc-api-key` | CoinMarketCap API key |
| `eventhub-conn-string` | Event Hub Namespace primary connection string (RootManageSharedAccessKey) |

### RBAC Role Assignments Made

| Scope | Principal | Role |
|---|---|---|
| Key Vault | Deploying user (self) | Key Vault Administrator |
| Key Vault | `AzureDatabricks` (Microsoft's fixed enterprise app, appid `2ff814a6-3304-4ab8-85cb-cd0e6f879c1d`) | Key Vault Secrets User — **required** for Databricks-backed secret scopes to fetch secrets; without this you get a 403 `PERMISSION_DENIED` error |
| Resource Group | `fraud-detection-sp` | Contributor |
| Storage Account | `dbw-access-connector` | Storage Blob Data Contributor |

---

## 6. Scripts Written So Far

### 6.1 `generate_training_data.py` (Path A — labeled training data generator)

Generates fake orders continuously (no fixed limit — runs until manually stopped with Ctrl+C), 85% normal / 15% fraud across 5 fraud types, all fields including `is_fraud` and `fraud_type`. Writes to `training_data.csv` with `f.flush()` after every batch so no data is lost if interrupted. Every `order_id` uses `uuid.uuid4()` guaranteeing uniqueness.

```python
import csv
import random
import uuid
from datetime import datetime, timedelta, timezone

OUTPUT_FILE = "training_data.csv"
BATCH_PRINT_EVERY = 500

SYMBOLS = {
    "AAPL_SIM": 180.0, "TSLA_SIM": 250.0, "MSFT_SIM": 410.0,
    "GOOGL_SIM": 165.0, "AMZN_SIM": 175.0,
    "BTC_SIM": 65000.0, "ETH_SIM": 3400.0, "SOL_SIM": 145.0,
}
baseline_prices = dict(SYMBOLS)

TRADER_POOL = [f"TRADER_{i:04d}" for i in range(1, 501)]

FIELDNAMES = [
    "order_id", "trader_id", "symbol", "order_type", "order_status",
    "price", "volume", "timestamp", "is_fraud", "fraud_type"
]

def now_iso(offset_seconds=0):
    return (datetime.now(timezone.utc) + timedelta(seconds=offset_seconds)).isoformat()

def drift_price(symbol):
    baseline_prices[symbol] *= (1 + random.uniform(-0.003, 0.003))
    return baseline_prices[symbol]

def gen_normal_trade():
    symbol = random.choice(list(SYMBOLS.keys()))
    price = round(drift_price(symbol), 4)
    volume = round(random.uniform(1, 500), 4)
    return [{
        "order_id": str(uuid.uuid4()), "trader_id": random.choice(TRADER_POOL),
        "symbol": symbol, "order_type": random.choice(["buy", "sell"]),
        "order_status": "executed", "price": price, "volume": volume,
        "timestamp": now_iso(), "is_fraud": False, "fraud_type": "none"
    }]

def gen_volume_spike():
    symbol = random.choice(list(SYMBOLS.keys()))
    price = round(drift_price(symbol), 4)
    volume = round(random.uniform(1, 500) * random.uniform(20, 100), 4)
    return [{
        "order_id": str(uuid.uuid4()), "trader_id": random.choice(TRADER_POOL),
        "symbol": symbol, "order_type": random.choice(["buy", "sell"]),
        "order_status": "executed", "price": price, "volume": volume,
        "timestamp": now_iso(), "is_fraud": True, "fraud_type": "volume_spike"
    }]

def gen_price_manipulation():
    symbol = random.choice(list(SYMBOLS.keys()))
    base = baseline_prices[symbol]
    direction = random.choice([1, -1])
    manipulated_price = round(base * (1 + direction * random.uniform(0.15, 0.30)), 4)
    volume = round(random.uniform(1, 300), 4)
    return [{
        "order_id": str(uuid.uuid4()), "trader_id": random.choice(TRADER_POOL),
        "symbol": symbol, "order_type": random.choice(["buy", "sell"]),
        "order_status": "executed", "price": manipulated_price, "volume": volume,
        "timestamp": now_iso(), "is_fraud": True, "fraud_type": "price_manipulation"
    }]

def gen_wash_trading():
    symbol = random.choice(list(SYMBOLS.keys()))
    trader = random.choice(TRADER_POOL)
    price = round(drift_price(symbol), 4)
    volume = round(random.uniform(5, 200), 4)
    gap = random.uniform(2, 25)
    rows = []
    for i, side in enumerate(["buy", "sell"]):
        rows.append({
            "order_id": str(uuid.uuid4()), "trader_id": trader, "symbol": symbol,
            "order_type": side, "order_status": "executed",
            "price": round(price * (1 + random.uniform(-0.002, 0.002)), 4),
            "volume": volume, "timestamp": now_iso(offset_seconds=i * gap),
            "is_fraud": True, "fraud_type": "wash_trading"
        })
    return rows

def gen_spoofing():
    symbol = random.choice(list(SYMBOLS.keys()))
    price = round(drift_price(symbol), 4)
    volume = round(random.uniform(500, 2000), 4)
    return [{
        "order_id": str(uuid.uuid4()), "trader_id": random.choice(TRADER_POOL),
        "symbol": symbol, "order_type": random.choice(["buy", "sell"]),
        "order_status": "cancelled", "price": price, "volume": volume,
        "timestamp": now_iso(), "is_fraud": True, "fraud_type": "spoofing"
    }]

def gen_layering():
    symbol = random.choice(list(SYMBOLS.keys()))
    trader = random.choice(TRADER_POOL)
    base_price = drift_price(symbol)
    num_orders = random.randint(5, 10)
    rows = []
    for i in range(num_orders):
        price_offset = random.uniform(-0.02, 0.02)
        rows.append({
            "order_id": str(uuid.uuid4()), "trader_id": trader, "symbol": symbol,
            "order_type": random.choice(["buy", "sell"]),
            "order_status": random.choice(["placed", "cancelled"]),
            "price": round(base_price * (1 + price_offset), 4),
            "volume": round(random.uniform(10, 100), 4),
            "timestamp": now_iso(offset_seconds=i * random.uniform(0.5, 2)),
            "is_fraud": True, "fraud_type": "layering"
        })
    return rows

PATTERN_WEIGHTS = [
    (gen_normal_trade, 85), (gen_volume_spike, 3), (gen_price_manipulation, 3),
    (gen_wash_trading, 3), (gen_spoofing, 3), (gen_layering, 3),
]

def pick_generator():
    generators, weights = zip(*PATTERN_WEIGHTS)
    return random.choices(generators, weights=weights, k=1)[0]

def main():
    event_count = 0
    with open(OUTPUT_FILE, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        if f.tell() == 0:
            writer.writeheader()
        print(f"Generating training data -> {OUTPUT_FILE} ... (Ctrl+C to stop)")
        while True:
            generator = pick_generator()
            rows = generator()
            for row in rows:
                writer.writerow(row)
                event_count += 1
            f.flush()
            if event_count % BATCH_PRINT_EVERY < 10:
                print(f"  {event_count} events generated so far...")

if __name__ == "__main__":
    main()
```

### 6.2 `live_order_simulator.py` (Path B — live producer, real prices + unlabeled fake orders)

Fetches real coin data from CoinMarketCap every 30 seconds, generates fake order events anchored to real prices, applies the same 5 fraud patterns (weighted 85% normal / 15% fraud), and **does not include `is_fraud`/`fraud_type`** — this is deliberately "blind" data for live inference. Currently writes to `live_orders.csv`; a `# TODO` marks where Event Hub sending should be added once the pipeline is stable.

```python
import requests, csv, random, time, uuid
from datetime import datetime, timezone

CMC_API_KEY = "PASTE_YOUR_COINMARKETCAP_KEY_HERE"
CMC_URL = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/listings/latest"

OUTPUT_FILE = "live_orders.csv"
FETCH_EVERY_SECONDS = 30
ORDERS_PER_CYCLE = 40

TRADER_POOL = [f"TRADER_{i:04d}" for i in range(1, 501)]

FIELDNAMES = [
    "order_id", "trader_id", "symbol", "coin_name", "order_type",
    "order_status", "price", "volume", "market_cap", "percent_change_24h",
    "timestamp"
]
# NOTE: is_fraud / fraud_type are intentionally absent — this is live/production data.

def fetch_real_coin_data():
    headers = {"X-CMC_PRO_API_KEY": CMC_API_KEY}
    params = {"start": "1", "limit": "20", "convert": "USD"}
    resp = requests.get(CMC_URL, headers=headers, params=params, timeout=10)
    resp.raise_for_status()
    return resp.json()["data"]

def gen_normal_order(coin):
    real_price = coin["quote"]["USD"]["price"]
    price = round(real_price * (1 + random.uniform(-0.002, 0.002)), 4)
    volume = round(random.uniform(1, 500), 4)
    return {
        "order_id": str(uuid.uuid4()), "trader_id": random.choice(TRADER_POOL),
        "symbol": coin["symbol"], "coin_name": coin["name"],
        "order_type": random.choice(["buy", "sell"]), "order_status": "executed",
        "price": price, "volume": volume,
        "market_cap": round(coin["quote"]["USD"]["market_cap"], 2),
        "percent_change_24h": round(coin["quote"]["USD"]["percent_change_24h"], 4),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

def gen_volume_spike_order(coin):
    order = gen_normal_order(coin)
    order["volume"] = round(order["volume"] * random.uniform(20, 100), 4)
    order["order_id"] = str(uuid.uuid4())
    return order

def gen_price_manipulation_order(coin):
    order = gen_normal_order(coin)
    real_price = coin["quote"]["USD"]["price"]
    direction = random.choice([1, -1])
    order["price"] = round(real_price * (1 + direction * random.uniform(0.15, 0.30)), 4)
    order["order_id"] = str(uuid.uuid4())
    return order

def gen_wash_trading_orders(coin):
    trader = random.choice(TRADER_POOL)
    real_price = coin["quote"]["USD"]["price"]
    volume = round(random.uniform(5, 200), 4)
    orders = []
    for side in ["buy", "sell"]:
        orders.append({
            "order_id": str(uuid.uuid4()), "trader_id": trader, "symbol": coin["symbol"],
            "coin_name": coin["name"], "order_type": side, "order_status": "executed",
            "price": round(real_price * (1 + random.uniform(-0.002, 0.002)), 4),
            "volume": volume, "market_cap": round(coin["quote"]["USD"]["market_cap"], 2),
            "percent_change_24h": round(coin["quote"]["USD"]["percent_change_24h"], 4),
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
    return orders

def gen_spoofing_order(coin):
    order = gen_normal_order(coin)
    order["order_id"] = str(uuid.uuid4())
    order["order_status"] = "cancelled"
    order["volume"] = round(order["volume"] * random.uniform(5, 15), 4)
    return order

def gen_layering_orders(coin):
    trader = random.choice(TRADER_POOL)
    real_price = coin["quote"]["USD"]["price"]
    num_orders = random.randint(5, 10)
    orders = []
    for _ in range(num_orders):
        price_offset = random.uniform(-0.02, 0.02)
        orders.append({
            "order_id": str(uuid.uuid4()), "trader_id": trader, "symbol": coin["symbol"],
            "coin_name": coin["name"], "order_type": random.choice(["buy", "sell"]),
            "order_status": random.choice(["placed", "cancelled"]),
            "price": round(real_price * (1 + price_offset), 4),
            "volume": round(random.uniform(10, 100), 4),
            "market_cap": round(coin["quote"]["USD"]["market_cap"], 2),
            "percent_change_24h": round(coin["quote"]["USD"]["percent_change_24h"], 4),
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
    return orders

def generate_orders_for_coin(coin):
    roll = random.random()
    if roll < 0.85: return [gen_normal_order(coin)]
    elif roll < 0.88: return [gen_volume_spike_order(coin)]
    elif roll < 0.91: return [gen_price_manipulation_order(coin)]
    elif roll < 0.94: return gen_wash_trading_orders(coin)
    elif roll < 0.97: return [gen_spoofing_order(coin)]
    else: return gen_layering_orders(coin)

def main():
    with open(OUTPUT_FILE, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        if f.tell() == 0:
            writer.writeheader()
        print("Starting live order simulator... (Ctrl+C to stop)")
        while True:
            try:
                coins = fetch_real_coin_data()
                print(f"Fetched {len(coins)} real coins from CoinMarketCap")
                cycle_orders = []
                for _ in range(ORDERS_PER_CYCLE):
                    coin = random.choice(coins)
                    cycle_orders.extend(generate_orders_for_coin(coin))
                for order in cycle_orders:
                    writer.writerow(order)
                    # TODO: send_to_eventhub(order)  -- add once pipeline is verified
                f.flush()
                print(f"  {len(cycle_orders)} fake orders generated using real coin data")
            except Exception as e:
                print(f"Error: {e} — retrying next cycle")
            time.sleep(FETCH_EVERY_SECONDS)

if __name__ == "__main__":
    main()
```

### 6.3 Bronze Ingestion Notebook (`01_bronze_ingest`, inside Databricks)

Reads from Event Hub via the **Kafka protocol** (not the Maven `azure-eventhubs-spark` connector — see Section 7 for why), writes to the Bronze Delta table.

```python
eventhub_conn_string = dbutils.secrets.get(scope="fraud-kv-scope", key="eventhub-conn-string")

eh_namespace = "ehns-frauddetect"  # actual namespace name
bootstrap_servers = f"{eh_namespace}.servicebus.windows.net:9093"

kafka_options = {
    "kafka.bootstrap.servers": bootstrap_servers,
    "subscribe": "eh-trade-events",
    "kafka.sasl.mechanism": "PLAIN",
    "kafka.security.protocol": "SASL_SSL",
    "kafka.sasl.jaas.config": f'kafkashaded.org.apache.kafka.common.security.plain.PlainLoginModule required username="$ConnectionString" password="{eventhub_conn_string}";',
    "startingOffsets": "earliest"
}

raw_df = spark.readStream.format("kafka").options(**kafka_options).load()
bronze_df = raw_df.selectExpr("CAST(value AS STRING) as json_str", "timestamp as enqueuedTime")

bronze_df.writeStream \
    .format("delta") \
    .option("checkpointLocation", "abfss://checkpoints@stfrauddetectlake.dfs.core.windows.net/bronze") \
    .trigger(availableNow=True) \
    .table("fraud_detection_catalog.bronze.raw_trades")
```

---

## 7. Issues Encountered & Fixes (Important — Avoid Repeating These)

| Issue | Root Cause | Fix |
|---|---|---|
| Key Vault "You are unauthorized to view these contents" | New Key Vaults default to RBAC authorization; creating the vault doesn't grant the creator access | Assign yourself **Key Vault Administrator** role on the vault via Access Control (IAM); wait 2–5 min for propagation |
| `terraform plan` errors on `azurerm_eventhub` about missing `resource_group_name`/`namespace_name` | The installed `azurerm` provider version expects `resource_group_name` + `namespace_name` instead of `namespace_id` | Use `resource_group_name` and `namespace_name` arguments in `azurerm_eventhub`, not `namespace_id` |
| `terraform plan` failing with `ReadOnlyDisabledSubscription` errors on every resource provider | The Azure subscription itself was disabled (free trial/credit exhausted) — nothing to do with Terraform | Created a new Azure account/subscription; verify subscription status is "Active" before doing anything else |
| Databricks notebook: `PERMISSION_DENIED... Caller is not authorized... Action: Microsoft.KeyVault/vaults/secrets/getSecret` | Databricks accesses Key Vault via a **fixed Microsoft enterprise identity** called `AzureDatabricks` (appid `2ff814a6-3304-4ab8-85cb-cd0e6f879c1d`), which had not been granted any Key Vault role | Assign `AzureDatabricks` the **Key Vault Secrets User** role on the Key Vault via Access Control (IAM); wait a few minutes for propagation |
| Databricks Compute page only shows "Serverless" tab; no visible "Create Compute" / classic cluster button | Likely a subscription-level VM quota restriction (common on new/free-trial subscriptions) or a workspace/tier limitation that hides classic all-purpose compute creation | Workaround: use **Serverless compute** instead of classic clusters (see next two rows). To confirm root cause, check `Quotas` blade in Azure Portal → Compute → look for 0-limit VM families in your region |
| `[INFINITE_STREAMING_TRIGGER_NOT_SUPPORTED]` error when starting a streaming write on Serverless compute | Azure Databricks Serverless compute does not support continuous/infinite streaming triggers (e.g. default `ProcessingTime` trigger) — only batch-style triggers | Add `.trigger(availableNow=True)` (or `.trigger(once=True)`) to the `writeStream` call. This processes whatever data is currently available then stops, rather than running forever. To approximate continuous streaming on Serverless, the cell must be re-run periodically (manually, in a loop, or via a scheduled Databricks Job) |
| Maven library install for Event Hub connector (`com.microsoft.azure:azure-eventhubs-spark_2.12:2.3.22`) not usable | Serverless compute does not support installing custom Maven JAR libraries the way classic clusters do | Switched to Azure Event Hub's **built-in Kafka protocol support** instead — Spark's Kafka connector ships with the Databricks Runtime by default, no extra library install needed. Connect using `kafka.bootstrap.servers = "{namespace}.servicebus.windows.net:9093"` with SASL_SSL/PLAIN auth using the Event Hub connection string as the password |

---

## 8. Progress Status (as of this document)

### ✅ Completed
- [x] Azure account + subscription verified active
- [x] Resource Group (`rg-fraud-detection`)
- [x] App Registration + Service Principal (`fraud-detection-sp`) with client secret
- [x] Key Vault (`kv-frauddetect0X`) with RBAC self-access + 5 secrets stored
- [x] RBAC: Service Principal granted Contributor on Resource Group
- [x] CoinMarketCap API account + key
- [x] `generate_training_data.py` written and runnable (generates labeled data continuously)
- [x] `live_order_simulator.py` written (fetches real CoinMarketCap prices, generates unlabeled fake orders) — **not yet sending to Event Hub, currently writes to local CSV only**
- [x] Event Hub Namespace (`ehns-frauddetect`, Standard tier) + Event Hub (`eh-trade-events`, 4 partitions)
- [x] Event Hub connection string stored in Key Vault
- [x] ADLS Gen2 Storage Account (`stfrauddetectlake`) with hierarchical namespace enabled
- [x] Storage containers: `bronze`, `silver`, `gold`, `checkpoints`, `unity-catalog-metastore`
- [x] Access Connector for Databricks (`dbw-access-connector`) + Storage Blob Data Contributor role
- [x] Azure Databricks Workspace (`dbw-frauddetection`, Premium SKU)
- [x] Unity Catalog auto-provisioned; `fraud_detection_catalog` created with `bronze`/`silver`/`gold`/`features` schemas
- [x] Key Vault-backed secret scope (`fraud-kv-scope`) created and **verified working** (`AzureDatabricks` identity granted Key Vault Secrets User role)
- [x] Bronze ingestion notebook (`01_bronze_ingest`) written, using Kafka protocol + `trigger(availableNow=True)` — using **Serverless compute** (classic cluster creation not available on this subscription)

### 🔄 In Progress / Next Steps
- [ ] Run/verify `01_bronze_ingest` notebook actually lands data once `live_order_simulator.py` is sending events (currently the simulator only writes local CSV, hasn't been wired to Event Hub yet)
- [ ] Wire `live_order_simulator.py` to send events to Event Hub (add `azure-eventhub` Python SDK send logic, using the connection string from Key Vault)
- [ ] Silver layer notebook (cleaning, dedup, schema validation) — **remember**: on Serverless compute, use `.trigger(availableNow=True)` and re-run periodically, not a single infinite streaming cell
- [ ] Gold layer notebook (windowed aggregations)
- [ ] Feature Engineering notebook using Databricks Feature Engineering Client, writing to `fraud_detection_catalog.features.*`
- [ ] **Path A**: Load `training_data.csv` into Databricks, engineer the same features, train Isolation Forest + XGBoost + Autoencoder, evaluate, register best model(s) in MLflow
- [ ] Deploy trained model to Databricks Model Serving endpoint
- [ ] Fraud scoring notebook: call the serving endpoint on Gold-layer features, write results (with risk_score) to a `gold.fraud_alerts` Delta table
- [ ] Power BI dashboard connected to `gold.fraud_alerts` / aggregated Gold tables
- [ ] Azure Logic App for email/Teams alerting on high-risk predictions
- [ ] Monitoring: Log Analytics workspace + diagnostic settings on Event Hub, Storage, Databricks, Key Vault; Databricks Lakehouse Monitoring on key tables
- [ ] CI/CD: GitHub repo + GitHub Actions workflow to deploy notebooks via Databricks CLI

### 📦 Also Available (Fallback, Not Used for Deployment)
- A complete Terraform project mirroring this architecture (Resource Group, Security, Event Hub, Storage, Databricks workspace shell, monitoring, plus an optional second-phase file for cluster/catalog/secret scope) exists as a reference/disaster-recovery option. It is intentionally **not** the deployment method being used — everything above was built manually via the Azure Portal UI.

---

## 9. Design Decisions & Rationale (Preserve These When Continuing)

1. **Manual Portal UI over CLI/Terraform for deployment** — explicit choice for hands-on learning. Terraform exists only as a fallback reference.
2. **CoinMarketCap + Python simulators instead of NYSE/NASDAQ/CBOE** — no free/legitimate API provides real order-level trade data (broker/exchange-confidential); CoinMarketCap's public market data provides a realistic price anchor, and Python generates the order-level, trader-level, and fraud-pattern detail needed for supervised + unsupervised model training.
3. **Two-script data separation (training vs. live)** — critical to avoid label leakage / an unrealistic setup. `generate_training_data.py` is the only place `is_fraud`/`fraud_type` should ever appear. `live_order_simulator.py` (and anything downstream of it in the live pipeline) must never include those columns — the model must predict them blind, exactly as it would with real unlabeled production data.
4. **Isolation Forest AND XGBoost (not just one)** — Isolation Forest needs no labels and can catch previously-unseen anomaly patterns; XGBoost uses the labels we do have (because we control the simulation) for higher-precision detection of the known fraud types. Using both demonstrates both unsupervised and supervised approaches.
5. **Single Resource Group** — everything lives in `rg-fraud-detection` so the whole project can be torn down with one resource-group deletion when not in use (cost control).
6. **Serverless compute adopted out of necessity, not preference** — classic all-purpose compute creation was unavailable on this subscription (likely a VM quota restriction). If continuing on a subscription where classic clusters ARE available, prefer them for streaming workloads (they support continuous triggers and Maven library installs, which Serverless does not) — but if not available, the Serverless + Kafka-protocol + `availableNow` trigger workaround documented in Section 7 is a valid substitute.

---

## 10. Instructions For The Next Agent / Contributor

If you are picking this project up:

1. Read Sections 3 and 9 first — they explain the *why* behind the architecture, not just the *what*. Do not merge the two data paths (training vs. live) — this was a deliberate, carefully-discussed design choice.
2. Check Section 8 for exact current progress — don't recreate resources that already exist (see Section 5 for their names).
3. Check Section 7 before debugging — several non-obvious Azure/Databricks issues have already been hit and solved; re-reading it will save time.
4. Continue from the "In Progress / Next Steps" checklist in Section 8, in order.
5. If asked to use Terraform for deployment: **don't**, unless the user explicitly changes this instruction. Terraform in this project is fallback/reference only (see the separate Terraform repo).
6. Preserve the "manual UI, one step at a time, confirm before proceeding" working style unless the user asks to move faster.
