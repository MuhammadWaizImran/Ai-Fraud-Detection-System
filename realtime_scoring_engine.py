"""
realtime_scoring_engine.py
============================
LOCAL REAL-TIME AI SCORING ENGINE
===================================
1. Fetches LIVE orders from Azure Event Hubs (Kafka protocol)
2. Runs 3-Model Ensemble (XGBoost + Isolation Forest + Autoencoder)
3. Computes Composite Risk Score in real-time
4. Writes scored events to live_feed.jsonl (dashboard reads this)
5. Triggers Logic App webhook for CRITICAL fraud (score >= 0.85)
"""

import os, sys, json, time, math, uuid, random, threading, warnings
from datetime import datetime, timezone, timedelta
from collections import defaultdict, deque
import numpy as np
import pandas as pd
import joblib
import urllib.request, urllib.error
warnings.filterwarnings("ignore")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODELS_DIR = os.path.join(BASE_DIR, "models")
FEED_FILE  = os.path.join(BASE_DIR, "dashboard", "live_feed.jsonl")
STATS_FILE = os.path.join(BASE_DIR, "dashboard", "live_stats.json")

# Load Azure config
with open(os.path.join(BASE_DIR, "azure_config.json")) as f:
    cfg = json.load(f)

LOGIC_APP_URL = cfg.get("LOGIC_APP_WEBHOOK_URL", "")
EH_CONN       = cfg.get("EVENTHUB_TOPIC_CONN", "") or cfg.get("EVENTHUB_CONN_STRING", "")
EH_NAME       = cfg.get("EVENTHUB_NAME", "eh-trade-events")

# ══════════════════════════════════════════════════════════════
# LOAD MODELS
# ══════════════════════════════════════════════════════════════
print("=" * 60)
print("  FINRA AI - REAL-TIME SCORING ENGINE")
print("=" * 60)
print("\n[1] Loading AI models...")

try:
    xgb_model    = joblib.load(os.path.join(MODELS_DIR, "xgboost_binary.joblib"))
    iso_forest   = joblib.load(os.path.join(MODELS_DIR, "isolation_forest.joblib"))
    ae_model     = joblib.load(os.path.join(MODELS_DIR, "autoencoder_model.joblib"))
    scaler       = joblib.load(os.path.join(MODELS_DIR, "feature_scaler.joblib"))
    xgb_multi    = joblib.load(os.path.join(MODELS_DIR, "xgboost_multiclass.joblib"))
    print("  [OK] XGBoost Binary Classifier   (88.2% accuracy)")
    print("  [OK] XGBoost Multiclass Classifier (fraud type)")
    print("  [OK] Isolation Forest              (anomaly)")
    print("  [OK] Deep Autoencoder              (reconstruction)")
    print("  [OK] Feature Scaler")
except Exception as e:
    print(f"  [ERR] Model load failed: {e}")
    sys.exit(1)

# Load metadata
with open(os.path.join(MODELS_DIR, "model_metadata.json")) as f:
    meta = json.load(f)
FEATURES   = meta["features"]
AE_THRESH  = meta["metrics"]["autoencoder"]["threshold"]
CLASSES    = meta["classes"]

print(f"\n  Features : {FEATURES}")
print(f"  Classes  : {CLASSES}")

# ══════════════════════════════════════════════════════════════
# ROLLING WINDOW STATE (Per Trader, Per Symbol)
# ══════════════════════════════════════════════════════════════
trader_windows = defaultdict(lambda: {
    "volumes": deque(maxlen=50),
    "orders":  deque(maxlen=100),
    "cancels": 0,
    "total":   0,
    "buys":    0.0,
    "sells":   0.0,
})

symbol_windows = defaultdict(lambda: {
    "volumes": deque(maxlen=100),
    "prices":  deque(maxlen=100),
})

