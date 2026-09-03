import os
import json
import uuid
import time
import structlog
import xgboost as xgb
import numpy as np
import pandas as pd
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.database import get_db
from app.schemas.risk import RiskScoreRequest, RiskScoreResponse, RiskExplanationResponse, FeatureContribution
from app.repositories import transaction_repo, risk_repo
from app.config import get_settings

from ml.features.transaction import extract_transaction_features
from ml.features.temporal import extract_temporal_features
from ml.features.behavioral import extract_behavioral_features
from ml.features.graph import extract_graph_features

logger = structlog.get_logger()
router = APIRouter(prefix="/api/v1/risk", tags=["risk"])

# Global model & explainer cache
_model = None
_explainer = None
_feature_names = None
_prediction_cache = {}  # prediction_id -> (X, feature_names)

CURRENCY_CATEGORIES = ['AUD', 'BRL', 'EUR', 'GBP', 'INR', 'JPY', 'USD']

EXPECTED_28_FEATURES = [
    'amount', 'amount_log', 'is_refund', 'is_transfer',
    'merchant_category_encoded', 'currency_encoded',
    'transaction_count_5m', 'transaction_count_1h', 'transaction_count_24h',
    'time_since_previous_transaction', 'account_age_hours',
    'hour_of_day', 'day_of_week', 'is_night', 'is_weekend',
    'avg_transaction_amount', 'amount_deviation', 'refund_rate',
    'merchant_count', 'device_count', 'instrument_count',
    'device_account_count', 'ip_account_count', 'instrument_account_count',
    'network_size', 'network_density', 'node_degree', 'network_growth_rate'
]


def get_model():
    global _model, _explainer, _feature_names
    if _model is not None and _explainer is not None:
        return _model, _explainer, _feature_names

    model_candidates = [
        '/app/model_artifacts/v1/model_2.json',
        '/app/model_artifacts/model_2.json',
        os.path.join(os.getcwd(), 'model_artifacts', 'v1', 'model_2.json'),
        os.path.join(os.getcwd(), 'model_artifacts', 'model_2.json'),
        os.path.join(os.getcwd(), '..', '..', 'model_artifacts', 'v1', 'model_2.json'),
        os.path.join(os.getcwd(), '..', '..', 'model_artifacts', 'model_2.json'),
        os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'model_artifacts', 'v1', 'model_2.json'),
    ]
    model_path = next((p for p in model_candidates if os.path.exists(p)), None)

    names_candidates = [
        '/app/model_artifacts/v1/feature_names.json',
        os.path.join(os.getcwd(), 'model_artifacts', 'v1', 'feature_names.json'),
        os.path.join(os.getcwd(), '..', '..', 'model_artifacts', 'v1', 'feature_names.json'),
        os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'model_artifacts', 'v1', 'feature_names.json'),
    ]
    names_path = next((p for p in names_candidates if os.path.exists(p)), None)

    if not model_path:
        logger.error("model_artifact_not_found", searched_paths=model_candidates)
        return None, None, None

    try:
        _model = xgb.XGBClassifier()
        _model._estimator_type = "classifier"
        _model.load_model(model_path)

        if names_path:
            with open(names_path, 'r') as f:
                f_data = json.load(f)
                _feature_names = f_data.get('all_features', EXPECTED_28_FEATURES)
        else:
            _feature_names = EXPECTED_28_FEATURES

        import shap
        _explainer = shap.TreeExplainer(_model, feature_perturbation='tree_path_dependent', model_output='raw')
        logger.info("loaded_risk_model_and_explainer", model_path=model_path, num_features=len(_feature_names))
    except Exception as e:
        logger.error("failed_loading_risk_model", error=str(e), model_path=model_path)
        _model = None
        _explainer = None

    return _model, _explainer, _feature_names


