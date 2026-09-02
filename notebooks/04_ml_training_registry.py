# Databricks Notebook: 04_ml_training_registry.py
# PATH A - ML Training Pipeline
# Loads training_data.csv, engineers features, trains 3 models
# (XGBoost, Isolation Forest, Autoencoder), evaluates, registers best in MLflow.

# ─── Cell 1: Install libraries (run once) ────────────────────────────────────
# %pip install xgboost scikit-learn mlflow torch torchvision

# ─── Cell 2: Config & Imports ────────────────────────────────────────────────
import mlflow
import mlflow.sklearn
import mlflow.xgboost
import mlflow.pytorch

import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, confusion_matrix, classification_report
)
import xgboost as xgb
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset
import warnings
warnings.filterwarnings("ignore")

storage_account = dbutils.secrets.get(scope="fraud-kv-scope", key="storage-account-name")
storage_key     = dbutils.secrets.get(scope="fraud-kv-scope", key="storage-account-key")

spark.conf.set(
    f"fs.azure.account.key.{storage_account}.dfs.core.windows.net",
    storage_key
)

CATALOG          = "fraud_detection_catalog"
TRAINING_CSV     = f"abfss://training-data@{storage_account}.dfs.core.windows.net/training_data.csv"
EXPERIMENT_NAME  = "/Shared/FraudDetection_MLExperiment"
MODEL_NAME       = "FraudDetectionModel"

mlflow.set_experiment(EXPERIMENT_NAME)
print("MLflow experiment:", EXPERIMENT_NAME)

# ─── Cell 3: Load training data ───────────────────────────────────────────────
print("Loading training data from ADLS...")
df_spark = spark.read.csv(TRAINING_CSV, header=True, inferSchema=True)
df = df_spark.toPandas()
print(f"Loaded {len(df):,} records | Fraud rate: {df['is_fraud'].mean()*100:.1f}%")
print(df["fraud_type"].value_counts())

# ─── Cell 4: Feature engineering on labeled data ──────────────────────────────
# Same feature signals as the live pipeline (03_gold_feature_engineering.py)
# but computed on the static labeled CSV using Pandas rolling windows.

# Sort by trader+symbol+timestamp for rolling calculations
df["timestamp"] = pd.to_datetime(df["timestamp"])
df = df.sort_values(["trader_id", "symbol", "timestamp"]).reset_index(drop=True)

# Per-group rolling stats
def compute_rolling_features(group):
    group = group.copy()
    group["rolling_avg_volume_10"]  = group["volume"].rolling(10, min_periods=1).mean()
    group["rolling_avg_price_10"]   = group["price"].rolling(10, min_periods=1).mean()
    group["rolling_std_price_10"]   = group["price"].rolling(10, min_periods=1).std().fillna(0)
    group["rolling_max_price_10"]   = group["price"].rolling(10, min_periods=1).max()
    group["rolling_min_price_10"]   = group["price"].rolling(10, min_periods=1).min()
    group["cancel_count_10"]        = (group["order_status"] == "cancelled").rolling(10, min_periods=1).sum()
    group["order_count_10"]         = group["volume"].rolling(10, min_periods=1).count()
    group["buy_count_10"]           = (group["order_type"] == "buy").rolling(10, min_periods=1).sum()
    group["sell_count_10"]          = (group["order_type"] == "sell").rolling(10, min_periods=1).sum()
    return group

df = df.groupby(["trader_id", "symbol"], group_keys=False).apply(compute_rolling_features)

# Derived fraud-signal features
EPSILON = 1e-9
df["volume_spike_ratio"]    = df["volume"] / (df["rolling_avg_volume_10"] + EPSILON)
df["price_range_pct"]       = (df["rolling_max_price_10"] - df["rolling_min_price_10"]) / (df["rolling_avg_price_10"] + EPSILON) * 100
df["cancel_to_trade_ratio"] = df["cancel_count_10"] / (df["order_count_10"] + EPSILON)
df["wash_trade_flag"]       = ((df["buy_count_10"] > 0) & (df["sell_count_10"] > 0)).astype(int)
df["layering_flag"]         = (df["order_count_10"] >= 5).astype(int)
df["orders_per_minute"]     = df["order_count_10"] / 10.0
df["buy_sell_imbalance"]    = abs(df["buy_count_10"] - df["sell_count_10"]) / (df["order_count_10"] + EPSILON)
df["price_deviation_pct"]   = abs(df["price"] - df["rolling_avg_price_10"]) / (df["rolling_avg_price_10"] + EPSILON) * 100

