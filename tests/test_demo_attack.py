import sqlite3
import decimal
import os
import sys
import subprocess
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
import pytest
from sqlalchemy import create_engine, text

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import simulator
from simulator.demo_attack import (
    generate_burst_transactions,
    json_serializer,
    compute_expected_risk,
    verify_case_for_attack_transaction,
    fetch_case_for_transaction_sync,
    fetch_case_entities_sync,
    fetch_case_evidence_sync,
    print_demo_summary,
    poll_pipeline_results,
    run_demo
)

sqlite3.register_adapter(uuid.UUID, lambda u: str(u))


def test_i_demo_attack_help_exits_successfully():
    """Test I: Verify python -m simulator.demo_attack --help exits with 0 and prints usage."""
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)

    cmd = [sys.executable, "-m", "simulator.demo_attack", "--help"]
    res = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True, env=env)

    assert res.returncode == 0, f"Command failed: {res.stderr}"
    assert "SentinelGraph Live Demo" in res.stdout
    assert "--transactions" in res.stdout
    assert "--amount" in res.stdout
    assert "--customer-id" in res.stdout
    assert "--api-url" in res.stdout
    assert "--dry-run" in res.stdout


def test_h_demo_attack_dry_run_no_mutation():
    """Test H: Verify python -m simulator.demo_attack --dry-run exits with 0 and writes no data."""
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)

    cmd = [sys.executable, "-m", "simulator.demo_attack", "--dry-run", "--transactions", "5"]
    res = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True, env=env)

    assert res.returncode == 0, f"Command failed: {res.stderr}"
    assert "DRY RUN" in res.stdout
    assert "Mode: Dry run - NO changes written to PostgreSQL or Kafka." in res.stdout


def test_a_card_testing_amounts_stay_within_range():
    """Test A: Card-testing warmup amounts stay within intended range ($1.50 - $4.50)."""
    dummy_entities = {
        "customer_id": uuid.uuid4(),
        "merchant_id": uuid.uuid4(),
        "device_id": uuid.uuid4(),
        "instrument_id": uuid.uuid4(),
        "ip_id": uuid.uuid4(),
    }
    txs = generate_burst_transactions(dummy_entities, count=25, attack_amount=4.98)
    assert len(txs) == 25
    warmup_txs = txs[:-1]
    for tx in warmup_txs:
        assert decimal.Decimal("1.50") <= tx["amount"] <= decimal.Decimal("4.50"), (
            f"Warmup amount {tx['amount']} outside card-testing range ($1.50 - $4.50)"
        )
    # The final attack transaction receives the explicit attack amount
    assert txs[-1]["amount"] == decimal.Decimal("4.98")


def test_b_approximately_25_warmup_transactions_generated():
    """Test B: Approximately 25 warmup/burst transactions are generated within roughly 60 seconds."""
    dummy_entities = {
        "customer_id": uuid.uuid4(),
        "merchant_id": uuid.uuid4(),
        "device_id": uuid.uuid4(),
        "instrument_id": uuid.uuid4(),
        "ip_id": uuid.uuid4(),
    }
    # Default count is 25
    txs = generate_burst_transactions(dummy_entities, window_seconds=60)
    assert len(txs) == 25
    warmup_count = len(txs) - 1
    assert warmup_count == 24  # 24 warmup + 1 attack = 25 total

    # Check window span is roughly 60 seconds
    duration = (txs[-1]["occurred_at"] - txs[0]["occurred_at"]).total_seconds()
    assert 50.0 <= duration <= 65.0


def test_c_final_attack_transaction_is_498_or_configured():
    """Test C: Final attack transaction is $4.98 by default or explicit configured attack amount."""
    dummy_entities = {
        "customer_id": uuid.uuid4(),
        "merchant_id": uuid.uuid4(),
        "device_id": uuid.uuid4(),
        "instrument_id": uuid.uuid4(),
        "ip_id": uuid.uuid4(),
    }
    # Default is $4.98
    txs_default = generate_burst_transactions(dummy_entities)
    assert txs_default[-1]["amount"] == decimal.Decimal("4.98")

    # Explicit configured amount
    txs_custom = generate_burst_transactions(dummy_entities, attack_amount=3.75)
    assert txs_custom[-1]["amount"] == decimal.Decimal("3.75")
    txs_custom_large = generate_burst_transactions(dummy_entities, attack_amount=1250.0)
    assert txs_custom_large[-1]["amount"] == decimal.Decimal("1250.00")


