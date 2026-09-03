import uuid
import json
import pytest
import numpy as np
from datetime import datetime, timedelta, timezone

from anomaly_detector import TemporalAnomalyDetector
from worker import extract_features_and_baselines, parse_datetime


def test_1_z_score_calculation():
    detector = TemporalAnomalyDetector()
    z = detector._compute_z_score(observed=10.0, mean=5.0, std=2.0)
    assert np.isclose(z, 2.5)


def test_2_zero_std_handling():
    detector = TemporalAnomalyDetector()
    # When observed equals mean and std is 0
    assert detector._compute_z_score(observed=5.0, mean=5.0, std=0.0) == 0.0
    # When observed differs from mean and std is 0
    assert detector._compute_z_score(observed=6.0, mean=5.0, std=0.0) == 3.0
    # When std is NaN
    assert detector._compute_z_score(observed=6.0, mean=5.0, std=float('nan')) == 3.0


def test_3_normal_observation():
    detector = TemporalAnomalyDetector(z_score_threshold=2.5)
    now = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    current_stats = {
        'tx_count_5m': 1,
        'tx_count_1h': 1,
        'tx_count_24h': 1,
        'refund_rate': 0.0,
        'amount': 50.0,
        'avg_amount': 50.0
    }
    baseline_stats = {
        'mean_tx_5m': 0.1,
        'std_tx_5m': 0.5,
        'mean_tx_1h': 0.5,
        'std_tx_1h': 1.0,
        'mean_tx_24h': 1.0,
        'std_tx_24h': 1.0,
        'mean_refund_rate': 0.0,
        'std_refund_rate': 0.1,
        'mean_amount': 50.0,
        'std_amount': 10.0,
        'amount_sample_count': 5
    }
    anomalies = detector.detect_anomalies(
        entity_id=str(uuid.uuid4()),
        entity_type='customer',
        current_stats=current_stats,
        baseline_stats=baseline_stats,
        window_start=now - timedelta(hours=24),
        window_end=now
    )
    assert len(anomalies) == 0


def test_4_anomalous_observation():
    detector = TemporalAnomalyDetector(z_score_threshold=2.5)
    now = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    current_stats = {
        'tx_count_5m': 4,      # z = |4 - 0.1| / 0.5 = 7.8 >= 2.5
        'tx_count_1h': 5,      # z = |5 - 0.5| / 1.0 = 4.5 >= 2.5
        'tx_count_24h': 6,     # z = |6 - 1.0| / 1.0 = 5.0 >= 2.5
        'refund_rate': 0.5,    # z = |0.5 - 0.0| / 0.1 = 5.0 >= 2.5
        'amount': 500.0,       # z = |500 - 50| / 10 = 45.0 >= 2.5
        'avg_amount': 250.0
    }
    baseline_stats = {
        'mean_tx_5m': 0.1,
        'std_tx_5m': 0.5,
        'mean_tx_1h': 0.5,
        'std_tx_1h': 1.0,
        'mean_tx_24h': 1.0,
        'std_tx_24h': 1.0,
        'mean_refund_rate': 0.0,
        'std_refund_rate': 0.1,
        'mean_amount': 50.0,
        'std_amount': 10.0,
        'amount_sample_count': 5
    }
    anomalies = detector.detect_anomalies(
        entity_id=str(uuid.uuid4()),
        entity_type='customer',
        current_stats=current_stats,
        baseline_stats=baseline_stats,
        window_start=now - timedelta(hours=24),
        window_end=now
    )
    assert len(anomalies) >= 4
    types = [a['anomaly_type'] for a in anomalies]
    assert 'velocity_spike_5m' in types
    assert 'velocity_spike_1h' in types
    assert 'velocity_spike_24h' in types
    assert 'refund_spike' in types
    assert 'amount_anomaly' in types


def test_5_temporal_window_boundaries():
    T = datetime(2024, 1, 2, 12, 0, 0, tzinfo=timezone.utc)
    detector = TemporalAnomalyDetector()
    tx_list = [
        {'transaction_id': 'tx1', 'transaction_type': 'sale', 'amount': 10.0, 'occurred_at': T - timedelta(minutes=2)},
        {'transaction_id': 'tx2', 'transaction_type': 'sale', 'amount': 20.0, 'occurred_at': T - timedelta(minutes=15)},
        {'transaction_id': 'tx3', 'transaction_type': 'sale', 'amount': 30.0, 'occurred_at': T - timedelta(hours=2)},
        {'transaction_id': 'tx4', 'transaction_type': 'sale', 'amount': 40.0, 'occurred_at': T - timedelta(hours=25)},
    ]
    current_stats, baseline_stats = extract_features_and_baselines(tx_list, T, 10.0, detector)
    assert current_stats['tx_count_5m'] == 1      # tx1 only
    assert current_stats['tx_count_1h'] == 2      # tx1, tx2
    assert current_stats['tx_count_24h'] == 3     # tx1, tx2, tx3
    # tx4 is outside 24h window (in prior_txs)
    assert baseline_stats['mean_tx_24h'] > 0


