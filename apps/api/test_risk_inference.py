import os
import json
import asyncio
import pytest
import numpy as np
import httpx
from decimal import Decimal
from sqlalchemy import text
from app.database import engine
from app.api.risk import get_model, EXPECTED_28_FEATURES, extract_features_for_transaction


async def get_test_client():
    candidates = [
        os.getenv("API_URL", "http://localhost:8000"),
        "http://api:8000",
        "http://localhost:8000"
    ]
    for url in candidates:
        try:
            async with httpx.AsyncClient(base_url=url, timeout=2.0) as client:
                r = await client.get("/health")
                if r.status_code == 200:
                    return httpx.AsyncClient(base_url=url, timeout=30.0)
        except Exception:
            pass
    return httpx.AsyncClient(base_url="http://localhost:8000", timeout=30.0)


def test_model_artifact_exists_and_loads():
    """A. Model loading: verify artifact existence and load integrity."""
    model, explainer, feature_names = get_model()
    assert model is not None, "Model 2 failed to load"
    assert explainer is not None, "TreeExplainer failed to load"
    assert feature_names is not None, "Feature names failed to load"
    assert len(feature_names) == 28


def test_feature_contract_and_order():
    """B. Feature contract: verify exact 28 features, ordering, finiteness."""
    model, explainer, feature_names = get_model()
    assert feature_names == EXPECTED_28_FEATURES, "Feature names do not match expected contract"
    assert len(feature_names) == 28

    dummy_x = np.ones((1, 28), dtype=float)
    assert dummy_x.shape == (1, 28)
    assert np.all(np.isfinite(dummy_x))

    prob = model.predict_proba(dummy_x)
    assert prob.shape == (1, 2)
    assert 0.0 <= prob[0, 1] <= 1.0


def test_feature_extraction_converts_decimal_and_is_finite():
    """B. Verify Decimal conversion and finite output on real DB transaction."""
    async def run():
        model, explainer, feature_names = get_model()
        async with engine.connect() as conn:
            res = await conn.execute(text("SELECT * FROM transactions LIMIT 1"))
            row = res.mappings().first()
            assert row is not None

            from types import SimpleNamespace
            tx_obj = SimpleNamespace(**dict(row))
            tx_obj.amount = Decimal(str(row['amount']))

            X = await extract_features_for_transaction(tx_obj, conn, feature_names)
            assert X.shape == (1, 28)
            assert np.all(np.isfinite(X))
            assert not np.any(np.isnan(X))
        await engine.dispose()

    asyncio.run(run())


def test_inference_determinism():
    """C. Inference: verify deterministic scoring and absence of random noise."""
    async def run():
        model, explainer, feature_names = get_model()
        async with engine.connect() as conn:
            res = await conn.execute(text("SELECT * FROM transactions LIMIT 1"))
            row = res.mappings().first()
            from types import SimpleNamespace
            tx_obj = SimpleNamespace(**dict(row))

            X1 = await extract_features_for_transaction(tx_obj, conn, feature_names)
            score1 = float(model.predict_proba(X1)[0, 1])

            X2 = await extract_features_for_transaction(tx_obj, conn, feature_names)
            score2 = float(model.predict_proba(X2)[0, 1])

            assert score1 == score2, "Model inference is non-deterministic!"
            assert 0.0 <= score1 <= 1.0
        await engine.dispose()

    asyncio.run(run())


def test_live_endpoint_scoring_and_persistence():
    """D. Real transaction scoring via HTTP and DB persistence verification."""
    async def run():
        async with engine.connect() as conn:
            res = await conn.execute(text("SELECT transaction_id FROM transactions LIMIT 1"))
            tx_id = str(res.fetchone()[0])
        await engine.dispose()

        client = await get_test_client()
        async with client:
            resp = await client.post("/api/v1/risk/score", json={"transaction_id": tx_id})
            assert resp.status_code == 200
            data = resp.json()

            assert data["transaction_id"] == tx_id
            assert data["model_version"] != "mock-v1.0"
            assert data["model_version"] == "xgb-graph-v1"
            assert 0.0 <= data["risk_score"] <= 1.0
            assert data["risk_tier"] in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
            assert data["decision"] in ["APPROVE", "REVIEW", "ESCALATE", "REJECT"]

        async with engine.connect() as conn:
            q = text("SELECT prediction_id, model_version, risk_score, risk_tier FROM risk_predictions WHERE transaction_id = :tid ORDER BY predicted_at DESC LIMIT 1")
            pred_row = (await conn.execute(q, {"tid": tx_id})).mappings().first()
            assert pred_row is not None
            assert pred_row["model_version"] == "xgb-graph-v1"
            assert np.isclose(pred_row["risk_score"], data["risk_score"])
        await engine.dispose()

    asyncio.run(run())


def test_live_endpoint_real_explanation():
    """E. Explanation endpoint: verify real SHAP contributions, no static mocks."""
    async def run():
        async with engine.connect() as conn:
            res = await conn.execute(text("SELECT prediction_id FROM risk_predictions WHERE model_version = 'xgb-graph-v1' ORDER BY predicted_at DESC LIMIT 1"))
            pred_id = str(res.fetchone()[0])
        await engine.dispose()

        client = await get_test_client()
        async with client:
            resp = await client.get(f"/api/v1/risk/predictions/{pred_id}/explanation")
            assert resp.status_code == 200
            data = resp.json()

            assert data["prediction_id"] == pred_id
            features = data["features"]
            assert len(features) > 0

            # Verify not hardcoded mock
            mock_triplet = [
                (f["name"], f["value"], f["contribution"]) for f in features
                if (f["name"] == "network_density" and np.isclose(f["value"], 0.85))
            ]
            assert len(mock_triplet) == 0, "Hardcoded mock explanation was returned!"

            for f in features:
                assert f["name"] in EXPECTED_28_FEATURES
                assert np.isfinite(f["value"])
                assert np.isfinite(f["contribution"])

    asyncio.run(run())