async def extract_features_for_transaction(transaction, db: AsyncSession, feature_names: list[str]) -> np.ndarray:
    t0 = transaction.occurred_at
    cid = transaction.customer_id

    # 1. Fetch customer transaction history up to t0
    q_tx = text("""
        SELECT transaction_id, customer_id, merchant_id, device_id, instrument_id, ip_id,
               amount, currency, transaction_type, status, occurred_at
        FROM transactions
        WHERE customer_id = :cid AND occurred_at <= :t0
        ORDER BY occurred_at ASC
    """)
    res_tx = await db.execute(q_tx, {"cid": cid, "t0": t0})
    cust_tx_df = pd.DataFrame(res_tx.fetchall(), columns=res_tx.keys())

    # Fallback if empty or target missing
    if cust_tx_df.empty or str(transaction.transaction_id) not in cust_tx_df['transaction_id'].astype(str).values:
        target_row = {
            'transaction_id': transaction.transaction_id,
            'customer_id': transaction.customer_id,
            'merchant_id': transaction.merchant_id,
            'device_id': transaction.device_id,
            'instrument_id': transaction.instrument_id,
            'ip_id': transaction.ip_id,
            'amount': float(transaction.amount) if transaction.amount is not None else 0.0,
            'currency': transaction.currency or 'USD',
            'transaction_type': transaction.transaction_type or 'purchase',
            'status': transaction.status or 'completed',
            'occurred_at': t0
        }
        cust_tx_df = pd.concat([cust_tx_df, pd.DataFrame([target_row])], ignore_index=True)

    cust_tx_df['amount'] = cust_tx_df['amount'].astype(float)
    cust_tx_df['type'] = cust_tx_df['transaction_type']
    cust_tx_df['occurred_at'] = pd.to_datetime(cust_tx_df['occurred_at'], utc=True)

    # 2. Fetch customer account info
    q_cust = text("""
        SELECT customer_id, country, status, account_created_at
        FROM customers
        WHERE customer_id = :cid
    """)
    res_cust = await db.execute(q_cust, {"cid": cid})
    cust_df = pd.DataFrame(res_cust.fetchall(), columns=res_cust.keys())
    if not cust_df.empty:
        cust_df['account_created_at'] = pd.to_datetime(cust_df['account_created_at'], utc=True)
    else:
        cust_df = pd.DataFrame([{
            'customer_id': cid,
            'country': 'US',
            'status': 'active',
            'account_created_at': t0
        }])

    merged_df = cust_tx_df.merge(cust_df, on='customer_id', how='left')

    # Currency categorical encoding matching training
    merged_df['currency_encoded'] = pd.Categorical(merged_df['currency'], categories=CURRENCY_CATEGORIES).codes
    merged_df['currency_encoded'] = merged_df['currency_encoded'].replace(-1, 0)

    # Extract transaction, temporal, behavioral features
    df_tx = extract_transaction_features(merged_df)
    df_temp = extract_temporal_features(df_tx)
    df_behav = extract_behavioral_features(df_temp)

    # Filter to the single target transaction row
    target_mask = df_behav['transaction_id'].astype(str) == str(transaction.transaction_id)
    target_df = df_behav[target_mask].copy()
    if target_df.empty:
        target_df = df_behav.iloc[[-1]].copy()

    # 3. Extract graph features up to t0 (Semantic B: information up to and including T)
    q_rel = text("""
        SELECT source_type, source_id, relationship_type, target_type, target_id, first_seen_at
        FROM entity_relationships
        WHERE first_seen_at <= :t0
        ORDER BY first_seen_at ASC
    """)
    res_rel = await db.execute(q_rel, {"t0": t0})
    rel_df = pd.DataFrame(res_rel.fetchall(), columns=res_rel.keys())

    # Fallback to connected transactions if entity_relationships in Postgres is sparse
    if len(rel_df) < 10:
        q_tx_rels = text("""
            SELECT customer_id, device_id, ip_id, instrument_id, occurred_at
            FROM transactions
            WHERE occurred_at <= :t0
              AND (customer_id = :cid
                   OR (device_id IS NOT NULL AND device_id = :did)
                   OR (ip_id IS NOT NULL AND ip_id = :ipid)
                   OR (instrument_id IS NOT NULL AND instrument_id = :instid))
        """)
        res_sub = await db.execute(q_tx_rels, {
            "t0": t0,
            "cid": transaction.customer_id,
            "did": transaction.device_id,
            "ipid": transaction.ip_id,
            "instid": transaction.instrument_id
        })
        sub_tx = pd.DataFrame(res_sub.fetchall(), columns=res_sub.keys())
        records = []
        for pair_type, col in [('device', 'device_id'), ('ip', 'ip_id'), ('instrument', 'instrument_id')]:
            valid = sub_tx[['customer_id', col, 'occurred_at']].dropna()
            grouped = valid.groupby(['customer_id', col]).agg(
                first_seen_at=('occurred_at', 'min')
            ).reset_index()
            for r in grouped.itertuples(index=False):
                records.append({
                    'source_type': 'customer',
                    'source_id': str(r[0]),
                    'relationship_type': 'uses',
                    'target_type': pair_type,
                    'target_id': str(r[1]),
                    'first_seen_at': r[2]
                })
        rel_df = pd.DataFrame(records)

    gf_df = extract_graph_features(target_df, rel_df)

    # 4. Construct strictly ordered 28-feature array
    feature_row = gf_df.iloc[0]
    vector = []
    for fname in feature_names:
        val = feature_row.get(fname, 0.0)
        try:
            val = float(val)
        except (ValueError, TypeError):
            val = 0.0
        vector.append(val)

    X = np.array([vector], dtype=float)
    X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)

    if X.shape != (1, len(feature_names)):
        raise ValueError(f"Feature shape mismatch: expected (1, {len(feature_names)}), got {X.shape}")
    if not np.all(np.isfinite(X)):
        raise ValueError("Feature vector contains non-finite values")

    return X


