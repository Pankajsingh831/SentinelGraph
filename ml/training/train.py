import os
import sys
import json
import time
from datetime import datetime, timezone
from pathlib import Path
import bisect

import numpy as np
import pandas as pd
import joblib
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
import xgboost as xgb
from sqlalchemy import text

from app.database import engine
from ml.features.pipeline import FeaturePipeline
from ml.training.split import chronological_split
from ml.training.evaluate import ModelEvaluator


class ModelTrainer:
    """Trains and saves Model 0 (LogReg), Model 1 (XGBoost no graph), Model 2 (XGBoost + graph)."""
    
    TRANSACTION_TEMPORAL_BEHAVIORAL_FEATURES = [
        'amount', 'amount_log', 'is_refund', 'is_transfer',
        'merchant_category_encoded', 'currency_encoded',
        'transaction_count_5m', 'transaction_count_1h', 'transaction_count_24h',
        'time_since_previous_transaction', 'account_age_hours',
        'hour_of_day', 'day_of_week', 'is_night', 'is_weekend',
        'avg_transaction_amount', 'amount_deviation', 'refund_rate',
        'merchant_count', 'device_count', 'instrument_count'
    ]
    
    GRAPH_FEATURES = [
        'device_account_count', 'ip_account_count', 'instrument_account_count',
        'network_size', 'network_density', 'node_degree', 'network_growth_rate'
    ]
    
    def __init__(self, output_dir: str = 'model_artifacts'):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def train_model_0(self, train_X, train_y, val_X, val_y):
        """Model 0: Logistic Regression baseline (transaction+temporal+behavioral only).
        Uses StandardScaler inside a Pipeline to guarantee numerical stability and convergence.
        """
        pipeline = Pipeline([
            ('scaler', StandardScaler()),
            ('classifier', LogisticRegression(max_iter=1000, class_weight='balanced', random_state=42))
        ])
        train_X_clean = train_X.fillna(0)
        pipeline.fit(train_X_clean, train_y)
        return pipeline
    
    def train_model_1(self, train_X, train_y, val_X, val_y) -> xgb.XGBClassifier:
        """Model 1: XGBoost WITHOUT graph features."""
        scale_pos_weight = float(np.sum(train_y == 0) / np.sum(train_y == 1)) if np.sum(train_y == 1) > 0 else 1.0
        
        model = xgb.XGBClassifier(
            n_estimators=200, 
            max_depth=6, 
            learning_rate=0.1, 
            scale_pos_weight=scale_pos_weight,
            eval_metric='aucpr', 
            early_stopping_rounds=20,
            random_state=42
        )
        
        model.fit(
            train_X, train_y,
            eval_set=[(val_X, val_y)],
            verbose=False
        )
        return model
    
    def train_model_2(self, train_X, train_y, val_X, val_y) -> xgb.XGBClassifier:
        """Model 2: XGBoost WITH graph features (the primary model)."""
        scale_pos_weight = float(np.sum(train_y == 0) / np.sum(train_y == 1)) if np.sum(train_y == 1) > 0 else 1.0
        
        model = xgb.XGBClassifier(
            n_estimators=200, 
            max_depth=6, 
            learning_rate=0.1, 
            scale_pos_weight=scale_pos_weight,
            eval_metric='aucpr', 
            early_stopping_rounds=20,
            random_state=42
        )
        
        model.fit(
            train_X, train_y,
            eval_set=[(val_X, val_y)],
            verbose=False
        )
        return model
    
    def save_model(self, model, name: str, version: str, metrics: dict = None):
        """Save model artifact + metrics JSON."""
        model_path = self.output_dir / version
        model_path.mkdir(parents=True, exist_ok=True)
        
        if isinstance(model, xgb.XGBClassifier):
            # Ensure _estimator_type is defined for scikit-learn/xgboost serialization compatibility
            if not hasattr(model, "_estimator_type") or model._estimator_type is None:
                model._estimator_type = "classifier"
            # Save XGBoost as .json for SHAP compatibility
            model.save_model(str(model_path / f"{name}.json"))
        else:
            joblib.dump(model, str(model_path / f"{name}.joblib"))
            
        if metrics:
            with open(model_path / f"{name}_metrics.json", "w") as f:
                json.dump(metrics, f, indent=4)
    
    def train_all(self, train_df, val_df, feature_names_no_graph, feature_names_with_graph, label='is_abuse'):
        """Train all three models and save artifacts."""
        print("Training Model 0...")
        model_0 = self.train_model_0(
            train_df[feature_names_no_graph], train_df[label],
            val_df[feature_names_no_graph], val_df[label]
        )
        self.save_model(model_0, "model_0", "v1")
        
        print("Training Model 1...")
        model_1 = self.train_model_1(
            train_df[feature_names_no_graph], train_df[label],
            val_df[feature_names_no_graph], val_df[label]
        )
        self.save_model(model_1, "model_1", "v1")
        
        print("Training Model 2...")
        model_2 = self.train_model_2(
            train_df[feature_names_with_graph], train_df[label],
            val_df[feature_names_with_graph], val_df[label]
        )
        self.save_model(model_2, "model_2", "v1")