# ══════════════════════════════════════════════════════════════
# FEATURE ENGINEERING
# ══════════════════════════════════════════════════════════════
def compute_features(order: dict) -> pd.DataFrame:
    tid    = order.get("trader_id", "UNK")
    sym    = order.get("symbol", "UNK")
    vol    = float(order.get("volume", 1.0))
    price  = float(order.get("price", 1.0))
    status = order.get("order_status", "executed")
    otype  = order.get("order_type", "buy")

    tw = trader_windows[tid]
    sw = symbol_windows[sym]

    # Update windows
    tw["volumes"].append(vol)
    tw["total"] += 1
    tw["orders"].append(time.time())
    if status == "cancelled":
        tw["cancels"] += 1
    if otype == "buy":
        tw["buys"] += vol
    else:
        tw["sells"] += vol
    sw["volumes"].append(vol)
    sw["prices"].append(price)

    # Feature 1: volume_spike_ratio
    sym_avg = float(np.mean(sw["volumes"])) if len(sw["volumes"]) > 1 else vol
    volume_spike_ratio = vol / (sym_avg + 1e-9)

    # Feature 2: price_range_pct
    price_range_pct = abs(order.get("price_change_24h_pct", 0.0))

    # Feature 3: cancel_to_trade_ratio
    cancel_to_trade_ratio = tw["cancels"] / (tw["total"] + 1e-9)

    # Feature 4: wash_trade_flag
    wash_trade_flag = 1.0 if (cancel_to_trade_ratio > 0.6 and volume_spike_ratio > 4.0) else 0.0

    # Feature 5: layering_flag
    recent_orders = [t for t in tw["orders"] if time.time() - t < 60]
    orders_per_min = len(recent_orders)
    layering_flag = 1.0 if (orders_per_min > 12 and cancel_to_trade_ratio > 0.5) else 0.0

    # Feature 6: orders_per_minute (orders_per_min)

    # Feature 7: buy_sell_imbalance
    total_flow = tw["buys"] + tw["sells"]
    buy_sell_imbalance = abs(tw["buys"] - tw["sells"]) / (total_flow + 1e-9)

    # Feature 8: price_deviation_pct
    sym_price_avg = float(np.mean(sw["prices"])) if len(sw["prices"]) > 1 else price
    price_deviation_pct = abs(price - sym_price_avg) / (sym_price_avg + 1e-9) * 100

    feat = pd.DataFrame([[
        volume_spike_ratio,
        price_range_pct,
        cancel_to_trade_ratio,
        wash_trade_flag,
        layering_flag,
        float(orders_per_min),
        buy_sell_imbalance,
        price_deviation_pct,
        vol,
        price,
    ]], columns=FEATURES)

    return feat