def test_d_transactions_are_ordered_and_timezone_aware():
    """Test D: All transaction timestamps are timezone-aware UTC and chronologically ordered."""
    dummy_entities = {
        "customer_id": uuid.uuid4(),
        "merchant_id": uuid.uuid4(),
        "device_id": uuid.uuid4(),
        "instrument_id": uuid.uuid4(),
        "ip_id": uuid.uuid4(),
    }
    txs = generate_burst_transactions(dummy_entities, count=25, window_seconds=60)

    for tx in txs:
        assert tx["occurred_at"].tzinfo is not None, "occurred_at is naive"
        assert tx["created_at"].tzinfo is not None, "created_at is naive"

    # Verify chronological ordering
    for i in range(len(txs) - 1):
        assert txs[i]["occurred_at"] <= txs[i + 1]["occurred_at"]


def test_generated_transaction_payload_fields():
    """Verify generated transactions contain all required schema fields and correct types."""
    dummy_entities = {
        "customer_id": uuid.uuid4(),
        "merchant_id": uuid.uuid4(),
        "device_id": uuid.uuid4(),
        "instrument_id": uuid.uuid4(),
        "ip_id": uuid.uuid4(),
    }
    count = 10
    attack_amount = 4.98
    txs = generate_burst_transactions(dummy_entities, count=count, attack_amount=attack_amount)

    assert len(txs) == count
    required_fields = [
        "transaction_id", "customer_id", "merchant_id", "device_id",
        "instrument_id", "ip_id", "amount", "currency", "transaction_type",
        "status", "occurred_at", "created_at"
    ]

    for tx in txs:
        for f in required_fields:
            assert f in tx, f"Missing required field: {f}"
        assert isinstance(tx["transaction_id"], uuid.UUID)
        assert tx["customer_id"] == dummy_entities["customer_id"]
        assert tx["merchant_id"] == dummy_entities["merchant_id"]
        assert tx["currency"] in ("USD", "INR")
        assert tx["transaction_type"] == "purchase"
        assert tx["status"] == "completed"
        assert isinstance(tx["amount"], decimal.Decimal)


def test_transaction_uuids_are_unique():
    """Verify generated transaction IDs are strictly unique."""
    dummy_entities = {
        "customer_id": uuid.uuid4(),
        "merchant_id": uuid.uuid4(),
        "device_id": uuid.uuid4(),
        "instrument_id": uuid.uuid4(),
        "ip_id": uuid.uuid4(),
    }
    txs = generate_burst_transactions(dummy_entities, count=50)
    tx_ids = [tx["transaction_id"] for tx in txs]
    assert len(set(tx_ids)) == 50


def test_json_serializer_handles_types():
    """Verify json_serializer handles UUID, datetime, and Decimal."""
    uid = uuid.uuid4()
    now = datetime.now(timezone.utc)
    dec = decimal.Decimal("123.45")

    assert json_serializer(uid) == str(uid)
    assert json_serializer(now) == now.isoformat()
    assert json_serializer(dec) == 123.45

    with pytest.raises(TypeError):
        json_serializer(object())