@router.post("/score", response_model=RiskScoreResponse)
async def score_transaction(request: RiskScoreRequest, db: AsyncSession = Depends(get_db)):
    transaction = await transaction_repo.get_transaction(db, request.transaction_id)
    if not transaction:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="TRANSACTION_NOT_FOUND")

    model, explainer, feature_names = get_model()
    if model is None or explainer is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="MODEL_NOT_AVAILABLE: Model 2 artifact could not be loaded"
        )

    t_start = time.perf_counter()
    try:
        X = await extract_features_for_transaction(transaction, db, feature_names)
        risk_score = float(model.predict_proba(X)[0, 1])
        model_version = "xgb-graph-v1"
    except Exception as e:
        logger.error("inference_feature_extraction_failed", error=str(e), transaction_id=str(request.transaction_id))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"FEATURE_EXTRACTION_FAILED: {str(e)}"
        )

    latency_ms = int((time.perf_counter() - t_start) * 1000)

    settings = get_settings()
    thresholds = [float(x) for x in settings.RISK_TIER_THRESHOLDS.split(',')]

    if risk_score >= thresholds[2]:
        risk_tier = "CRITICAL"
        decision = "REJECT"
    elif risk_score >= thresholds[1]:
        risk_tier = "HIGH"
        decision = "ESCALATE"
    elif risk_score >= thresholds[0]:
        risk_tier = "MEDIUM"
        decision = "REVIEW"
    else:
        risk_tier = "LOW"
        decision = "APPROVE"

    prediction_data = {
        "transaction_id": request.transaction_id,
        "model_version": model_version,
        "risk_score": risk_score,
        "risk_tier": risk_tier,
        "prediction_latency_ms": latency_ms,
        "predicted_at": datetime.now(timezone.utc)
    }

    prediction = await risk_repo.create_prediction(db, prediction_data)

    # Cache feature vector for fast explanation retrieval
    _prediction_cache[str(prediction.prediction_id)] = (X, feature_names)
    if len(_prediction_cache) > 1000:
        oldest_key = next(iter(_prediction_cache))
        _prediction_cache.pop(oldest_key, None)

    return RiskScoreResponse(
        transaction_id=request.transaction_id,
        risk_score=risk_score,
        risk_tier=risk_tier,
        decision=decision,
        model_version=model_version
    )


@router.get("/predictions/{prediction_id}/explanation", response_model=RiskExplanationResponse)
async def get_explanation(prediction_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    prediction = await risk_repo.get_prediction(db, prediction_id)
    if not prediction:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="PREDICTION_NOT_FOUND")

    model, explainer, feature_names = get_model()
    if model is None or explainer is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="MODEL_NOT_AVAILABLE: Explainer could not be loaded"
        )

    # Retrieve cached feature vector or re-extract
    cache_entry = _prediction_cache.get(str(prediction_id))
    if cache_entry is not None:
        X, f_names = cache_entry
    else:
        transaction = await transaction_repo.get_transaction(db, prediction.transaction_id)
        if not transaction:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="TRANSACTION_NOT_FOUND")
        X = await extract_features_for_transaction(transaction, db, feature_names)
        f_names = feature_names

    try:
        shap_values = explainer.shap_values(X)
        vals = shap_values[0] if shap_values.ndim == 2 else shap_values

        features = []
        for idx, fname in enumerate(f_names):
            features.append(FeatureContribution(
                name=str(fname),
                value=float(X[0, idx]),
                contribution=float(vals[idx])
            ))

        # Sort by absolute contribution and take top 5
        features.sort(key=lambda x: abs(x.contribution), reverse=True)
        features = features[:5]
    except Exception as e:
        logger.error("explanation_computation_failed", error=str(e), prediction_id=str(prediction_id))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"SHAP_EXPLANATION_FAILED: {str(e)}"
        )

    return RiskExplanationResponse(
        prediction_id=prediction_id,
        risk_score=prediction.risk_score,
        features=features
    )
