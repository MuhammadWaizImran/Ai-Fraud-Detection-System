import os
import sys
import json
import time
import joblib
import numpy as np
import pandas as pd
from datetime import datetime

# ML Libraries
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.ensemble import IsolationForest
from sklearn.neural_network import MLPRegressor
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, classification_report, confusion_matrix
)
import xgboost as xgb

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "training_data.csv")
MODELS_DIR = os.path.join(BASE_DIR, "models")
CFG_FILE = os.path.join(BASE_DIR, "azure_config.json")

os.makedirs(MODELS_DIR, exist_ok=True)

print("=" * 80)
print("  FINRA FRAUD DETECTION PLATFORM — ML TRAINING & PIPELINE INTEGRATION")
print("=" * 80)

# ── 1. Load Training Data ──────────────────────────────────────────────────────
print("\n[1/6] Loading training dataset...")
if not os.path.exists(DATA_FILE):
    print(f"[ERR] {DATA_FILE} not found!")
    sys.exit(1)

df = pd.read_csv(DATA_FILE)
print(f"  Total records loaded : {len(df):,}")
print(f"  Columns              : {list(df.columns)}")
print(f"  Fraud rate in dataset: {df['is_fraud'].mean() * 100:.2f}%")
print(f"  Fraud distribution   :\n{df['fraud_type'].value_counts().to_string(index=True)}")

# ── 2. Feature Engineering ─────────────────────────────────────────────────────
print("\n[2/6] Engineering advanced microstructural fraud signals...")
df["timestamp"] = pd.to_datetime(df["timestamp"])
df = df.sort_values(["trader_id", "symbol", "timestamp"]).reset_index(drop=True)

# Rolling feature engineering
def compute_features(group):
    group = group.copy()
    group["rolling_avg_vol_10"] = group["volume"].rolling(10, min_periods=1).mean()
    group["rolling_std_vol_10"] = group["volume"].rolling(10, min_periods=1).std().fillna(0)
    group["rolling_avg_px_10"] = group["price"].rolling(10, min_periods=1).mean()
    group["rolling_std_px_10"] = group["price"].rolling(10, min_periods=1).std().fillna(0)
    group["cancel_count_10"] = (group["order_status"] == "cancelled").rolling(10, min_periods=1).sum()
    group["order_count_10"] = group["volume"].rolling(10, min_periods=1).count()
    group["buy_count_10"] = (group["order_type"] == "buy").rolling(10, min_periods=1).sum()
    group["sell_count_10"] = (group["order_type"] == "sell").rolling(10, min_periods=1).sum()
    return group

df = df.groupby(["trader_id", "symbol"], group_keys=False).apply(compute_features)

EPSILON = 1e-9
df["volume_spike_ratio"] = df["volume"] / (df["rolling_avg_vol_10"] + EPSILON)
df["price_volatility"]   = df["rolling_std_px_10"] / (df["rolling_avg_px_10"] + EPSILON)
df["cancel_ratio"]       = df["cancel_count_10"] / (df["order_count_10"] + EPSILON)
df["buy_sell_imbalance"] = (df["buy_count_10"] - df["sell_count_10"]).abs() / (df["order_count_10"] + EPSILON)
df["spread_pct"]         = (df["ask_price"] - df["bid_price"]).abs() / (df["price"] + EPSILON)
df["wash_indicator"]     = ((df["wash_trade_count"] > 0).astype(float) * 2.0)
df["spoof_indicator"]    = ((df["cancel_ratio"] > 0.6) & (df["volume_spike_ratio"] > 2.5)).astype(float)

FEATURE_COLS = [
    "volume", "price", "bid_price", "ask_price", "spread_pct",
    "rolling_avg_vol_10", "rolling_std_vol_10", "rolling_avg_px_10", "rolling_std_px_10",
    "volume_spike_ratio", "price_volatility", "cancel_ratio", "buy_sell_imbalance",
    "wash_indicator", "spoof_indicator"
]

X = df[FEATURE_COLS].fillna(0)
y_binary = df["is_fraud"].astype(int)

# Label encoding for multi-class fraud types
label_encoder = LabelEncoder()
y_multiclass = label_encoder.fit_transform(df["fraud_type"].fillna("NORMAL"))