@pytest.fixture
def case_test_db():
    engine = create_engine("sqlite:///:memory:")
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE risk_cases (
                case_id TEXT PRIMARY KEY,
                primary_entity_type TEXT NOT NULL,
                primary_entity_id TEXT NOT NULL,
                transaction_risk_score REAL,
                network_risk_score REAL,
                temporal_risk_score REAL,
                overall_risk_score REAL NOT NULL,
                risk_tier TEXT NOT NULL,
                status TEXT NOT NULL,
                case_reason TEXT,
                created_at TIMESTAMP NOT NULL,
                updated_at TIMESTAMP,
                resolved_at TIMESTAMP
            );
        """))
        conn.execute(text("""
            CREATE TABLE case_entities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                case_id TEXT NOT NULL,
                entity_type TEXT NOT NULL,
                entity_id TEXT NOT NULL,
                role TEXT,
                added_at TIMESTAMP NOT NULL
            );
        """))
        conn.execute(text("""
            CREATE TABLE case_evidence (
                evidence_id TEXT PRIMARY KEY,
                case_id TEXT NOT NULL,
                evidence_type TEXT NOT NULL,
                entity_type TEXT,
                entity_id TEXT,
                description TEXT,
                severity TEXT,
                created_at TIMESTAMP
            );
        """))
        conn.commit()
        yield conn


def test_g_expected_aggregate_calculation_rubrics():
    """Test G: Verify independently calculated expected case score and tier rubrics."""
    # 1. Standard weights: 0.50*tx + 0.30*net + 0.20*temp
    # 0.50*0.8 + 0.30*0.6 + 0.20*0.5 = 0.40 + 0.18 + 0.10 = 0.68 -> HIGH
    score, tier = compute_expected_risk(0.8, 0.6, 0.5)
    assert pytest.approx(score, 0.0001) == 0.68
    assert tier == "HIGH"

    # 2. Tier boundaries
    # LOW (< 0.30)
    s_low, t_low = compute_expected_risk(0.2, 0.2, 0.2)
    assert pytest.approx(s_low, 0.0001) == 0.20
    assert t_low == "LOW"

    # MEDIUM (0.30 <= score < 0.60)
    s_med, t_med = compute_expected_risk(0.4, 0.4, 0.4)
    assert pytest.approx(s_med, 0.0001) == 0.40
    assert t_med == "MEDIUM"

    # HIGH (0.60 <= score < 0.80)
    s_high, t_high = compute_expected_risk(0.7, 0.7, 0.7)
    assert pytest.approx(s_high, 0.0001) == 0.70
    assert t_high == "HIGH"

    # CRITICAL (>= 0.80)
    s_crit, t_crit = compute_expected_risk(0.9, 0.9, 0.9)
    assert pytest.approx(s_crit, 0.0001) == 0.90
    assert t_crit == "CRITICAL"

    # 3. Clamping
    s_clamp_high, t_clamp_high = compute_expected_risk(1.5, 1.2, 1.0)
    assert s_clamp_high == 1.0
    assert t_clamp_high == "CRITICAL"

    s_clamp_low, t_clamp_low = compute_expected_risk(-0.5, 0.0, 0.0)
    assert s_clamp_low == 0.0
    assert t_clamp_low == "LOW"


def test_e_exact_attack_transaction_case_is_selected(case_test_db):
    """Test E: The demo correctly identifies the case associated with the exact attack transaction."""
    cust_id = uuid.uuid4()
    attack_tx_id = uuid.uuid4()
    older_tx_id = uuid.uuid4()

    case_attack_id = uuid.uuid4()
    case_older_id = uuid.uuid4()

    t_older = datetime(2026, 9, 1, 10, 0, 0, tzinfo=timezone.utc)
    t_attack = datetime(2026, 9, 4, 12, 0, 0, tzinfo=timezone.utc)

    # Insert older case (for older_tx_id)
    case_test_db.execute(text("""
        INSERT INTO risk_cases (case_id, primary_entity_type, primary_entity_id, transaction_risk_score,
                                network_risk_score, temporal_risk_score, overall_risk_score, risk_tier,
                                status, case_reason, created_at)
        VALUES (:cid, 'customer', :cust, 0.5, 0.2, 0.3, 0.37, 'MEDIUM', 'closed', 'Old activity', :dt);
    """), {"cid": case_older_id, "cust": cust_id, "dt": t_older})

    case_test_db.execute(text("""
        INSERT INTO case_entities (case_id, entity_type, entity_id, role, added_at)
        VALUES (:cid, 'transaction', :tx, 'trigger_transaction', :dt);
    """), {"cid": case_older_id, "tx": older_tx_id, "dt": t_older})

    # Insert attack case (for attack_tx_id)
    case_test_db.execute(text("""
        INSERT INTO risk_cases (case_id, primary_entity_type, primary_entity_id, transaction_risk_score,
                                network_risk_score, temporal_risk_score, overall_risk_score, risk_tier,
                                status, case_reason, created_at)
        VALUES (:cid, 'customer', :cust, 0.85, 0.40, 0.90, 0.725, 'HIGH', 'open', 'Velocity burst', :dt);
    """), {"cid": case_attack_id, "cust": cust_id, "dt": t_attack})

    case_test_db.execute(text("""
        INSERT INTO case_entities (case_id, entity_type, entity_id, role, added_at)
        VALUES (:cid, 'transaction', :tx, 'trigger_transaction', :dt);
    """), {"cid": case_attack_id, "tx": attack_tx_id, "dt": t_attack})

    ev_id = uuid.uuid4()
    case_test_db.execute(text("""
        INSERT INTO case_evidence (evidence_id, case_id, evidence_type, severity, created_at)
        VALUES (:eid, :cid, 'velocity_spike', 'HIGH', :dt);
    """), {"eid": ev_id, "cid": case_attack_id, "dt": t_attack})
    case_test_db.commit()

    # Query for exact attack transaction
    case_res = fetch_case_for_transaction_sync(case_test_db, attack_tx_id)
    assert case_res is not None
    assert case_res["case_id"] == str(case_attack_id)
    assert case_res["customer_id"] == str(cust_id)
    assert case_res["overall_risk"] == 0.725
    assert case_res["tier"] == "HIGH"
    assert case_res["status"] == "open"
    assert case_res["associated_transaction_id"] == str(attack_tx_id)

    # Verification passes
    entities = fetch_case_entities_sync(case_test_db, case_attack_id)
    evidences = fetch_case_evidence_sync(case_test_db, case_attack_id)
    verif = verify_case_for_attack_transaction(
        case_record=case_res,
        case_entities=entities,
        evidence_records=evidences,
        expected_customer_id=cust_id,
        attack_tx_id=attack_tx_id
    )
    assert verif["verified"] is True
    assert verif["error"] is None


def test_f_unrelated_customer_case_not_selected(case_test_db):
    """Test F: Unrelated newer or older customer case is NOT selected for the attack transaction."""
    cust_id = uuid.uuid4()
    attack_tx_id = uuid.uuid4()
    other_tx_id = uuid.uuid4()
    unrelated_case_id = uuid.uuid4()
    t_now = datetime.now(timezone.utc)

    # Customer has a recent case, but it's linked to other_tx_id, NOT attack_tx_id
    case_test_db.execute(text("""
        INSERT INTO risk_cases (case_id, primary_entity_type, primary_entity_id, transaction_risk_score,
                                network_risk_score, temporal_risk_score, overall_risk_score, risk_tier,
                                status, case_reason, created_at)
        VALUES (:cid, 'customer', :cust, 0.9, 0.8, 0.7, 0.83, 'CRITICAL', 'open', 'Unrelated case', :dt);
    """), {"cid": unrelated_case_id, "cust": cust_id, "dt": t_now})

    case_test_db.execute(text("""
        INSERT INTO case_entities (case_id, entity_type, entity_id, role, added_at)
        VALUES (:cid, 'transaction', :tx, 'trigger_transaction', :dt);
    """), {"cid": unrelated_case_id, "tx": other_tx_id, "dt": t_now})
    case_test_db.commit()

    # Query for attack_tx_id: must return None (unrelated case must NEVER be selected)
    case_res = fetch_case_for_transaction_sync(case_test_db, attack_tx_id)
    assert case_res is None, f"Expected None for unlinked attack_tx_id, but got case {case_res}"


def test_no_attack_case_reported_as_not_created(capsys):
    """Test C: If no case exists for the attack transaction, report 'CASE FOR ATTACK TRANSACTION: NOT CREATED'."""
    cust_id = uuid.uuid4()
    attack_tx_id = uuid.uuid4()
    now = datetime.now(timezone.utc)

    transactions = [
        {"transaction_id": uuid.uuid4(), "occurred_at": now - timedelta(seconds=10), "amount": 50.0},
        {"transaction_id": attack_tx_id, "occurred_at": now, "amount": 1250.0}
    ]
    attack_tx = transactions[-1]

    api_result = {
        "risk_score": 0.05,
        "risk_tier": "LOW",
        "decision": "APPROVE",
        "model_version": "xgb-graph-v1"
    }

    # Pipeline result with NO attack case, but with an unrelated existing customer case
    unrelated_case_id = uuid.uuid4()
    pipeline_result = {
        "anomalies_count": 2,
        "temporal_risk": 0.20,
        "network_risk": 0.10,
        "network_size": 4,
        "prediction": {"risk_score": 0.05, "risk_tier": "LOW"},
        "case": None,  # NOT CREATED
        "evidence_count": 0,
        "case_reason": None,
        "is_case_verified": False,
        "latest_customer_case": {
            "case_id": str(unrelated_case_id),
            "overall_risk": 0.75,
            "tier": "HIGH",
            "status": "closed",
            "created_at": now - timedelta(days=2)
        }
    }

    print_demo_summary(cust_id, transactions, attack_tx, api_result, pipeline_result)
    captured = capsys.readouterr().out

    # Assertions
    assert "CASE FOR ATTACK TRANSACTION: NOT CREATED" in captured
    assert "ML risk: 0.0500" in captured
    assert "temporal risk: 0.2000" in captured
    assert "current graph risk: 0.1000" in captured
    assert "expected aggregate risk: 0.0950 (LOW)" in captured
    assert "Separate latest customer case (unrelated to this attack transaction):" in captured
    assert str(unrelated_case_id) in captured


def test_case_verification_catches_tampering_or_mismatch():
    """Test verification helper rejects customer mismatch, missing tx, or mismatched evidence."""
    cust_id = uuid.uuid4()
    wrong_cust_id = uuid.uuid4()
    attack_tx_id = uuid.uuid4()
    case_id = uuid.uuid4()

    valid_case = {
        "case_id": str(case_id),
        "customer_id": str(cust_id),
        "overall_risk": 0.75,
        "tier": "HIGH",
        "status": "open",
        "transaction_risk": 0.90,
        "network_risk": 0.60,
        "temporal_risk": 0.60
    }
    valid_entities = [{"entity_type": "transaction", "entity_id": str(attack_tx_id), "role": "trigger_transaction"}]
    valid_evidence = [{"evidence_id": str(uuid.uuid4()), "case_id": str(case_id), "evidence_type": "velocity"}]

    # 1. Valid case passes
    v = verify_case_for_attack_transaction(valid_case, valid_entities, valid_evidence, cust_id, attack_tx_id)
    assert v["verified"] is True
    assert v["error"] is None

    # 2. Wrong customer ID fails
    v_wrong_cust = verify_case_for_attack_transaction(valid_case, valid_entities, valid_evidence, wrong_cust_id, attack_tx_id)
    assert v_wrong_cust["verified"] is False
    assert "Customer ID mismatch" in v_wrong_cust["error"]

    # 3. Missing attack transaction entity fails
    v_wrong_tx = verify_case_for_attack_transaction(valid_case, [], valid_evidence, cust_id, attack_tx_id)
    assert v_wrong_tx["verified"] is False
    assert "not found in case entities" in v_wrong_tx["error"]

    # 4. Evidence belonging to different case fails
    wrong_ev = [{"evidence_id": str(uuid.uuid4()), "case_id": str(uuid.uuid4()), "evidence_type": "velocity"}]
    v_wrong_ev = verify_case_for_attack_transaction(valid_case, valid_entities, wrong_ev, cust_id, attack_tx_id)
    assert v_wrong_ev["verified"] is False
    assert "belongs to case" in v_wrong_ev["error"]

    # 5. Empty evidence records fails
    v_empty_ev = verify_case_for_attack_transaction(valid_case, valid_entities, [], cust_id, attack_tx_id)
    assert v_empty_ev["verified"] is False
    assert "No evidence records" in v_empty_ev["error"]


def test_case_verification_risk_mismatch_rejected():
    """Verify that case with tampered or mismatched overall_risk is rejected."""
    cust_id = uuid.uuid4()
    attack_tx_id = uuid.uuid4()
    case_id = uuid.uuid4()

    tampered_risk_case = {
        "case_id": str(case_id),
        "customer_id": str(cust_id),
        "overall_risk": 0.95,  # Expected: 0.50*0.90 + 0.30*0.60 + 0.20*0.60 = 0.75
        "tier": "HIGH",
        "status": "open",
        "transaction_risk": 0.90,
        "network_risk": 0.60,
        "temporal_risk": 0.60
    }
    entities = [{"entity_type": "transaction", "entity_id": str(attack_tx_id), "role": "trigger_transaction"}]
    evidence = [{"evidence_id": str(uuid.uuid4()), "case_id": str(case_id), "evidence_type": "velocity"}]

    v = verify_case_for_attack_transaction(tampered_risk_case, entities, evidence, cust_id, attack_tx_id)
    assert v["verified"] is False
    assert "Risk score mismatch" in v["error"]


def test_case_verification_tier_mismatch_rejected():
    """Verify that case with mismatched risk tier is rejected."""
    cust_id = uuid.uuid4()
    attack_tx_id = uuid.uuid4()
    case_id = uuid.uuid4()

    # Aggregate is 0.75, which corresponds to HIGH, but tier is set to CRITICAL
    tampered_tier_case = {
        "case_id": str(case_id),
        "customer_id": str(cust_id),
        "overall_risk": 0.75,
        "tier": "CRITICAL",
        "status": "open",
        "transaction_risk": 0.90,
        "network_risk": 0.60,
        "temporal_risk": 0.60
    }
    entities = [{"entity_type": "transaction", "entity_id": str(attack_tx_id), "role": "trigger_transaction"}]
    evidence = [{"evidence_id": str(uuid.uuid4()), "case_id": str(case_id), "evidence_type": "velocity"}]

    v = verify_case_for_attack_transaction(tampered_tier_case, entities, evidence, cust_id, attack_tx_id)
    assert v["verified"] is False
    assert "Risk tier mismatch" in v["error"]


def test_case_verification_missing_risk_component_rejected():
    """Verify that case with missing risk components is rejected."""
    cust_id = uuid.uuid4()
    attack_tx_id = uuid.uuid4()
    case_id = uuid.uuid4()

    # Missing temporal_risk
    missing_comp_case = {
        "case_id": str(case_id),
        "customer_id": str(cust_id),
        "overall_risk": 0.75,
        "tier": "HIGH",
        "status": "open",
        "transaction_risk": 0.90,
        "network_risk": 0.60,
        "temporal_risk": None
    }
    entities = [{"entity_type": "transaction", "entity_id": str(attack_tx_id), "role": "trigger_transaction"}]
    evidence = [{"evidence_id": str(uuid.uuid4()), "case_id": str(case_id), "evidence_type": "velocity"}]

    v = verify_case_for_attack_transaction(missing_comp_case, entities, evidence, cust_id, attack_tx_id)
    assert v["verified"] is False
    assert "Missing persisted temporal_risk component" in v["error"]


def test_invalid_transaction_count_rejected():
    """Verify that CLI and run_demo reject --transactions < 2."""
    cmd = [sys.executable, "-m", "simulator.demo_attack", "--transactions", "1"]
    res = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True)
    assert res.returncode != 0
    assert "--transactions must be >= 2" in res.stderr

    import asyncio
    with pytest.raises(ValueError, match="--transactions must be >= 2"):
        asyncio.run(run_demo("sqlite:///:memory:", "localhost:9092", "http://localhost:8000", count=1, dry_run=True))


def test_invalid_interval_rejected():
    """Verify that CLI and run_demo reject --interval-ms < 0."""
    cmd = [sys.executable, "-m", "simulator.demo_attack", "--interval-ms", "-10"]
    res = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True)
    assert res.returncode != 0
    assert "--interval-ms must be >= 0" in res.stderr

    import asyncio
    with pytest.raises(ValueError, match="--interval-ms must be >= 0"):
        asyncio.run(run_demo("sqlite:///:memory:", "localhost:9092", "http://localhost:8000", interval_ms=-1, dry_run=True))


def test_invalid_amount_rejected():
    """Verify that CLI and run_demo reject --amount <= 0."""
    cmd = [sys.executable, "-m", "simulator.demo_attack", "--amount", "0"]
    res = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True)
    assert res.returncode != 0
    assert "--amount must be > 0" in res.stderr

    cmd_neg = [sys.executable, "-m", "simulator.demo_attack", "--amount", "-4.50"]
    res_neg = subprocess.run(cmd_neg, cwd=REPO_ROOT, capture_output=True, text=True)
    assert res_neg.returncode != 0
    assert "--amount must be > 0" in res_neg.stderr

    import asyncio
    with pytest.raises(ValueError, match="--amount must be > 0"):
        asyncio.run(run_demo("sqlite:///:memory:", "localhost:9092", "http://localhost:8000", attack_amount=0, dry_run=True))


def test_failed_verification_does_not_cause_premature_polling_success():
    """Verify that if a case exists but verification fails, polling does not prematurely succeed."""
    import asyncio

    async def _runner():
        cust_id = uuid.uuid4()
        attack_tx_id = uuid.uuid4()
        target_case_id = uuid.uuid4()
        now = datetime.now(timezone.utc)

        # Case has tampered risk score (0.99 instead of 0.725)
        mock_case_row = (
            target_case_id,
            cust_id,
            0.99,       # overall_risk_score (tampered)
            "HIGH",     # risk_tier
            "open",     # status
            "Velocity", # case_reason
            now,        # created_at
            0.85,       # transaction_risk_score
            0.40,       # network_risk_score
            0.90        # temporal_risk_score
        )
        mock_entities = [("transaction", str(attack_tx_id), "trigger_transaction")]
        mock_evidence = [(str(uuid.uuid4()), str(target_case_id), "velocity")]

        class MockResult:
            def __init__(self, first_row=None, all_rows=None):
                self._first = first_row
                self._all = all_rows or ([] if first_row is None else [first_row])

            def first(self):
                return self._first

            def fetchall(self):
                return self._all

        class MockConn:
            async def execute(self, statement, params=None):
                sql = str(statement)
                if "temporal_anomalies" in sql:
                    return MockResult((0, 0.0))
                if "network_risks" in sql:
                    return MockResult((0.0, 0))
                if "risk_predictions" in sql:
                    return MockResult(None)
                if "case_entities ce ON c.case_id = ce.case_id" in sql:
                    return MockResult(mock_case_row)
                if "FROM case_entities" in sql:
                    return MockResult(all_rows=mock_entities)
                if "FROM case_evidence" in sql:
                    return MockResult(all_rows=mock_evidence)
                return MockResult(None)

            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                pass

        class MockEngine:
            def connect(self):
                return MockConn()

        # Poll with max_wait_sec = 0.2
        start_time = time.time()
        res = await poll_pipeline_results(MockEngine(), cust_id, attack_tx_id, max_wait_sec=0.2)
        elapsed = time.time() - start_time

        # Verification must fail and polling must NOT mark case as verified
        assert res["case"] is not None
        assert res["is_case_verified"] is False
        assert res["verification_error"] is not None
        assert "Risk score mismatch" in res["verification_error"]
        # Verify it waited and did not break prematurely on iteration 1
        assert elapsed >= 0.15

    asyncio.run(_runner())


class _PollingResult:
    def __init__(self, first_row=None, all_rows=None):
        self._first = first_row
        self._all = all_rows or ([] if first_row is None else [first_row])

    def first(self):
        return self._first

    def fetchall(self):
        return self._all


class _PollingConnection:
    def __init__(self, case_row, attack_tx_id, case_id, network_after=0, network_rows=None):
        self.case_row = case_row
        self.attack_tx_id = attack_tx_id
        self.case_id = case_id
        self.network_after = network_after
        self.network_rows = network_rows or [(0.0, 30)]
        self.poll_count = 0

    async def execute(self, statement, params=None):
        sql = str(statement)
        if "temporal_anomalies" in sql:
            return _PollingResult((1, 2.5))
        if "network_risks" in sql:
            self.poll_count += 1
            if self.poll_count <= self.network_after:
                return _PollingResult(None)
            row = self.network_rows[min(self.poll_count - self.network_after - 1, len(self.network_rows) - 1)]
            return _PollingResult(row)
        if "risk_predictions" in sql:
            return _PollingResult((0.85, "HIGH", "model-2", datetime.now(timezone.utc)))
        if "case_entities ce ON c.case_id = ce.case_id" in sql:
            return _PollingResult(self.case_row)
        if "FROM case_entities" in sql:
            return _PollingResult(all_rows=[("transaction", str(self.attack_tx_id), "trigger_transaction")])
        if "FROM case_evidence" in sql:
            return _PollingResult(all_rows=[(str(uuid.uuid4()), str(self.case_id), "velocity")])
        return _PollingResult(None)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass


class _PollingEngine:
    def __init__(self, connection):
        self.connection = connection

    def connect(self):
        return self.connection


def _valid_polling_fixture(network_after=0, network_rows=None):
    customer_id = uuid.uuid4()
    attack_tx_id = uuid.uuid4()
    case_id = uuid.uuid4()
    now = datetime.now(timezone.utc)
    case_row = (
        case_id, customer_id, 0.725, "HIGH", "open", "Velocity", now,
        0.85, 0.40, 0.90
    )
    connection = _PollingConnection(
        case_row, attack_tx_id, case_id, network_after=network_after,
        network_rows=network_rows
    )
    return customer_id, attack_tx_id, connection


def test_polling_waits_for_network_risks_after_case_exists():
    import asyncio

    async def _runner():
        customer_id, attack_tx_id, connection = _valid_polling_fixture(network_after=1)
        result = await poll_pipeline_results(
            _PollingEngine(connection), customer_id, attack_tx_id, max_wait_sec=0.8
        )
        assert result["is_case_verified"] is True
        assert result["network_snapshot_ready"] is True
        assert result["timed_out"] is False
        assert connection.poll_count >= 2

    asyncio.run(_runner())


def test_polling_network_size_is_node_count_and_case_risk_is_authoritative():
    import asyncio

    async def _runner():
        customer_id, attack_tx_id, connection = _valid_polling_fixture(
            network_rows=[(0.90, 30), (0.10, 40)]
        )
        result = await poll_pipeline_results(
            _PollingEngine(connection), customer_id, attack_tx_id, max_wait_sec=0.2
        )
        assert result["network_size"] == 30
        assert result["network_risk"] == 0.90
        assert result["case_network_risk"] == 0.40
        assert result["case"]["network_risk"] == 0.40

    asyncio.run(_runner())


def test_polling_times_out_clearly_when_network_risks_never_appear():
    import asyncio

    async def _runner():
        customer_id, attack_tx_id, connection = _valid_polling_fixture(network_after=100)
        result = await poll_pipeline_results(
            _PollingEngine(connection), customer_id, attack_tx_id, max_wait_sec=0.1
        )
        assert result["timed_out"] is True
        assert "network_risks snapshot" in result["timeout_error"]
        assert result["is_case_verified"] is True

    asyncio.run(_runner())