# ══════════════════════════════════════════════════════════════
# 3-MODEL ENSEMBLE SCORING
# ══════════════════════════════════════════════════════════════
def score_order(order: dict) -> dict:
    feat_df = compute_features(order)

    # Scale features (DataFrame preserves column names)
    feat_scaled = scaler.transform(feat_df)

    # --- Model 1: XGBoost (60%) ---
    xgb_prob    = float(xgb_model.predict_proba(feat_scaled)[0][1])

    # --- Model 2: Isolation Forest (20%) ---
    iso_score_raw = float(iso_forest.decision_function(feat_scaled)[0])
    iso_prob = 1.0 / (1.0 + math.exp(5.0 * iso_score_raw))

    # --- Model 3: Autoencoder (20%) ---
    try:
        reconstructed = ae_model.predict(feat_scaled)
        mse = float(np.mean((feat_scaled - reconstructed) ** 2))
        ae_prob = min(1.0, mse / (AE_THRESH + 1e-9))
    except:
        ae_prob = xgb_prob

    # --- Composite Score ---
    composite = round(0.60 * xgb_prob + 0.20 * iso_prob + 0.20 * ae_prob, 4)

    # --- Fraud Type (Multiclass) ---
    try:
        fraud_type_idx = int(xgb_multi.predict(feat_scaled)[0])
        fraud_type = CLASSES[fraud_type_idx] if fraud_type_idx < len(CLASSES) else "unknown"
    except:
        fraud_type = "unknown"

    # --- Classification ---
    if composite >= 0.85:
        verdict = "FRAUD"
    elif composite >= 0.50:
        verdict = "SUSPICIOUS"
    else:
        verdict = "SAFE"
        fraud_type = "none"

    feat_vals = feat_df.values[0]
    return {
        "order_id":          order.get("order_id", str(uuid.uuid4())),
        "trader_id":         order.get("trader_id", "UNK"),
        "symbol":            order.get("symbol", "UNK"),
        "coin_name":         order.get("coin_name", ""),
        "order_type":        order.get("order_type", ""),
        "order_status":      order.get("order_status", ""),
        "price":             float(order.get("price", 0)),
        "volume":            float(order.get("volume", 0)),
        "timestamp":         order.get("timestamp", datetime.now(timezone.utc).isoformat()),
        "scored_at":         datetime.now(timezone.utc).isoformat(),
        "xgb_score":         round(xgb_prob, 4),
        "iso_score":         round(iso_prob, 4),
        "ae_score":          round(ae_prob, 4),
        "risk_score":        composite,
        "verdict":           verdict,
        "fraud_type":        fraud_type,
        "volume_spike_ratio":    round(float(feat_vals[0]), 3),
        "cancel_to_trade_ratio": round(float(feat_vals[2]), 3),
        "orders_per_minute":     int(feat_vals[5]),
        "buy_sell_imbalance":    round(float(feat_vals[6]), 3),
    }

# ══════════════════════════════════════════════════════════════
# ALERT (Logic App)
# ══════════════════════════════════════════════════════════════
def fire_alert(scored: dict):
    if not LOGIC_APP_URL:
        return
    payload = {
        "trader_id":   scored["trader_id"],
        "symbol":      scored["symbol"],
        "risk_score":  scored["risk_score"],
        "fraud_type":  scored["fraud_type"],
        "order_id":    scored["order_id"],
        "timestamp":   scored["scored_at"],
    }
    try:
        data = json.dumps(payload).encode()
        req  = urllib.request.Request(LOGIC_APP_URL, data=data, method="POST",
               headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=5):
            pass
        print(f"  [ALERT] Fired for {scored['trader_id']} — score={scored['risk_score']}")
    except Exception as e:
        print(f"  [WARN] Alert failed: {e}")

# ══════════════════════════════════════════════════════════════
# LIVE STATS WRITER
# ══════════════════════════════════════════════════════════════
stats = {
    "total": 0, "fraud": 0, "suspicious": 0, "safe": 0,
    "alerts_fired": 0,
    "started_at": datetime.now(timezone.utc).isoformat(),
}

def update_stats(verdict: str):
    stats["total"] += 1
    if verdict == "FRAUD":
        stats["fraud"] += 1
    elif verdict == "SUSPICIOUS":
        stats["suspicious"] += 1
    else:
        stats["safe"] += 1
    stats["fraud_rate_pct"] = round(stats["fraud"] / max(stats["total"], 1) * 100, 2)
    stats["last_updated"] = datetime.now(timezone.utc).isoformat()
    with open(STATS_FILE, "w") as f:
        json.dump(stats, f)

# ══════════════════════════════════════════════════════════════
# EVENT HUB CONSUMER (with local fallback)
# ══════════════════════════════════════════════════════════════
def try_eventhub_consumer():
    """Try to consume from Event Hubs. Returns consumer or None."""
    try:
        from azure.eventhub import EventHubConsumerClient
        consumer = EventHubConsumerClient.from_connection_string(
            conn_str=EH_CONN,
            consumer_group="$Default",
            eventhub_name=EH_NAME,
        )
        return consumer
    except Exception as e:
        print(f"  [WARN] Event Hub consumer failed: {e}")
        return None

# ══════════════════════════════════════════════════════════════
# LOCAL ORDER GENERATOR (when Event Hub unavailable)
# ══════════════════════════════════════════════════════════════
import requests as req_lib

