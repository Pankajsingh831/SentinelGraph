# SentinelGraph — ML Pipeline

## Problem Statement

Detect coordinated payment abuse — patterns where individual transactions appear normal but become suspicious when viewed as a connected network. Traditional per-transaction models miss these patterns.

## Feature Groups

### 1. Transaction Features
- `amount`, `amount_log` (log-transformed)
- `is_refund`, `is_transfer` (binary flags)
- `merchant_category_encoded`, `currency_encoded` (label-encoded)

### 2. Temporal Features
- `transaction_count_5m`, `transaction_count_1h`, `transaction_count_24h` (rolling velocity)
- `time_since_previous_transaction` (seconds)
- `account_age_hours`
- `hour_of_day`, `day_of_week`, `is_night`, `is_weekend`

### 3. Behavioral Features
- `avg_transaction_amount` (running average)
- `amount_deviation` (z-score from customer mean)
- `refund_rate` (expanding refund fraction)
- `merchant_count`, `device_count`, `instrument_count` (distinct counts)

### 4. Graph Features ⭐
- `device_account_count` — accounts sharing the same device
- `ip_account_count` — accounts sharing the same IP
- `instrument_account_count` — accounts sharing the same instrument
- `network_size` — connected component size
- `network_density` — edge density of customer's network
- `node_degree` — entity connections
- `network_growth_rate` — new connections in trailing 7 days

## Leakage Prevention

All features use **only past data** relative to each transaction's `occurred_at` timestamp:
- Temporal features: rolling windows look backward only
- Graph features: only relationships with `first_seen_at <= occurred_at`
- Split: chronological 70/15/15 (oldest → newest), never random
- Validated by `FeaturePipeline.validate_no_leakage()`

## Models

| Model | Features | Algorithm |
|-------|----------|-----------|
| Model 0 | Transaction + Temporal + Behavioral | Logistic Regression |
| Model 1 | Transaction + Temporal + Behavioral | XGBoost (200 trees, depth 6) |
| **Model 2** | **All features including Graph** | **XGBoost (200 trees, depth 6)** |

### XGBoost Hyperparameters
```python
n_estimators=200, max_depth=6, learning_rate=0.1,
scale_pos_weight=<auto from class imbalance>,
eval_metric='aucpr', early_stopping_rounds=20
```

## Explainability (SHAP)

- `shap.TreeExplainer` with `feature_perturbation='tree_path_dependent'`
- Per-prediction feature contributions sorted by absolute value
- Top-5 features displayed to analyst per case
- Model saved as `.json` (not pickle) for SHAP compatibility

## Evaluation Metrics

- **Primary**: PR-AUC (imbalanced dataset)
- **Secondary**: Precision, Recall, F1, FPR, ROC-AUC
- **Operational**: p50/p95/p99 inference latency
- **Threshold**: F1-optimal on validation set

## Pipeline Commands

```bash
make simulate    # Generate synthetic data
make train       # Train all three models
make evaluate    # Compare models and generate report
```