async def load_database_data():
    """Load transactions, customers, entity_relationships, and ground truth from PostgreSQL."""
    async with engine.connect() as conn:
        print("Loading transactions...")
        tx_query = """
            SELECT transaction_id, customer_id, merchant_id, device_id, instrument_id, ip_id,
                   amount, currency, transaction_type, status, occurred_at
            FROM transactions
            ORDER BY occurred_at ASC
        """
        res = await conn.execute(text(tx_query))
        tx_df = pd.DataFrame(res.fetchall(), columns=res.keys())
        tx_df['occurred_at'] = pd.to_datetime(tx_df['occurred_at'], utc=True)
        tx_df['amount'] = tx_df['amount'].astype(float)
        tx_df['type'] = tx_df['transaction_type']
        print(f"Loaded {len(tx_df)} transactions.")

        print("Loading customers...")
        cust_query = """
            SELECT customer_id, country, status, account_created_at
            FROM customers
        """
        res = await conn.execute(text(cust_query))
        cust_df = pd.DataFrame(res.fetchall(), columns=res.keys())
        cust_df['account_created_at'] = pd.to_datetime(cust_df['account_created_at'], utc=True)
        print(f"Loaded {len(cust_df)} customers.")

        print("Loading relationships...")
        rel_query = """
            SELECT source_type, source_id, relationship_type, target_type, target_id,
                   first_seen_at, last_seen_at, interaction_count
            FROM entity_relationships
            ORDER BY first_seen_at ASC
        """
        res = await conn.execute(text(rel_query))
        rel_df = pd.DataFrame(res.fetchall(), columns=res.keys())
        print(f"Loaded {len(rel_df)} rows from entity_relationships table.")

        if len(rel_df) < len(tx_df) * 0.1:
            print(f"Database entity_relationships table contains only {len(rel_df)} rows (due to offline state/limited replay).")
            print(f"Constructing complete historical relationships from all {len(tx_df)} transactions for feature extraction...")
            records = []
            for pair_type, col in [('device', 'device_id'), ('ip', 'ip_id'), ('instrument', 'instrument_id')]:
                valid = tx_df[['customer_id', col, 'occurred_at']].dropna()
                grouped = valid.groupby(['customer_id', col]).agg(
                    first_seen_at=('occurred_at', 'min'),
                    last_seen_at=('occurred_at', 'max'),
                    interaction_count=('occurred_at', 'count')
                ).reset_index()
                for row in grouped.itertuples(index=False):
                    records.append({
                        'source_type': 'customer',
                        'source_id': row[0],
                        'relationship_type': 'uses',
                        'target_type': pair_type,
                        'target_id': row[1],
                        'first_seen_at': row[2],
                        'last_seen_at': row[3],
                        'interaction_count': row[4]
                    })
            rel_df = pd.DataFrame(records)
            rel_df['first_seen_at'] = pd.to_datetime(rel_df['first_seen_at'], utc=True)
            rel_df['last_seen_at'] = pd.to_datetime(rel_df['last_seen_at'], utc=True)
            print(f"Constructed {len(rel_df)} complete historical relationships.")

        print("Loading ground truth...")
        gt_query = """
            SELECT entity_id, is_abuse, abuse_type
            FROM ground_truth
            WHERE entity_type = 'transaction'
        """
        res = await conn.execute(text(gt_query))
        gt_df = pd.DataFrame(res.fetchall(), columns=res.keys())
        print(f"Loaded {len(gt_df)} transaction-level ground truth labels.")

        # Check for duplicate transaction labels
        duplicates = gt_df['entity_id'].duplicated()
        if duplicates.any():
            dup_count = duplicates.sum()
            raise ValueError(f"CRITICAL ERROR: Found {dup_count} duplicate transaction labels in ground_truth!")

        return tx_df, cust_df, rel_df, gt_df


