import sqlite3
import os
import sys
import uuid
import pytest
import numpy as np
from datetime import datetime, timedelta, timezone
from sqlalchemy import create_engine, text

# Add services/case-worker to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'services', 'case-worker')))

from evidence_generator import EvidenceGenerator
from worker import (
    compute_overall_risk,
    parse_datetime,
    get_transaction_risk,
    get_trigger_transaction_entities
)

sqlite3.register_adapter(uuid.UUID, lambda u: str(u))


def test_1_risk_aggregation_weights():
    # Weights: 0.50 * tx + 0.30 * net + 0.20 * temp
    score, tier = compute_overall_risk(tx_risk=1.0, net_risk=0.0, temp_risk=0.0)
    assert np.isclose(score, 0.50)
    assert tier == "MEDIUM"

    score, tier = compute_overall_risk(tx_risk=0.8, net_risk=0.6, temp_risk=0.5)
    # 0.50*0.8 + 0.30*0.6 + 0.20*0.5 = 0.40 + 0.18 + 0.10 = 0.68
    assert np.isclose(score, 0.68)
    assert tier == "HIGH"


def test_2_score_clamping():
    # Values above 1.0 clamped to 1.0
    score, tier = compute_overall_risk(tx_risk=1.5, net_risk=1.0, temp_risk=1.0)
    assert score == 1.0
    assert tier == "CRITICAL"

    # Negative values clamped to 0.0
    score, tier = compute_overall_risk(tx_risk=-0.5, net_risk=0.0, temp_risk=0.0)
    assert score == 0.0
    assert tier == "LOW"


def test_3_risk_tier_classifications():
    # Thresholds: LOW (<0.30), MEDIUM (0.30-0.60), HIGH (0.60-0.80), CRITICAL (>=0.80)
    s_low, t_low = compute_overall_risk(0.2, 0.2, 0.2)   # 0.20
    assert t_low == "LOW"

    s_med, t_med = compute_overall_risk(0.4, 0.4, 0.4)   # 0.40
    assert t_med == "MEDIUM"

    s_high, t_high = compute_overall_risk(0.7, 0.7, 0.7) # 0.70
    assert t_high == "HIGH"

    s_crit, t_crit = compute_overall_risk(0.9, 0.9, 0.9) # 0.90
    assert t_crit == "CRITICAL"


def test_4_missing_signals_handling():
    # Missing signals default to 0.0 without crash
    score, tier = compute_overall_risk(0.0, 0.0, 0.0)
    assert score == 0.0
    assert tier == "LOW"

    # Only temporal signal present
    score, tier = compute_overall_risk(0.0, 0.0, 1.0) # 0.20
    assert score == 0.20
    assert tier == "LOW"


def test_5_evidence_generation_velocity_rubrics():
    gen = EvidenceGenerator()
    case_id = uuid.uuid4()
    cust_id = uuid.uuid4()

    # Extreme velocity (CRITICAL >= 5.0x)
    anoms_crit = [{
        'anomaly_type': 'velocity_spike_5m',
        'observed_value': 30.0,
        'baseline_value': 1.0,
        'anomaly_score': 29.0
    }]
    ev_crit = gen.generate_evidence(case_id, temporal_anomalies=anoms_crit, entity_id=cust_id)
    assert len(ev_crit) == 1
    assert ev_crit[0]['severity'] == 'CRITICAL'
    assert 'Transaction velocity 30.0x above baseline' in ev_crit[0]['description']

    # High velocity (HIGH >= 3.0x)
    anoms_high = [{
        'anomaly_type': 'velocity_spike_1h',
        'observed_value': 3.5,
        'baseline_value': 1.0,
        'anomaly_score': 2.5
    }]
    ev_high = gen.generate_evidence(case_id, temporal_anomalies=anoms_high, entity_id=cust_id)
    assert len(ev_high) == 1
    assert ev_high[0]['severity'] == 'HIGH'

    # Moderate velocity (MEDIUM >= 2.0x)
    anoms_med = [{
        'anomaly_type': 'velocity_spike_24h',
        'observed_value': 2.2,
        'baseline_value': 1.0,
        'anomaly_score': 1.2
    }]
    ev_med = gen.generate_evidence(case_id, temporal_anomalies=anoms_med, entity_id=cust_id)
    assert len(ev_med) == 1
    assert ev_med[0]['severity'] == 'MEDIUM'


