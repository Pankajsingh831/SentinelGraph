import uuid
import pytest
import numpy as np
from datetime import datetime, timedelta, timezone

from evidence_generator import EvidenceGenerator
from worker import compute_overall_risk, parse_datetime


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