FEATURES = [
    "volume_spike_ratio", "price_range_pct", "cancel_to_trade_ratio",
    "wash_trade_flag", "layering_flag", "orders_per_minute",
    "buy_sell_imbalance", "price_deviation_pct",
    "volume", "price"
]

X = df[FEATURES].fillna(0)
y = df["is_fraud"].astype(int)

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled  = scaler.transform(X_test)

print(f"Train: {len(X_train):,} | Test: {len(X_test):,}")
print(f"Fraud in test: {y_test.sum()} ({y_test.mean()*100:.1f}%)")

# ─── Cell 5: Model 1 - XGBoost (Supervised) ──────────────────────────────────
print("\n--- Training XGBoost ---")

fraud_weight = (y_train == 0).sum() / (y_train == 1).sum()

with mlflow.start_run(run_name="XGBoost_Supervised") as run_xgb:
    xgb_params = {
        "n_estimators": 300, "max_depth": 6, "learning_rate": 0.05,
        "scale_pos_weight": fraud_weight, "use_label_encoder": False,
        "eval_metric": "logloss", "random_state": 42, "n_jobs": -1
    }
    xgb_model = xgb.XGBClassifier(**xgb_params)
    xgb_model.fit(X_train_scaled, y_train, eval_set=[(X_test_scaled, y_test)], verbose=False)

    y_pred_xgb  = xgb_model.predict(X_test_scaled)
    y_prob_xgb  = xgb_model.predict_proba(X_test_scaled)[:, 1]

    metrics_xgb = {
        "accuracy":  accuracy_score(y_test, y_pred_xgb),
        "precision": precision_score(y_test, y_pred_xgb),
        "recall":    recall_score(y_test, y_pred_xgb),
        "f1":        f1_score(y_test, y_pred_xgb),
        "roc_auc":   roc_auc_score(y_test, y_prob_xgb),
    }
    mlflow.log_params(xgb_params)
    mlflow.log_metrics(metrics_xgb)
    mlflow.xgboost.log_model(xgb_model, "xgboost_model")

    print("XGBoost Results:")
    for k, v in metrics_xgb.items():
        print(f"  {k}: {v:.4f}")
    print(classification_report(y_test, y_pred_xgb, target_names=["Normal", "Fraud"]))
    xgb_run_id = run_xgb.info.run_id

# ─── Cell 6: Model 2 - Isolation Forest (Unsupervised) ───────────────────────
print("\n--- Training Isolation Forest ---")

with mlflow.start_run(run_name="IsolationForest_Unsupervised") as run_if:
    if_params = {"n_estimators": 200, "contamination": 0.15, "random_state": 42, "n_jobs": -1}
    if_model = IsolationForest(**if_params)
    # Train on NORMAL trades only (unsupervised: learns what normal looks like)
    X_train_normal = X_train_scaled[y_train == 0]
    if_model.fit(X_train_normal)

    # Predict: IsolationForest returns -1 (anomaly) / 1 (normal)
    y_pred_if_raw = if_model.predict(X_test_scaled)
    y_pred_if     = np.where(y_pred_if_raw == -1, 1, 0)  # convert to 0=normal, 1=fraud
    y_score_if    = -if_model.score_samples(X_test_scaled)  # higher = more anomalous

    metrics_if = {
        "accuracy":  accuracy_score(y_test, y_pred_if),
        "precision": precision_score(y_test, y_pred_if),
        "recall":    recall_score(y_test, y_pred_if),
        "f1":        f1_score(y_test, y_pred_if),
        "roc_auc":   roc_auc_score(y_test, y_score_if),
    }
    mlflow.log_params(if_params)
    mlflow.log_metrics(metrics_if)
    mlflow.sklearn.log_model(if_model, "isolation_forest_model")
    # Also save scaler
    mlflow.sklearn.log_model(scaler, "feature_scaler")

    print("Isolation Forest Results:")
    for k, v in metrics_if.items():
        print(f"  {k}: {v:.4f}")
    if_run_id = run_if.info.run_id

# ─── Cell 7: Model 3 - Autoencoder (Unsupervised Neural Network) ──────────────
print("\n--- Training Autoencoder ---")

class FraudAutoencoder(nn.Module):
    def __init__(self, input_dim, encoding_dim=5):
        super().__init__()
        self.encoder = nn.Sequential(
            nn.Linear(input_dim, 16),
            nn.ReLU(),
            nn.Linear(16, encoding_dim),
            nn.ReLU()
        )
        self.decoder = nn.Sequential(
            nn.Linear(encoding_dim, 16),
            nn.ReLU(),
            nn.Linear(16, input_dim)
        )

    def forward(self, x):
        return self.decoder(self.encoder(x))