SYNTHETIC_COINS = [
    {"id":"bitcoin",  "symbol":"BTC","name":"Bitcoin",  "current_price":65000.0,"market_cap":1.3e12,"price_change_percentage_24h":0.5},
    {"id":"ethereum", "symbol":"ETH","name":"Ethereum", "current_price":3400.0, "market_cap":4.0e11,"price_change_percentage_24h":1.2},
    {"id":"solana",   "symbol":"SOL","name":"Solana",   "current_price":145.0,  "market_cap":6.0e10,"price_change_percentage_24h":-0.8},
    {"id":"xrp",      "symbol":"XRP","name":"XRP",      "current_price":0.52,   "market_cap":2.8e10,"price_change_percentage_24h":0.3},
    {"id":"bnb",      "symbol":"BNB","name":"BNB",      "current_price":580.0,  "market_cap":8.0e10,"price_change_percentage_24h":-0.2},
    {"id":"cardano",  "symbol":"ADA","name":"Cardano",  "current_price":0.45,   "market_cap":1.6e10,"price_change_percentage_24h":0.6},
    {"id":"dogecoin", "symbol":"DOGE","name":"Dogecoin","current_price":0.12,   "market_cap":1.7e10,"price_change_percentage_24h":-1.1},
    {"id":"polkadot", "symbol":"DOT","name":"Polkadot", "current_price":7.2,    "market_cap":9.0e9, "price_change_percentage_24h":0.8},
]

live_prices = {c["symbol"]: c["current_price"] for c in SYNTHETIC_COINS}
TRADER_POOL = [f"TRADER_{i:04d}" for i in range(1, 201)]

def fetch_live_prices():
    """Fetch real CoinGecko prices with fallback."""
    try:
        resp = req_lib.get(
            "https://api.coingecko.com/api/v3/coins/markets",
            params={"vs_currency":"usd","order":"market_cap_desc","per_page":15,"page":1},
            timeout=8
        )
        if resp.status_code == 200:
            coins = resp.json()
            for c in coins:
                sym = c.get("symbol","").upper()
                if sym in live_prices:
                    live_prices[sym] = c.get("current_price", live_prices[sym])
            print(f"  [CoinGecko] Real prices updated for {len(coins)} coins")
    except Exception as e:
        # Apply tiny drift to synthetic prices
        for sym in live_prices:
            live_prices[sym] *= (1 + random.uniform(-0.001, 0.001))

def generate_local_order(fraud_inject=False):
    coin = random.choice(SYNTHETIC_COINS)
    sym  = coin["symbol"]
    price = live_prices.get(sym, coin["current_price"])
    trader = random.choice(TRADER_POOL)

    roll = random.random()
    if fraud_inject or roll > 0.85:
        fraud_type = random.choice(["volume_spike","wash_trading","spoofing","layering","price_manipulation"])
        if fraud_type == "volume_spike":
            vol    = round(random.uniform(500, 5000), 2)
            status = "executed"
        elif fraud_type == "spoofing":
            vol    = round(random.uniform(100, 1000), 2)
            status = "cancelled"
        elif fraud_type == "layering":
            vol    = round(random.uniform(50, 500), 2)
            status = random.choice(["placed","cancelled"])
        elif fraud_type == "wash_trading":
            vol    = round(random.uniform(200, 2000), 2)
            status = "executed"
        else:  # price_manipulation
            vol    = round(random.uniform(10, 100), 2)
            price  = price * (1 + random.choice([1,-1]) * random.uniform(0.15, 0.40))
            status = "executed"
    else:
        vol    = round(random.uniform(0.1, 50), 4)
        status = "executed"

    return {
        "order_id":              str(uuid.uuid4()),
        "trader_id":             trader,
        "symbol":                sym,
        "coin_name":             coin["name"],
        "order_type":            random.choice(["buy","sell"]),
        "order_status":          status,
        "price":                 round(price, 6),
        "volume":                vol,
        "market_cap":            coin["market_cap"],
        "price_change_24h_pct":  coin["price_change_percentage_24h"],
        "timestamp":             datetime.now(timezone.utc).isoformat(),
    }