def handle_missing_values(train_df, val_df, test_df, feature_cols):
    """Safely impute NaN and inf values using statistics derived strictly from train_df."""
    print("\n--- Feature Quality & Imputation Report ---")
    
    imputation_values = {}
    nan_counts = {}
    inf_counts = {}
    
    for col in feature_cols:
        # Convert infinite values to NaN
        for split_name, split_df in [('train', train_df), ('val', val_df), ('test', test_df)]:
            inf_mask = np.isinf(split_df[col].values)
            if inf_mask.any():
                inf_counts[f"{split_name}_{col}"] = int(inf_mask.sum())
                split_df.loc[inf_mask, col] = np.nan
        
        # Determine imputation value strictly from train_df
        train_series = train_df[col].dropna()
        if len(train_series) > 0:
            # Use median for continuous, 0 for binary/counts
            val = float(train_series.median())
        else:
            val = 0.0
        imputation_values[col] = val
        
        train_nans = int(train_df[col].isna().sum())
        val_nans = int(val_df[col].isna().sum())
        test_nans = int(test_df[col].isna().sum())
        
        if train_nans > 0 or val_nans > 0 or test_nans > 0:
            nan_counts[col] = (train_nans, val_nans, test_nans)
            
        train_df[col] = train_df[col].fillna(val)
        val_df[col] = val_df[col].fillna(val)
        test_df[col] = test_df[col].fillna(val)

    if nan_counts:
        print(f"Features with NaNs imputed (train, val, test): {nan_counts}")
    else:
        print("No NaNs detected across feature sets.")
        
    if inf_counts:
        print(f"Infinite values cleaned: {inf_counts}")
    else:
        print("No infinite values detected.")

    # Confirm clean matrices
    assert not train_df[feature_cols].isna().any().any(), "NaNs remain in train_df after imputation!"
    assert not val_df[feature_cols].isna().any().any(), "NaNs remain in val_df after imputation!"
    assert not test_df[feature_cols].isna().any().any(), "NaNs remain in test_df after imputation!"
    print("All features verified clean (0 NaNs, 0 Infs).\n")


def print_graph_feature_sanity_check(df, graph_features):
    """Validate that graph features are populated, varied, and non-constant."""
    print("\n================ GRAPH FEATURE SANITY CHECK ================")
    print(f"{'Feature Name':<28} | {'Non-Null':<8} | {'Min':<8} | {'Max':<10} | {'Mean':<10}")
    print("-" * 72)
    
    all_zero_or_constant = True
    for col in graph_features:
        series = df[col]
        cnt = int(series.count())
        c_min = float(series.min())
        c_max = float(series.max())
        c_mean = float(series.mean())
        
        print(f"{col:<28} | {cnt:<8} | {c_min:<8.4f} | {c_max:<10.4f} | {c_mean:<10.4f}")
        
        if c_max > c_min and c_max > 0:
            all_zero_or_constant = False
            
    print("=" * 72)
    
    if all_zero_or_constant:
        raise RuntimeError("CRITICAL WARNING: All graph features are zero or constant! Stopping training pipeline.")