with mlflow.start_run(run_name="Autoencoder_Unsupervised") as run_ae:
    INPUT_DIM    = len(FEATURES)
    ENCODING_DIM = 5
    EPOCHS       = 50
    BATCH_SIZE   = 256
    LR           = 1e-3

    ae_model  = FraudAutoencoder(INPUT_DIM, ENCODING_DIM)
    criterion = nn.MSELoss()
    optimizer = optim.Adam(ae_model.parameters(), lr=LR)

    # Train only on normal trades
    X_normal_tensor = torch.tensor(X_train_scaled[y_train == 0], dtype=torch.float32)
    dataset = TensorDataset(X_normal_tensor)
    loader  = DataLoader(dataset, batch_size=BATCH_SIZE, shuffle=True)

    ae_model.train()
    for epoch in range(EPOCHS):
        epoch_loss = 0.0
        for (batch,) in loader:
            optimizer.zero_grad()
            recon = ae_model(batch)
            loss  = criterion(recon, batch)
            loss.backward()
            optimizer.step()
            epoch_loss += loss.item()
        if (epoch + 1) % 10 == 0:
            print(f"  Epoch {epoch+1}/{EPOCHS} | Loss: {epoch_loss/len(loader):.6f}")

    # Score test set by reconstruction error
    ae_model.eval()
    with torch.no_grad():
        X_test_tensor  = torch.tensor(X_test_scaled, dtype=torch.float32)
        reconstructed  = ae_model(X_test_tensor)
        recon_errors   = torch.mean((X_test_tensor - reconstructed) ** 2, dim=1).numpy()

    # Threshold at 95th percentile of normal test reconstruction errors
    normal_errors = recon_errors[y_test == 0]
    threshold     = np.percentile(normal_errors, 95)
    y_pred_ae     = (recon_errors > threshold).astype(int)

    metrics_ae = {
        "accuracy":       accuracy_score(y_test, y_pred_ae),
        "precision":      precision_score(y_test, y_pred_ae),
        "recall":         recall_score(y_test, y_pred_ae),
        "f1":             f1_score(y_test, y_pred_ae),
        "roc_auc":        roc_auc_score(y_test, recon_errors),
        "recon_threshold": float(threshold),
    }
    ae_params = {"input_dim": INPUT_DIM, "encoding_dim": ENCODING_DIM,
                 "epochs": EPOCHS, "batch_size": BATCH_SIZE, "lr": LR}
    mlflow.log_params(ae_params)
    mlflow.log_metrics(metrics_ae)
    mlflow.pytorch.log_model(ae_model, "autoencoder_model")

    print("Autoencoder Results:")
    for k, v in metrics_ae.items():
        print(f"  {k}: {v:.4f}")
    ae_run_id = run_ae.info.run_id

# ─── Cell 8: Select Champion Model & Register in MLflow ──────────────────────
print("\n--- Model Comparison ---")
results = {
    "XGBoost":         {"f1": metrics_xgb["f1"], "roc_auc": metrics_xgb["roc_auc"], "run_id": xgb_run_id, "artifact": "xgboost_model"},
    "IsolationForest": {"f1": metrics_if["f1"],  "roc_auc": metrics_if["roc_auc"],  "run_id": if_run_id,  "artifact": "isolation_forest_model"},
    "Autoencoder":     {"f1": metrics_ae["f1"],  "roc_auc": metrics_ae["roc_auc"],  "run_id": ae_run_id,  "artifact": "autoencoder_model"},
}
for name, r in results.items():
    print(f"  {name:20s} | F1: {r['f1']:.4f} | ROC-AUC: {r['roc_auc']:.4f}")

champion = max(results, key=lambda k: results[k]["roc_auc"])
print(f"\n[*] Champion Model: {champion} (ROC-AUC: {results[champion]['roc_auc']:.4f})")

# Register champion in MLflow Model Registry
model_uri = f"runs:/{results[champion]['run_id']}/{results[champion]['artifact']}"
mv = mlflow.register_model(model_uri=model_uri, name=MODEL_NAME)
print(f"[*] Model '{MODEL_NAME}' registered as version {mv.version}")

# Also register XGBoost always (for Databricks Model Serving which prefers sklearn/xgboost)
xgb_uri = f"runs:/{xgb_run_id}/xgboost_model"
mv_xgb = mlflow.register_model(model_uri=xgb_uri, name=f"{MODEL_NAME}_XGBoost")
print(f"[*] XGBoost model registered as '{MODEL_NAME}_XGBoost' version {mv_xgb.version}")

print("\nML Training Pipeline Complete. Next step: Deploy serving endpoint from Databricks UI or 05_realtime_scoring_engine.py")