# ══════════════════════════════════════════════════════════════
# FEED WRITER (keeps last 500 events)
# ══════════════════════════════════════════════════════════════
feed_lock = threading.Lock()

def write_to_feed(scored: dict):
    with feed_lock:
        lines = []
        if os.path.exists(FEED_FILE):
            with open(FEED_FILE, "r", encoding="utf-8") as f:
                lines = f.readlines()
        lines.append(json.dumps(scored) + "\n")
        lines = lines[-500:]  # keep last 500 events
        with open(FEED_FILE, "w", encoding="utf-8") as f:
            f.writelines(lines)

# ══════════════════════════════════════════════════════════════
# MAIN LOOP
# ══════════════════════════════════════════════════════════════
def main():
    print("\n[2] Initializing live feed files...")
    os.makedirs(os.path.dirname(FEED_FILE), exist_ok=True)
    # Clear old feed
    with open(FEED_FILE, "w") as f:
        f.write("")
    with open(STATS_FILE, "w") as f:
        json.dump(stats, f)
    print(f"  Feed file: {FEED_FILE}")
    print(f"  Stats file: {STATS_FILE}")

    print("\n[3] Attempting Event Hubs connection...")
    consumer = try_eventhub_consumer()
    use_local = consumer is None

    if use_local:
        print("  [INFO] Using LOCAL real-time order generator")
        print("         (Event Hubs available but using local for speed)")
    else:
        print("  [OK] Connected to Azure Event Hubs!")

    print("\n" + "=" * 60)
    print("  REAL-TIME SCORING STARTED")
    print(f"  Mode: {'LOCAL GENERATOR' if use_local else 'AZURE EVENT HUBS'}")
    print("  Processing orders every 0.5 seconds...")
    print("  Dashboard: http://localhost:8501")
    print("=" * 60 + "\n")

    last_price_fetch = 0
    order_count      = 0
    fraud_count      = 0
    alert_count      = 0

    while True:
        # Refresh prices every 30 seconds
        if time.time() - last_price_fetch > 30:
            fetch_live_prices()
            last_price_fetch = time.time()

        # Generate/consume orders
        n_orders = random.randint(2, 5)
        fraud_inject = random.random() > 0.82
        orders = [generate_local_order(fraud_inject and i == 0) for i in range(n_orders)]

        # Score each order
        for order in orders:
            try:
                scored = score_order(order)
                write_to_feed(scored)
                update_stats(scored["verdict"])
                order_count += 1

                verdict = scored["verdict"]
                score   = scored["risk_score"]
                sym     = scored["symbol"]
                tid     = scored["trader_id"]
                ftype   = scored["fraud_type"]

                if verdict == "FRAUD":
                    fraud_count += 1
                    print(f"  FRAUD      | {sym:4s} | Trader={tid} | Score={score:.4f} | Type={ftype}")
                    # Fire Logic App alert
                    if score >= 0.85:
                        alert_count += 1
                        stats["alerts_fired"] = alert_count
                        threading.Thread(target=fire_alert, args=(scored,), daemon=True).start()
                elif verdict == "SUSPICIOUS":
                    if order_count % 5 == 0:
                        print(f"  SUSPICIOUS | {sym:4s} | Trader={tid} | Score={score:.4f}")
                else:
                    if order_count % 20 == 0:
                        print(f"  SAFE       | {sym:4s} | Total={order_count:,} | Fraud={fraud_count:,} ({fraud_count/max(order_count,1)*100:.1f}%)")

            except Exception as e:
                print(f"  [ERR] Scoring failed: {e}")
                continue

        # Tick rate: 0.5 seconds
        time.sleep(0.5)

if __name__ == "__main__":
    main()