def test_6_future_transactions_excluded():
    T = datetime(2024, 1, 2, 12, 0, 0, tzinfo=timezone.utc)
    detector = TemporalAnomalyDetector()
    # If a future transaction somehow slipped into tx_list
    tx_list = [
        {'transaction_id': 'tx1', 'transaction_type': 'sale', 'amount': 10.0, 'occurred_at': T - timedelta(minutes=1)},
        {'transaction_id': 'future_tx', 'transaction_type': 'sale', 'amount': 100.0, 'occurred_at': T + timedelta(minutes=5)}
    ]
    current_stats, _ = extract_features_and_baselines(tx_list, T, 10.0, detector)
    # The 5m, 1h, 24h counts must strictly exclude future_tx
    assert current_stats['tx_count_5m'] == 1
    assert current_stats['tx_count_1h'] == 1
    assert current_stats['tx_count_24h'] == 1


def test_7_current_event_semantics():
    T = datetime(2024, 1, 2, 12, 0, 0, tzinfo=timezone.utc)
    detector = TemporalAnomalyDetector()
    tx_list = [
        {'transaction_id': 'current_tx', 'transaction_type': 'sale', 'amount': 75.0, 'occurred_at': T}
    ]
    current_stats, _ = extract_features_and_baselines(tx_list, T, 75.0, detector)
    # Current event is present at time T and included in rolling windows
    assert current_stats['tx_count_5m'] == 1
    assert current_stats['tx_count_1h'] == 1
    assert current_stats['tx_count_24h'] == 1
    assert current_stats['amount'] == 75.0


def test_8_malformed_event_handling():
    # Invalid ISO format
    with pytest.raises(Exception):
        parse_datetime("invalid-datetime-string")
    
    # Valid ISO format with Z
    dt = parse_datetime("2024-01-01T10:00:00Z")
    assert dt.year == 2024
    assert dt.tzinfo == timezone.utc


def test_9_event_id_extraction():
    event1 = {"transaction_id": "tx-123", "customer_id": "c-1", "amount": 100}
    event2 = {"id": "tx-456", "customer_id": "c-2", "amount": 200}
    
    id1 = event1.get("transaction_id") or event1.get("id")
    id2 = event2.get("transaction_id") or event2.get("id")
    
    assert id1 == "tx-123"
    assert id2 == "tx-456"


def test_10_anomaly_record_construction():
    detector = TemporalAnomalyDetector(z_score_threshold=2.5)
    now = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    cust_id = str(uuid.uuid4())
    current_stats = {'tx_count_5m': 5}
    baseline_stats = {'mean_tx_5m': 0.1, 'std_tx_5m': 0.5}

    anomalies = detector.detect_anomalies(
        entity_id=cust_id,
        entity_type='customer',
        current_stats=current_stats,
        baseline_stats=baseline_stats,
        window_start=now - timedelta(hours=24),
        window_end=now
    )
    assert len(anomalies) == 1
    rec = anomalies[0]
    expected_keys = {
        'anomaly_id', 'entity_type', 'entity_id', 'anomaly_type',
        'baseline_value', 'observed_value', 'anomaly_score',
        'window_start', 'window_end', 'detected_at'
    }
    assert set(rec.keys()) == expected_keys
    assert isinstance(rec['anomaly_id'], uuid.UUID)
    assert isinstance(rec['entity_id'], uuid.UUID)
    assert np.isfinite(rec['anomaly_score'])


def test_11_deterministic_deduplication():
    detector = TemporalAnomalyDetector()
    cust_id = str(uuid.uuid4())
    T = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    
    id1 = detector.generate_deterministic_anomaly_id('customer', cust_id, 'velocity_spike_5m', T)
    id2 = detector.generate_deterministic_anomaly_id('customer', cust_id, 'velocity_spike_5m', T)
    assert id1 == id2, "Anomaly IDs for identical events must be deterministic!"

    # Different anomaly type or different window_end yields different ID
    id3 = detector.generate_deterministic_anomaly_id('customer', cust_id, 'velocity_spike_1h', T)
    assert id1 != id3
    id4 = detector.generate_deterministic_anomaly_id('customer', cust_id, 'velocity_spike_5m', T + timedelta(seconds=1))
    assert id1 != id4


def test_12_kafka_output_payload_construction():
    anom_id = uuid.uuid4()
    cust_id = uuid.uuid4()
    now = datetime.now(timezone.utc)
    
    update_payload = {
        "id": str(uuid.uuid4()),
        "event_id": str(uuid.uuid4()),
        "transaction_id": "tx-999",
        "customer_id": str(cust_id),
        "entity_type": "customer",
        "entity_id": str(cust_id),
        "anomaly_type": "velocity_spike_5m",
        "anomaly_types": ["velocity_spike_5m"],
        "anomaly_score": 3.8,
        "temporal_risk_score": 0.76,
        "anomalies": [
            {
                "anomaly_id": str(anom_id),
                "anomaly_type": "velocity_spike_5m",
                "baseline_value": 0.1,
                "observed_value": 2.0,
                "anomaly_score": 3.8,
                "window_start": (now - timedelta(minutes=5)).isoformat(),
                "window_end": now.isoformat(),
                "detected_at": now.isoformat()
            }
        ],
        "detected_at": now.isoformat()
    }
    
    # Must serialize to valid JSON without error
    raw_json = json.dumps(update_payload)
    parsed = json.loads(raw_json)
    assert parsed["transaction_id"] == "tx-999"
    assert parsed["temporal_risk_score"] == 0.76
    assert parsed["id"] is not None
    assert len(parsed["anomalies"]) == 1