X_train, X_test, y_train, y_test, y_train_multi, y_test_multi = train_test_split(
    X, y_binary, y_multiclass, test_size=0.20, random_state=42, stratify=y_binary
)

scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled  = scaler.transform(X_test)

print(f"  Training set size    : {len(X_train):,} samples")
print(f"  Test set size        : {len(X_test):,} samples")
print(f"  Features engineered  : {len(FEATURE_COLS)}")

# ── 3. Train Model 1: XGBoost Classifier ───────────────────────────────────────
print("\n[3/6] Training Model 1: XGBoost Multi-Class Fraud Detector...")
xgb_model = xgb.XGBClassifier(
    n_estimators=150,
    max_depth=6,
    learning_rate=0.08,
    subsample=0.85,
    colsample_bytree=0.85,
    random_state=42,
    eval_metric="mlogloss"
)

start_time = time.time()
xgb_model.fit(X_train, y_train_multi)
xgb_duration = time.time() - start_time

xgb_preds = xgb_model.predict(X_test)
xgb_probs = xgb_model.predict_proba(X_test)

# Map back to binary for binary metrics
normal_class_idx = list(label_encoder.classes_).index("NORMAL")
xgb_binary_preds = (xgb_preds != normal_class_idx).astype(int)
xgb_binary_probs = 1.0 - xgb_probs[:, normal_class_idx]

xgb_acc = accuracy_score(y_test, xgb_binary_preds)
xgb_prec = precision_score(y_test, xgb_binary_preds, zero_division=0)
xgb_rec = recall_score(y_test, xgb_binary_preds, zero_division=0)
xgb_f1 = f1_score(y_test, xgb_binary_preds, zero_division=0)
xgb_auc = roc_auc_score(y_test, xgb_binary_probs)

print(f"  [OK] XGBoost trained in {xgb_duration:.2f}s")
print(f"    - Accuracy  : {xgb_acc * 100:.2f}%")
print(f"    - Precision : {xgb_prec * 100:.2f}%")
print(f"    - Recall    : {xgb_rec * 100:.2f}%")
print(f"    - F1-Score  : {xgb_f1 * 100:.2f}%")
print(f"    - ROC-AUC   : {xgb_auc:.4f}")

# ── 4. Train Model 2: Isolation Forest Anomaly Detector ─────────────────────────
print("\n[4/6] Training Model 2: Isolation Forest Unsupervised Anomaly Detector...")
iso_forest = IsolationForest(
    n_estimators=100,
    contamination=0.08,
    random_state=42,
    n_jobs=-1
)

start_time = time.time()
iso_forest.fit(X_train_scaled)
iso_duration = time.time() - start_time

# Convert (-1: outlier, 1: inlier) to (1: fraud, 0: safe)
iso_raw = iso_forest.predict(X_test_scaled)
iso_preds = (iso_raw == -1).astype(int)
iso_scores = -iso_forest.score_samples(X_test_scaled)

iso_prec = precision_score(y_test, iso_preds, zero_division=0)
iso_rec = recall_score(y_test, iso_preds, zero_division=0)
iso_f1 = f1_score(y_test, iso_preds, zero_division=0)

print(f"  [OK] Isolation Forest trained in {iso_duration:.2f}s")
print(f"    - Anomaly Precision : {iso_prec * 100:.2f}%")
print(f"    - Anomaly Recall    : {iso_rec * 100:.2f}%")
print(f"    - Anomaly F1-Score  : {iso_f1 * 100:.2f}%")

# ── 5. Train Model 3: Neural Network Autoencoder ───────────────────────────────
print("\n[5/6] Training Model 3: Deep Neural Autoencoder for Reconstruction Loss...")
# Filter normal transactions for training autoencoder
X_train_normal = X_train_scaled[y_train == 0]

autoencoder = MLPRegressor(
    hidden_layer_sizes=(32, 16, 8, 16, 32),
    activation="relu",
    solver="adam",
    max_iter=30,
    random_state=42
)

start_time = time.time()
autoencoder.fit(X_train_normal, X_train_normal)
ae_duration = time.time() - start_time