def test_6_evidence_generation_refund_rubrics():
    gen = EvidenceGenerator()
    case_id = uuid.uuid4()
    cust_id = uuid.uuid4()

    anoms = [{
        'anomaly_type': 'refund_spike',
        'observed_value': 0.60,
        'baseline_value': 0.05,
        'anomaly_score': 5.5
    }]
    ev = gen.generate_evidence(case_id, temporal_anomalies=anoms, entity_id=cust_id)
    assert len(ev) == 1
    assert ev[0]['severity'] == 'CRITICAL'
    assert 'Extreme refund rate: 60.0%' in ev[0]['description']


def test_7_evidence_generation_device_and_ip_sharing():
    gen = EvidenceGenerator()
    case_id = uuid.uuid4()
    cust_id = uuid.uuid4()

    graph_stats = {
        'device_account_count': 6,
        'ip_account_count': 12,
        'network_growth': 5
    }
    ev = gen.generate_evidence(case_id, graph_stats=graph_stats, entity_id=cust_id)
    assert len(ev) == 3
    types = [e['evidence_type'] for e in ev]
    assert 'device_sharing' in types
    assert 'ip_sharing' in types
    assert 'network_growth' in types

    dev_ev = next(e for e in ev if e['evidence_type'] == 'device_sharing')
    assert dev_ev['severity'] == 'HIGH'
    assert 'High device sharing: 6 accounts on single device' in dev_ev['description']

    ip_ev = next(e for e in ev if e['evidence_type'] == 'ip_sharing')
    assert ip_ev['severity'] == 'CRITICAL'
    assert 'Extreme IP sharing: 12 accounts on single IP' in ip_ev['description']


def test_8_evidence_generation_shap_features():
    gen = EvidenceGenerator()
    case_id = uuid.uuid4()
    cust_id = uuid.uuid4()

    shap_feats = [
        {'name': 'transaction_count_5m', 'contribution': 0.25, 'value': 30.0},
        {'name': 'network_density', 'contribution': 0.08, 'value': 0.75}
    ]
    ev = gen.generate_evidence(case_id, shap_features=shap_feats, entity_id=cust_id)
    assert len(ev) == 2
    top_ev = next(e for e in ev if e['evidence_data']['feature_name'] == 'transaction_count_5m')
    assert top_ev['severity'] == 'HIGH'
    assert 'Top risk factor: transaction_count_5m' in top_ev['description']


def test_9_deterministic_evidence_id_idempotency():
    gen = EvidenceGenerator()
    case_id = uuid.uuid4()
    cust_id = uuid.uuid4()

    id1 = gen.generate_deterministic_evidence_id(case_id, 'velocity', cust_id, "spike:30:1")
    id2 = gen.generate_deterministic_evidence_id(case_id, 'velocity', cust_id, "spike:30:1")
    assert id1 == id2, "Evidence IDs for same parameters must be identical!"

    id3 = gen.generate_deterministic_evidence_id(case_id, 'velocity', cust_id, "spike:10:1")
    assert id1 != id3


def test_10_datetime_parsing():
    dt1 = parse_datetime("2024-01-21T17:04:55Z")
    assert dt1.tzinfo == timezone.utc
    assert dt1.year == 2024

    dt2 = parse_datetime("2024-01-21T17:04:55.123456+00:00")
    assert dt2.tzinfo == timezone.utc
    assert dt2.microsecond == 123456

    dt3 = parse_datetime(None)
    assert dt3.tzinfo == timezone.utc