def run_pipeline():
    """Execute the full end-to-end ML training pipeline."""
    import asyncio
    
    # 1. Load data
    tx_df, cust_df, rel_df, gt_df = asyncio.run(load_database_data())
    
    # 2. Build features
    print("Building features...")
    pipeline = FeaturePipeline(include_graph_features=True)
    features_df = pipeline.build_features(
        transactions_df=tx_df,
        customers_df=cust_df,
        relationships_df=rel_df
    )
    print(f"Features extracted: {features_df.shape[1]} columns for {len(features_df)} transactions.")
    
    # 3. Join ground truth labels
    print("Joining labels...")
    merged_df = features_df.merge(
        gt_df,
        left_on='transaction_id',
        right_on='entity_id',
        how='inner'
    )
    
    if len(merged_df) != len(tx_df):
        raise ValueError(f"Label join mismatch: expected {len(tx_df)} rows but got {len(merged_df)} rows!")
        
    merged_df['is_abuse'] = merged_df['is_abuse'].astype(int)
    print(f"Joined labels successfully. Total labeled transactions: {len(merged_df)}.")
    
    # 4. Prevent leakage & validate features
    print("Validating leakage...")
    assert merged_df['occurred_at'].is_monotonic_increasing, "Transactions are not in chronological order!"
    
    no_graph_features = ModelTrainer.TRANSACTION_TEMPORAL_BEHAVIORAL_FEATURES
    graph_features = ModelTrainer.GRAPH_FEATURES
    all_features = no_graph_features + graph_features
    
    # Ensure forbidden leakage columns are not in feature list
    forbidden = {'is_abuse', 'abuse_type', 'transaction_id', 'entity_id', 'occurred_at'}
    for col in forbidden:
        assert col not in all_features, f"Leakage violation: {col} is included in feature list!"
        
    # Check that all required features exist in DataFrame
    missing_features = [f for f in all_features if f not in merged_df.columns]
    if missing_features:
        raise ValueError(
            f"Missing features:\n{missing_features}\n"
            f"Available features:\n{list(merged_df.columns)}"
        )
    print("Leakage validation passed: features are chronological and free of label/identifier leakage.")
    
    # 5. Graph Feature Sanity Check
    print_graph_feature_sanity_check(merged_df, graph_features)
    
    # 6. Chronological split
    print("Splitting chronologically...")
    train_df, val_df, test_df = chronological_split(
        merged_df,
        train_ratio=0.70,
        val_ratio=0.15,
        test_ratio=0.15,
        time_column='occurred_at'
    )
    
    print("\n--- Split Diagnostic Summary ---")
    print(f"Train rows: {len(train_df)} ({train_df['occurred_at'].min()} to {train_df['occurred_at'].max()})")
    print(f"Validation rows: {len(val_df)} ({val_df['occurred_at'].min()} to {val_df['occurred_at'].max()})")
    print(f"Test rows: {len(test_df)} ({test_df['occurred_at'].min()} to {test_df['occurred_at'].max()})")
    print(f"Train abuse ratio: {train_df['is_abuse'].mean():.4f} ({train_df['is_abuse'].sum()} abuse cases)")
    print(f"Validation abuse ratio: {val_df['is_abuse'].mean():.4f} ({val_df['is_abuse'].sum()} abuse cases)")
    print(f"Test abuse ratio: {test_df['is_abuse'].mean():.4f} ({test_df['is_abuse'].sum()} abuse cases)\n")
    
    # 7. Safe Missing Value Handling
    handle_missing_values(train_df, val_df, test_df, all_features)
    
    train_y = train_df['is_abuse']
    val_y = val_df['is_abuse']
    test_y = test_df['is_abuse']
    
    # 8. Train Models
    trainer = ModelTrainer(output_dir='model_artifacts')
    
    print("Training Model 0 (Logistic Regression baseline)...")
    model_0 = trainer.train_model_0(
        train_df[no_graph_features], train_y,
        val_df[no_graph_features], val_y
    )
    print("Model 0 training complete.")
    
    print("Training Model 1 (XGBoost without graph features)...")
    model_1 = trainer.train_model_1(
        train_df[no_graph_features], train_y,
        val_df[no_graph_features], val_y
    )
    print("Model 1 training complete.")
    
    print("Training Model 2 (XGBoost WITH graph features)...")
    model_2 = trainer.train_model_2(
        train_df[all_features], train_y,
        val_df[all_features], val_y
    )
    print("Model 2 training complete.")
    
    # 9. Evaluate Models on Test Set
    print("Evaluating models on held-out test set...")
    evaluator = ModelEvaluator()
    metrics_0 = evaluator.evaluate_model(model_0, test_df[no_graph_features], test_y, "Model 0")
    metrics_1 = evaluator.evaluate_model(model_1, test_df[no_graph_features], test_y, "Model 1")
    metrics_2 = evaluator.evaluate_model(model_2, test_df[all_features], test_y, "Model 2")
    
    # 10. Model Comparison
    print("\n================ MODEL COMPARISON ================\n")
    print("Model 0 — Logistic Regression")
    print(f"ROC-AUC:   {metrics_0['roc_auc']:.4f}")
    print(f"PR-AUC:    {metrics_0['pr_auc']:.4f}")
    print(f"Precision: {metrics_0['precision']:.4f}")
    print(f"Recall:    {metrics_0['recall']:.4f}")
    print(f"F1:        {metrics_0['f1']:.4f}\n")
    
    print("Model 1 — XGBoost without graph")
    print(f"ROC-AUC:   {metrics_1['roc_auc']:.4f}")
    print(f"PR-AUC:    {metrics_1['pr_auc']:.4f}")
    print(f"Precision: {metrics_1['precision']:.4f}")
    print(f"Recall:    {metrics_1['recall']:.4f}")
    print(f"F1:        {metrics_1['f1']:.4f}\n")
    
    print("Model 2 — XGBoost with graph")
    print(f"ROC-AUC:   {metrics_2['roc_auc']:.4f}")
    print(f"PR-AUC:    {metrics_2['pr_auc']:.4f}")
    print(f"Precision: {metrics_2['precision']:.4f}")
    print(f"Recall:    {metrics_2['recall']:.4f}")
    print(f"F1:        {metrics_2['f1']:.4f}")
    print("===================================================\n")
    
    print(evaluator.compare_models([metrics_0, metrics_1, metrics_2]))
    print()
    
    # 11. Save Artifacts
    print("Saving artifacts...")
    version = "v1"
    trainer.save_model(model_0, "model_0", version, metrics=metrics_0)
    trainer.save_model(model_1, "model_1", version, metrics=metrics_1)
    trainer.save_model(model_2, "model_2", version, metrics=metrics_2)
    
    # Save root model_2.json for API service compatibility
    model_2.save_model(str(trainer.output_dir / "model_2.json"))
    
    # Save feature names
    feature_names_path = trainer.output_dir / version / "feature_names.json"
    with open(feature_names_path, "w") as f:
        json.dump({
            "no_graph_features": no_graph_features,
            "graph_features": graph_features,
            "all_features": all_features
        }, f, indent=4)
        
    # Save training metadata
    metadata_path = trainer.output_dir / version / "training_metadata.json"
    training_metadata = {
        "version": version,
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "total_transactions": len(merged_df),
        "total_abuse_cases": int(merged_df['is_abuse'].sum()),
        "train_rows": len(train_df),
        "train_abuse_count": int(train_df['is_abuse'].sum()),
        "val_rows": len(val_df),
        "val_abuse_count": int(val_df['is_abuse'].sum()),
        "test_rows": len(test_df),
        "test_abuse_count": int(test_df['is_abuse'].sum()),
        "train_time_range": [str(train_df['occurred_at'].min()), str(train_df['occurred_at'].max())],
        "val_time_range": [str(val_df['occurred_at'].min()), str(val_df['occurred_at'].max())],
        "test_time_range": [str(test_df['occurred_at'].min()), str(test_df['occurred_at'].max())],
        "model_0_pr_auc": metrics_0['pr_auc'],
        "model_1_pr_auc": metrics_1['pr_auc'],
        "model_2_pr_auc": metrics_2['pr_auc']
    }
    with open(metadata_path, "w") as f:
        json.dump(training_metadata, f, indent=4)
        
    print(f"Artifacts successfully saved in {trainer.output_dir / version}")
    print("Training complete.")


def main():
    try:
        run_pipeline()
        sys.exit(0)
    except Exception as e:
        print(f"\nCRITICAL PIPELINE FAILURE: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