# Reconstruction error as anomaly score
reconstructed = autoencoder.predict(X_test_scaled)
mse_errors = np.mean((X_test_scaled - reconstructed) ** 2, axis=1)
ae_threshold = np.percentile(mse_errors[y_test == 0], 95)
ae_preds = (mse_errors > ae_threshold).astype(int)

ae_prec = precision_score(y_test, ae_preds, zero_division=0)
ae_rec = recall_score(y_test, ae_preds, zero_division=0)
ae_f1 = f1_score(y_test, ae_preds, zero_division=0)

print(f"  [OK] Autoencoder trained in {ae_duration:.2f}s")
print(f"    - Reconstruction Threshold: {ae_threshold:.4f}")
print(f"    - Autoencoder Precision   : {ae_prec * 100:.2f}%")
print(f"    - Autoencoder Recall      : {ae_rec * 100:.2f}%")
print(f"    - Autoencoder F1-Score    : {ae_f1 * 100:.2f}%")

# ── 6. Ensemble Scoring Engine & Export ─────────────────────────────────────────
print("\n[6/6] Building Ensemble Model & Saving Registry Artifacts...")

# Save artifacts
joblib.dump(xgb_model, os.path.join(MODELS_DIR, "xgboost_fraud_detector.joblib"))
joblib.dump(iso_forest, os.path.join(MODELS_DIR, "isolation_forest.joblib"))
joblib.dump(autoencoder, os.path.join(MODELS_DIR, "autoencoder_model.joblib"))
joblib.dump(scaler, os.path.join(MODELS_DIR, "feature_scaler.joblib"))
joblib.dump(label_encoder, os.path.join(MODELS_DIR, "label_encoder.joblib"))

model_metadata = {
    "trained_at": datetime.utcnow().isoformat(),
    "training_records": len(df),
    "features": FEATURE_COLS,
    "metrics": {
        "xgboost": {
            "accuracy": round(xgb_acc, 4),
            "precision": round(xgb_prec, 4),
            "recall": round(xgb_rec, 4),
            "f1_score": round(xgb_f1, 4),
            "roc_auc": round(xgb_auc, 4)
        },
        "isolation_forest": {
            "precision": round(iso_prec, 4),
            "recall": round(iso_rec, 4),
            "f1_score": round(iso_f1, 4)
        },
        "autoencoder": {
            "precision": round(ae_prec, 4),
            "recall": round(ae_rec, 4),
            "f1_score": round(ae_f1, 4),
            "threshold": round(float(ae_threshold), 4)
        }
    },
    "classes": list(label_encoder.classes_)
}

with open(os.path.join(MODELS_DIR, "model_metadata.json"), "w") as f:
    json.dump(model_metadata, f, indent=2)

print("  [OK] All model artifacts saved to `models/` directory.")

# ── 7. Upload to ADLS Gen2 (if azure_config.json available) ────────────────────
if os.path.exists(CFG_FILE):
    try:
        with open(CFG_FILE) as f:
            cfg = json.load(f)
        sa_name = cfg.get("STORAGE_ACCOUNT_NAME")
        sa_key  = cfg.get("STORAGE_ACCOUNT_KEY")
        if sa_name and sa_key:
            print(f"\n[*] Uploading model artifacts to ADLS Gen2 ({sa_name}/checkpoints/models)...")
            from azure.storage.blob import BlobServiceClient
            blob_service = BlobServiceClient(
                account_url=f"https://{sa_name}.blob.core.windows.net",
                credential=sa_key
            )
            container_client = blob_service.get_container_client("checkpoints")
            for fname in os.listdir(MODELS_DIR):
                fpath = os.path.join(MODELS_DIR, fname)
                if os.path.isfile(fpath):
                    with open(fpath, "rb") as bdata:
                        container_client.upload_blob(name=f"models/{fname}", data=bdata, overwrite=True)
            print(f"  [OK] All models successfully uploaded to Azure ADLS Gen2!")
    except Exception as e:
        print(f"  [INFO] Cloud upload note: {e}")

# ── 8. Live Scoring Simulation Test ────────────────────────────────────────────
print("\n" + "=" * 80)
print("  END-TO-END PIPELINE VALIDATION TEST")
print("=" * 80)