def test_11_evidence_record_structure_conformance():
    gen = EvidenceGenerator()
    case_id = uuid.uuid4()
    cust_id = uuid.uuid4()
    anoms = [{
        'anomaly_type': 'velocity_spike_5m',
        'observed_value': 10.0,
        'baseline_value': 1.0,
        'anomaly_score': 9.0
    }]
    ev_list = gen.generate_evidence(case_id, temporal_anomalies=anoms, entity_id=cust_id)
    assert len(ev_list) == 1
    ev = ev_list[0]
    expected_fields = {
        'evidence_id', 'case_id', 'evidence_type', 'entity_type',
        'entity_id', 'description', 'severity', 'evidence_data', 'created_at'
    }
    assert set(ev.keys()) == expected_fields
    assert isinstance(ev['evidence_id'], uuid.UUID)
    assert isinstance(ev['case_id'], uuid.UUID)
    assert isinstance(ev['entity_id'], uuid.UUID)


@pytest.fixture
def db_conn():
    engine = create_engine("sqlite:///:memory:")
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE risk_predictions (
                prediction_id TEXT PRIMARY KEY,
                transaction_id TEXT NOT NULL,
                risk_score REAL NOT NULL,
                risk_tier TEXT NOT NULL,
                predicted_at TIMESTAMP NOT NULL
            );
        """))
        conn.execute(text("""
            CREATE TABLE transactions (
                transaction_id TEXT PRIMARY KEY,
                customer_id TEXT NOT NULL,
                merchant_id TEXT,
                device_id TEXT,
                instrument_id TEXT,
                ip_id TEXT,
                amount REAL,
                currency TEXT,
                transaction_type TEXT,
                status TEXT,
                occurred_at TIMESTAMP NOT NULL
            );
        """))
        conn.commit()
        yield conn


def test_12_no_cross_transaction_prediction_leakage(db_conn):
    """Test A: tx_a has no prediction; tx_b for same customer has prediction (0.9956).
    Event for tx_a must return tx_risk = 0.0 and NOT inherit tx_b's prediction.
    """
    cust_id = uuid.uuid4()
    tx_a = uuid.uuid4()
    tx_b = uuid.uuid4()
    now = datetime.now(timezone.utc)

    # Insert tx_b prediction
    db_conn.execute(text("""
        INSERT INTO risk_predictions (prediction_id, transaction_id, risk_score, risk_tier, predicted_at)
        VALUES (:pid, :tx, :score, :tier, :pred_at)
    """), {
        "pid": str(uuid.uuid4()),
        "tx": tx_b,
        "score": 0.9956,
        "tier": "CRITICAL",
        "pred_at": now - timedelta(minutes=5)
    })
    db_conn.commit()

    # Query for tx_a: must NOT inherit tx_b's prediction
    score = get_transaction_risk(db_conn, tx_a, now)
    assert score == 0.0, f"Expected 0.0, got {score}; tx_a leaked tx_b's prediction!"

    # Also check when event has no transaction_id (None): returns 0.0
    assert get_transaction_risk(db_conn, None, now) == 0.0

    # Overall risk aggregation with temporal risk = 1.0, tx_risk = 0.0
    overall_score, tier = compute_overall_risk(tx_risk=score, net_risk=0.0, temp_risk=1.0)
    assert np.isclose(overall_score, 0.20)
    assert tier == "LOW"


def test_13_exact_transaction_prediction_used(db_conn):
    """Test B: tx_a has prediction 0.80; tx_b for same customer has prediction 0.9956.
    Event for tx_a must use tx_a's exact prediction (0.80).
    """
    cust_id = uuid.uuid4()
    tx_a = uuid.uuid4()
    tx_b = uuid.uuid4()
    now = datetime.now(timezone.utc)

    db_conn.execute(text("""
        INSERT INTO risk_predictions (prediction_id, transaction_id, risk_score, risk_tier, predicted_at)
        VALUES (:pid, :tx, :score, :tier, :pred_at)
    """), [
        {
            "pid": str(uuid.uuid4()),
            "tx": tx_a,
            "score": 0.80,
            "tier": "HIGH",
            "pred_at": now - timedelta(minutes=2)
        },
        {
            "pid": str(uuid.uuid4()),
            "tx": tx_b,
            "score": 0.9956,
            "tier": "CRITICAL",
            "pred_at": now - timedelta(minutes=5)
        }
    ])
    db_conn.commit()

    score = get_transaction_risk(db_conn, tx_a, now)
    assert np.isclose(score, 0.80), f"Expected 0.80, got {score}"

    overall_score, tier = compute_overall_risk(tx_risk=score, net_risk=0.0, temp_risk=1.0)
    # 0.50*0.80 + 0.30*0.0 + 0.20*1.0 = 0.40 + 0.20 = 0.60
    assert np.isclose(overall_score, 0.60)
    assert tier == "HIGH"


def test_14_future_prediction_rejected(db_conn):
    """Test C: tx_a has prediction with predicted_at > event_time (future prediction).
    Must return tx_risk = 0.0 and NOT fall back to any other prediction.
    """
    cust_id = uuid.uuid4()
    tx_a = uuid.uuid4()
    tx_b = uuid.uuid4()
    event_time = datetime.now(timezone.utc)

    # tx_a prediction is 10 seconds in future
    # tx_b has older prediction
    db_conn.execute(text("""
        INSERT INTO risk_predictions (prediction_id, transaction_id, risk_score, risk_tier, predicted_at)
        VALUES (:pid, :tx, :score, :tier, :pred_at)
    """), [
        {
            "pid": str(uuid.uuid4()),
            "tx": tx_a,
            "score": 0.95,
            "tier": "CRITICAL",
            "pred_at": event_time + timedelta(seconds=10)
        },
        {
            "pid": str(uuid.uuid4()),
            "tx": tx_b,
            "score": 0.9956,
            "tier": "CRITICAL",
            "pred_at": event_time - timedelta(minutes=5)
        }
    ])
    db_conn.commit()

    score = get_transaction_risk(db_conn, tx_a, event_time)
    assert score == 0.0, f"Future prediction should be rejected, got {score}"


def test_15_case_entity_uses_exact_event_transaction(db_conn):
    """Test D: Customer has tx_a at T1 and tx_b at T2 (T2 > T1).
    When tx_id is provided, get_trigger_transaction_entities must return tx_a's row, not tx_b.
    When tx_id is None, it falls back to tx_b (latest transaction up to event_time).
    """
    cust_id = uuid.uuid4()
    tx_a = uuid.uuid4()
    tx_b = uuid.uuid4()
    t1 = datetime.now(timezone.utc) - timedelta(minutes=10)
    t2 = datetime.now(timezone.utc) - timedelta(minutes=2)
    event_time = datetime.now(timezone.utc)

    db_conn.execute(text("""
        INSERT INTO transactions (transaction_id, customer_id, merchant_id, device_id, instrument_id, ip_id, amount, currency, transaction_type, status, occurred_at)
        VALUES (:tx, :cust, :merch, :dev, :inst, :ip, :amt, 'USD', 'PAYMENT', 'COMPLETED', :occ)
    """), [
        {
            "tx": tx_a,
            "cust": cust_id,
            "merch": "merch_a",
            "dev": "dev_a",
            "inst": "inst_a",
            "ip": "ip_a",
            "amt": 50.0,
            "occ": t1
        },
        {
            "tx": tx_b,
            "cust": cust_id,
            "merch": "merch_b",
            "dev": "dev_b",
            "inst": "inst_b",
            "ip": "ip_b",
            "amt": 100.0,
            "occ": t2
        }
    ])
    db_conn.commit()

    # Case 1: tx_id is tx_a -> must return tx_a
    row_a = get_trigger_transaction_entities(db_conn, cust_id, tx_a, event_time)
    assert row_a is not None
    assert str(row_a[0]) == str(tx_a)
    assert row_a[1] == "merch_a"

    # Case 2: tx_id is None -> fallback to latest transaction up to event_time (tx_b)
    row_fallback = get_trigger_transaction_entities(db_conn, cust_id, None, event_time)
    assert row_fallback is not None
    assert str(row_fallback[0]) == str(tx_b)
    assert row_fallback[1] == "merch_b"