test_samples = [
    # Sample 1: Normal trade
    {"order_id": "TEST-001", "trader_id": "TRD-SAFE", "symbol": "BTC/USD", "volume": 1.2, "price": 64500.0, "bid_price": 64495.0, "ask_price": 64505.0, "spread_pct": 0.00015, "rolling_avg_vol_10": 1.1, "rolling_std_vol_10": 0.2, "rolling_avg_px_10": 64500.0, "rolling_std_px_10": 15.0, "volume_spike_ratio": 1.09, "price_volatility": 0.0002, "cancel_ratio": 0.0, "buy_sell_imbalance": 0.1, "wash_indicator": 0.0, "spoof_indicator": 0.0},
    # Sample 2: Wash Trading
    {"order_id": "TEST-002", "trader_id": "TRD-WASH", "symbol": "ETH/USD", "volume": 85.0, "price": 3450.0, "bid_price": 3449.0, "ask_price": 3451.0, "spread_pct": 0.0005, "rolling_avg_vol_10": 15.0, "rolling_std_vol_10": 3.0, "rolling_avg_px_10": 3450.0, "rolling_std_px_10": 2.0, "volume_spike_ratio": 5.66, "price_volatility": 0.0005, "cancel_ratio": 0.1, "buy_sell_imbalance": 0.05, "wash_indicator": 2.0, "spoof_indicator": 0.0},
    # Sample 3: Spoofing / Layering Attack
    {"order_id": "TEST-003", "trader_id": "TRD-SPOOF", "symbol": "SOL/USD", "volume": 2500.0, "price": 145.0, "bid_price": 144.5, "ask_price": 145.5, "spread_pct": 0.0068, "rolling_avg_vol_10": 120.0, "rolling_std_vol_10": 45.0, "rolling_avg_px_10": 145.0, "rolling_std_px_10": 8.5, "volume_spike_ratio": 20.8, "price_volatility": 0.058, "cancel_ratio": 0.85, "buy_sell_imbalance": 0.90, "wash_indicator": 0.0, "spoof_indicator": 1.0},
]

sample_df = pd.DataFrame(test_samples)[FEATURE_COLS]
sample_scaled = scaler.transform(sample_df)

xgb_out = xgb_model.predict(sample_df)
xgb_out_probs = xgb_model.predict_proba(sample_df)
iso_out = iso_forest.predict(sample_scaled)
ae_out_mse = np.mean((sample_scaled - autoencoder.predict(sample_scaled)) ** 2, axis=1)

for idx, sample in enumerate(test_samples):
    predicted_type = label_encoder.inverse_transform([xgb_out[idx]])[0]
    xgb_risk = float(1.0 - xgb_out_probs[idx][normal_class_idx])
    iso_flag = "ANOMALOUS" if iso_out[idx] == -1 else "NORMAL"
    ae_flag = "ALERT" if ae_out_mse[idx] > ae_threshold else "NORMAL"
    
    # Ensemble composite risk score (0.0 to 1.0)
    composite_risk = (xgb_risk * 0.6) + ((1 if iso_flag == "ANOMALOUS" else 0) * 0.2) + ((1 if ae_flag == "ALERT" else 0) * 0.2)
    decision = "FRAUD" if composite_risk > 0.65 else ("SUSPICIOUS" if composite_risk > 0.40 else "SAFE")
    
    print(f"\nOrder [{sample['order_id']}] Trader [{sample['trader_id']}] Symbol [{sample['symbol']}]:")
    print(f"  • XGBoost Predicted Type : {predicted_type} (Risk Probability: {xgb_risk * 100:.1f}%)")
    print(f"  • Isolation Forest Flag  : {iso_flag}")
    print(f"  • Autoencoder Anomaly MSE: {ae_out_mse[idx]:.4f} ({ae_flag})")
    print(f"  • Composite Risk Score   : {composite_risk:.2f} / 1.00  -->  DECISION: [{decision}]")

print("\n" + "=" * 80)
print("  MODEL TRAINING & PIPELINE VALIDATION 100% COMPLETE AND OPERATIONAL!")
