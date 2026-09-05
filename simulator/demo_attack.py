"""SentinelGraph Live Demo - Isolated Current-Time Fraud Attack Generator.

Generates a realistic current-time velocity-abuse burst for an existing customer,
persists transactions to PostgreSQL, publishes to Kafka payment.events, scores the
attack transaction via the authenticated Risk API, and verifies downstream
Temporal, Graph, and Case Worker processing.
"""

import argparse
import asyncio
import decimal
import json
import os
import sys
import time
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# Controlled import-path adjustment:
_REPO_ROOT = Path(__file__).resolve().parent.parent
_API_DIR = _REPO_ROOT / "apps" / "api"
if _API_DIR.is_dir() and str(_API_DIR) not in sys.path:
    sys.path.insert(0, str(_API_DIR))
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


def json_serializer(obj: Any) -> Any:
    """JSON serializer for UUID, datetime, and Decimal objects."""
    if isinstance(obj, uuid.UUID):
        return str(obj)
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, decimal.Decimal):
        return float(obj)
    raise TypeError(f"Type {type(obj)} not serializable")


def generate_burst_transactions(
    entities: Dict[str, Any],
    count: int = 25,
    attack_amount: float = 4.98,
    window_seconds: int = 60,
    base_time: Optional[datetime] = None
) -> List[Dict[str, Any]]:
    """Generate in-memory card-testing velocity burst transactions ending at base_time (UTC)."""
    now = base_time or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)

    window_sec = max(10, window_seconds)
    start_time = now - timedelta(seconds=window_sec)
    step = timedelta(seconds=(window_sec - 2) / max(1, count - 1)) if count > 1 else timedelta(seconds=0)

    transactions = []
    for i in range(count):
        tx_id = uuid.uuid4()
        is_final = (i == count - 1)
        occurred = now if is_final else (start_time + i * step)

        # Card-testing micro-transactions ($1.50 - $4.50) for warmup, configured attack amount ($4.98) for final attack
        if is_final:
            amt = decimal.Decimal(str(round(attack_amount, 2)))
        else:
            # Deterministic card-testing amounts between $1.50 and $4.50
            warmup_val = 1.50 + ((i % 10) * 0.30)
            amt = decimal.Decimal(str(round(warmup_val, 2)))

        tx = {
            "transaction_id": tx_id,
            "customer_id": entities["customer_id"],
            "merchant_id": entities["merchant_id"],
            "device_id": entities.get("device_id"),
            "instrument_id": entities.get("instrument_id"),
            "ip_id": entities.get("ip_id"),
            "amount": amt,
            "currency": "USD",
            "transaction_type": "purchase",
            "status": "completed",
            "occurred_at": occurred,
            "created_at": now
        }
        transactions.append(tx)

    return transactions


async def fetch_demo_customer_and_entities(engine, customer_id: Optional[str] = None) -> Dict[str, Any]:
    """Fetch an existing customer and related entity IDs from PostgreSQL."""
    from sqlalchemy import text

    async with engine.connect() as conn:
        if customer_id:
            cust_uuid = uuid.UUID(str(customer_id))
            q = text("""
                SELECT t.customer_id, t.merchant_id, t.device_id, t.instrument_id, t.ip_id
                FROM transactions t
                WHERE t.customer_id = :cid
                ORDER BY t.occurred_at DESC
                LIMIT 1;
            """)
            res = await conn.execute(q, {"cid": cust_uuid})
            row = res.first()
            if row:
                return {
                    "customer_id": row[0],
                    "merchant_id": row[1],
                    "device_id": row[2],
                    "instrument_id": row[3],
                    "ip_id": row[4],
                }

            # Check if customer exists in customers table
            q_cust = text("SELECT customer_id FROM customers WHERE customer_id = :cid")
            res_c = await conn.execute(q_cust, {"cid": cust_uuid})
            if not res_c.first():
                raise ValueError(f"Customer '{customer_id}' does not exist in PostgreSQL.")

            # Fallback to any valid active entities for the customer
            m_id = (await conn.execute(text("SELECT merchant_id FROM merchants LIMIT 1"))).scalar()
            d_id = (await conn.execute(text("SELECT device_id FROM devices LIMIT 1"))).scalar()
            i_id = (await conn.execute(text("SELECT instrument_id FROM payment_instruments LIMIT 1"))).scalar()
            ip_id = (await conn.execute(text("SELECT ip_id FROM ip_addresses LIMIT 1"))).scalar()
            return {
                "customer_id": cust_uuid,
                "merchant_id": m_id,
                "device_id": d_id,
                "instrument_id": i_id,
                "ip_id": ip_id
            }

        # Auto-select an active customer with >= 20 historical transactions and no current open case
        q_auto = text("""
            SELECT c.customer_id,
                   max(t.merchant_id::text) as merchant_id,
                   max(t.device_id::text) as device_id,
                   max(t.instrument_id::text) as instrument_id,
                   max(t.ip_id::text) as ip_id
            FROM customers c
            JOIN transactions t ON c.customer_id = t.customer_id
            WHERE c.customer_id NOT IN (
                SELECT primary_entity_id FROM risk_cases WHERE primary_entity_type = 'customer' AND status = 'open'
            )
            GROUP BY c.customer_id
            HAVING count(t.transaction_id) >= 20
            ORDER BY count(t.transaction_id) DESC
            LIMIT 1;
        """)
        res = await conn.execute(q_auto)
        row = res.first()
        if not row:
            raise RuntimeError("No suitable existing customer found in PostgreSQL.")

        return {
            "customer_id": uuid.UUID(str(row[0])),
            "merchant_id": uuid.UUID(str(row[1])),
            "device_id": uuid.UUID(str(row[2])),
            "instrument_id": uuid.UUID(str(row[3])),
            "ip_id": uuid.UUID(str(row[4])),
        }


def login_for_access_token(
    api_url: str,
    username: Optional[str] = None,
    password: Optional[str] = None
) -> str:
    """Authenticate against POST /api/v1/auth/login and return the JWT bearer token."""
    user = username or os.environ.get("SENTINEL_API_USER") or os.environ.get("API_USERNAME") or os.environ.get("API_USER") or "admin"
    pwd = password or os.environ.get("SENTINEL_API_PASSWORD") or os.environ.get("API_PASSWORD") or os.environ.get("DEMO_API_PASSWORD")

    if not pwd:
        raise RuntimeError(
            "Missing API password for Risk API authentication. "
            "Please provide --api-password or set the API_PASSWORD environment variable."
        )

    url = f"{api_url.rstrip('/')}/api/v1/auth/login"
    payload = json.dumps({"username": user, "password": pwd}).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    req = urllib.request.Request(url, data=payload, headers=headers)

    try:
        with urllib.request.urlopen(req, timeout=10.0) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            token = data.get("token")
            if not token:
                raise RuntimeError(f"Authentication response from {url} did not include a 'token' field.")
            return str(token)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        raise RuntimeError(f"Authentication failed for user '{user}' (HTTP {e.code}): {body}")
    except Exception as e:
        raise RuntimeError(f"Failed to connect to authentication endpoint at {url}: {e}")


def call_risk_score_api(api_url: str, transaction_id: uuid.UUID, auth_token: Optional[str] = None) -> Dict[str, Any]:
    """Call POST /api/v1/risk/score to obtain and persist real Model 2 XGBoost prediction."""
    url = f"{api_url.rstrip('/')}/api/v1/risk/score"
    payload = json.dumps({"transaction_id": str(transaction_id)}).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if auth_token:
        headers["Authorization"] = f"Bearer {auth_token}"

    req = urllib.request.Request(url, data=payload, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=15.0) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        raise RuntimeError(f"Risk API HTTP {e.code} error: {body}")
    except Exception as e:
        raise RuntimeError(f"Failed to connect to Risk API at {url}: {e}")


def compute_expected_risk(tx_risk: float, net_risk: float, temp_risk: float) -> tuple[float, str]:
    """Calculate the expected case score independently using Case Worker formula:
    overall = clamp(0.50 * tx + 0.30 * net + 0.20 * temp, 0, 1)
    Returns (round(clamped, 4), tier).
    """
    score = 0.50 * float(tx_risk) + 0.30 * float(net_risk) + 0.20 * float(temp_risk)
    clamped = max(0.0, min(1.0, score))
    if clamped >= 0.80:
        tier = "CRITICAL"
    elif clamped >= 0.60:
        tier = "HIGH"
    elif clamped >= 0.30:
        tier = "MEDIUM"
    else:
        tier = "LOW"
    return round(clamped, 4), tier


def verify_case_for_attack_transaction(
    case_record: Optional[Dict[str, Any]],
    case_entities: List[Dict[str, Any]],
    evidence_records: List[Dict[str, Any]],
    expected_customer_id: uuid.UUID,
    attack_tx_id: uuid.UUID
) -> Dict[str, Any]:
    """Verify that a retrieved case is legitimately associated with the attack transaction.

    Verifies:
    1. Case exists
    2. case.customer_id == expected_customer_id
    3. case_entities contains attack_tx_id with entity_type == 'transaction'
    4. evidence belongs to the same case (and evidence is non-empty)
    5. case status exists
    6. persisted case transaction/network/temporal risk components exist
    7. independently calculated expected aggregate risk matches persisted case overall risk within tolerance (0.001)
    8. persisted case tier matches independently calculated expected tier
    """
    if not case_record:
        return {
            "verified": False,
            "error": "No case record provided"
        }

    # 1. Customer ID match
    case_cust_id = str(case_record.get("customer_id") or case_record.get("primary_entity_id") or "")
    if not case_cust_id or case_cust_id != str(expected_customer_id):
        return {
            "verified": False,
            "error": f"Customer ID mismatch: expected {expected_customer_id}, got {case_cust_id}"
        }

    # 2. Case entities contains attack transaction ID
    tx_entity_found = any(
        str(e.get("entity_id")) == str(attack_tx_id) and str(e.get("entity_type", "")).lower() == "transaction"
        for e in (case_entities or [])
    )
    if not tx_entity_found:
        return {
            "verified": False,
            "error": f"Attack transaction {attack_tx_id} not found in case entities"
        }

    # 3. Status is reported correctly
    status = case_record.get("status")
    if not status:
        return {
            "verified": False,
            "error": "Missing status in case record"
        }

    # 4. Evidence belongs to this case
    case_id_str = str(case_record.get("case_id") or "")
    if not case_id_str:
        return {
            "verified": False,
            "error": "Missing case_id in case record"
        }
    if not evidence_records:
        return {
            "verified": False,
            "error": f"No evidence records found for case {case_id_str}"
        }
    for ev in evidence_records:
        ev_case_id = str(ev.get("case_id") or "")
        if ev_case_id != case_id_str:
            return {
                "verified": False,
                "error": f"Evidence {ev.get('evidence_id')} belongs to case {ev_case_id}, not {case_id_str}"
            }

    # 5. Persisted risk components exist
    tx_risk = case_record.get("transaction_risk") if case_record.get("transaction_risk") is not None else case_record.get("transaction_risk_score")
    if tx_risk is None:
        return {
            "verified": False,
            "error": "Missing persisted transaction_risk component in case record"
        }

    net_risk = case_record.get("network_risk") if case_record.get("network_risk") is not None else case_record.get("network_risk_score")
    if net_risk is None:
        return {
            "verified": False,
            "error": "Missing persisted network_risk component in case record"
        }

    temp_risk = case_record.get("temporal_risk") if case_record.get("temporal_risk") is not None else case_record.get("temporal_risk_score")
    if temp_risk is None:
        return {
            "verified": False,
            "error": "Missing persisted temporal_risk component in case record"
        }

    overall_risk = case_record.get("overall_risk") if case_record.get("overall_risk") is not None else case_record.get("overall_risk_score")
    if overall_risk is None:
        return {
            "verified": False,
            "error": "Missing persisted overall_risk in case record"
        }

    risk_tier = case_record.get("tier") or case_record.get("risk_tier")
    if not risk_tier:
        return {
            "verified": False,
            "error": "Missing persisted risk_tier in case record"
        }

    # 6. Independently calculated expected aggregate risk matches persisted overall risk
    expected_aggregate_unrounded = max(
        0.0,
        min(1.0, 0.50 * float(tx_risk) + 0.30 * float(net_risk) + 0.20 * float(temp_risk))
    )
    diff = abs(float(overall_risk) - expected_aggregate_unrounded)
    if diff > 1e-3:
        return {
            "verified": False,
            "error": (
                f"Risk score mismatch: persisted overall_risk={overall_risk}, "
                f"expected aggregate={expected_aggregate_unrounded:.6f} "
                f"(diff={diff:.6f}, tolerance=0.001)"
            )
        }

    # 7. Persisted tier matches expected tier
    if expected_aggregate_unrounded >= 0.80:
        expected_tier = "CRITICAL"
    elif expected_aggregate_unrounded >= 0.60:
        expected_tier = "HIGH"
    elif expected_aggregate_unrounded >= 0.30:
        expected_tier = "MEDIUM"
    else:
        expected_tier = "LOW"

    if str(risk_tier).upper() != expected_tier:
        return {
            "verified": False,
            "error": f"Risk tier mismatch: persisted tier='{risk_tier}', expected tier='{expected_tier}'"
        }

    return {
        "verified": True,
        "error": None
    }


def fetch_case_for_transaction_sync(conn, attack_tx_id: uuid.UUID) -> Optional[Dict[str, Any]]:
    """Synchronously query the risk case associated with the exact attack transaction ID via case_entities."""
    from sqlalchemy import text
    q = text("""
        SELECT c.case_id,
               c.primary_entity_id,
               c.overall_risk_score,
               c.risk_tier,
               c.status,
               c.case_reason,
               c.created_at,
               c.transaction_risk_score,
               c.network_risk_score,
               c.temporal_risk_score
        FROM risk_cases c
        JOIN case_entities ce ON c.case_id = ce.case_id
        WHERE ce.entity_type = 'transaction'
          AND ce.entity_id = :tx_id
        ORDER BY c.created_at DESC
        LIMIT 1;
    """)
    row = conn.execute(q, {"tx_id": attack_tx_id}).first()
    if not row:
        return None
    return {
        "case_id": str(row[0]),
        "customer_id": str(row[1]),
        "overall_risk": float(row[2]),
        "tier": str(row[3]),
        "status": str(row[4]),
        "case_reason": str(row[5]),
        "created_at": row[6],
        "transaction_risk": float(row[7]) if row[7] is not None else None,
        "network_risk": float(row[8]) if row[8] is not None else None,
        "temporal_risk": float(row[9]) if row[9] is not None else None,
        "associated_transaction_id": str(attack_tx_id)
    }


def fetch_case_entities_sync(conn, case_id: uuid.UUID) -> List[Dict[str, Any]]:
    """Synchronously fetch all case entities for a given case_id."""
    from sqlalchemy import text
    q = text("SELECT entity_type, entity_id, role FROM case_entities WHERE case_id = :cid")
    rows = conn.execute(q, {"cid": case_id}).fetchall()
    return [{"entity_type": str(r[0]), "entity_id": str(r[1]), "role": str(r[2]) if r[2] else None} for r in rows]


def fetch_case_evidence_sync(conn, case_id: uuid.UUID) -> List[Dict[str, Any]]:
    """Synchronously fetch evidence records for a given case_id."""
    from sqlalchemy import text
    q = text("SELECT evidence_id, case_id, evidence_type FROM case_evidence WHERE case_id = :cid")
    rows = conn.execute(q, {"cid": case_id}).fetchall()
    return [{"evidence_id": str(r[0]), "case_id": str(r[1]), "evidence_type": str(r[2])} for r in rows]


async def poll_pipeline_results(engine, customer_id: uuid.UUID, attack_tx_id: uuid.UUID, max_wait_sec: float = 45.0) -> Dict[str, Any]:
    """Query PostgreSQL for downstream Temporal, Graph, ML, and Case Worker records.
    Explicitly associates the case with the exact attack transaction via case_entities.
    """
    from sqlalchemy import text

    start_wait = time.time()
    results: Dict[str, Any] = {
        "anomalies_count": 0,
        "temporal_risk": 0.0,
        "network_risk": 0.0,
        "case_network_risk": None,
        "network_size": 0,
        "network_snapshot_ready": False,
        "prediction": None,
        "case": None,
        "evidence_count": 0,
        "case_reason": None,
        "case_entities": [],
        "is_case_verified": False,
        "verification_error": None,
        "latest_customer_case": None,
        "timed_out": False,
        "timeout_error": None
    }

    while time.time() - start_wait < max_wait_sec:
        async with engine.connect() as conn:
            # 1. Temporal anomalies for this customer detected recently
            q_anom = text("""
                SELECT count(*), coalesce(max(anomaly_score), 0.0)
                FROM temporal_anomalies
                WHERE entity_id = :cid
                  AND detected_at >= now() - INTERVAL '5 minutes';
            """)
            r_anom = (await conn.execute(q_anom, {"cid": customer_id})).first()
            if r_anom:
                results["anomalies_count"] = int(r_anom[0])
                score = float(r_anom[1])
                results["temporal_risk"] = round(min(1.0, score / 5.0), 4)

            # 2. Network risks for this customer
            q_net = text("""
                SELECT graph_risk_score, node_count as net_size
                FROM network_risks
                WHERE network_id = :cid
                ORDER BY detected_at DESC
                LIMIT 1;
            """)
            r_net = (await conn.execute(q_net, {"cid": customer_id})).first()
            if r_net:
                results["network_risk"] = float(r_net[0])
                results["network_size"] = int(r_net[1])
                results["network_snapshot_ready"] = True

            # 3. Risk prediction for attack transaction
            q_pred = text("""
                SELECT risk_score, risk_tier, model_version, predicted_at
                FROM risk_predictions
                WHERE transaction_id = :tx_id
                ORDER BY predicted_at DESC
                LIMIT 1;
            """)
            r_pred = (await conn.execute(q_pred, {"tx_id": attack_tx_id})).first()
            if r_pred:
                results["prediction"] = {
                    "risk_score": float(r_pred[0]),
                    "risk_tier": str(r_pred[1]),
                    "model_version": str(r_pred[2]),
                    "predicted_at": r_pred[3]
                }

            # 4. Check for case associated with the EXACT attack transaction ID via case_entities
            q_attack_case = text("""
                SELECT c.case_id,
                       c.primary_entity_id,
                       c.overall_risk_score,
                       c.risk_tier,
                       c.status,
                       c.case_reason,
                       c.created_at,
                       c.transaction_risk_score,
                       c.network_risk_score,
                       c.temporal_risk_score
                FROM risk_cases c
                JOIN case_entities ce ON c.case_id = ce.case_id
                WHERE ce.entity_type = 'transaction'
                  AND ce.entity_id = :tx_id
                ORDER BY c.created_at DESC
                LIMIT 1;
            """)
            r_attack_case = (await conn.execute(q_attack_case, {"tx_id": attack_tx_id})).first()

            if r_attack_case:
                target_case_id = r_attack_case[0]
                case_dict = {
                    "case_id": str(target_case_id),
                    "customer_id": str(r_attack_case[1]),
                    "overall_risk": float(r_attack_case[2]),
                    "tier": str(r_attack_case[3]),
                    "status": str(r_attack_case[4]),
                    "created_at": r_attack_case[6],
                    "transaction_risk": float(r_attack_case[7]) if r_attack_case[7] is not None else None,
                    "network_risk": float(r_attack_case[8]) if r_attack_case[8] is not None else None,
                    "temporal_risk": float(r_attack_case[9]) if r_attack_case[9] is not None else None,
                    "associated_transaction_id": str(attack_tx_id)
                }
                results["case"] = case_dict
                results["case_network_risk"] = case_dict["network_risk"]
                results["case_reason"] = str(r_attack_case[5])

                # Fetch all entities for this case
                q_entities = text("""
                    SELECT entity_type, entity_id, role
                    FROM case_entities
                    WHERE case_id = :cid;
                """)
                res_ent = await conn.execute(q_entities, {"cid": target_case_id})
                entities_list = [
                    {"entity_type": str(row[0]), "entity_id": str(row[1]), "role": str(row[2]) if row[2] else None}
                    for row in res_ent.fetchall()
                ]
                results["case_entities"] = entities_list

                # Fetch evidence for this case
                q_ev = text("""
                    SELECT evidence_id, case_id, evidence_type
                    FROM case_evidence
                    WHERE case_id = :cid;
                """)
                res_ev = await conn.execute(q_ev, {"cid": target_case_id})
                ev_list = [
                    {"evidence_id": str(row[0]), "case_id": str(row[1]), "evidence_type": str(row[2])}
                    for row in res_ev.fetchall()
                ]
                results["evidence_count"] = len(ev_list)

                # Verify case legitimacy
                verif = verify_case_for_attack_transaction(
                    case_record=case_dict,
                    case_entities=entities_list,
                    evidence_records=ev_list,
                    expected_customer_id=customer_id,
                    attack_tx_id=attack_tx_id
                )
                results["is_case_verified"] = verif["verified"]
                results["verification_error"] = verif["error"]

            else:
                # Also fetch latest customer case (if any) separately for transparency
                q_latest_cust = text("""
                    SELECT case_id, overall_risk_score, risk_tier, status, case_reason, created_at
                    FROM risk_cases
                    WHERE primary_entity_type = 'customer'
                    AND primary_entity_id = :cid
                    ORDER BY created_at DESC
                    LIMIT 1;
                """)
                r_cust_case = (await conn.execute(q_latest_cust, {"cid": customer_id})).first()
                if r_cust_case:
                    results["latest_customer_case"] = {
                        "case_id": str(r_cust_case[0]),
                        "overall_risk": float(r_cust_case[1]),
                        "tier": str(r_cust_case[2]),
                        "status": str(r_cust_case[3]),
                        "case_reason": str(r_cust_case[4]),
                        "created_at": r_cust_case[5]
                    }

        # Every asynchronous signal must be present before the demo is complete.
        if (
            results["anomalies_count"] > 0
            and results["prediction"] is not None
            and results["network_size"] > 0
            and results["case"] is not None
            and results["evidence_count"] > 0
            and results["is_case_verified"] is True
        ):
            break

        await asyncio.sleep(0.5)

    if not (
        results["anomalies_count"] > 0
        and results["prediction"] is not None
        and results["network_snapshot_ready"]
        and results["case"] is not None
        and results["evidence_count"] > 0
        and results["is_case_verified"] is True
    ):
        missing = []
        if results["anomalies_count"] <= 0:
            missing.append("temporal result")
        if results["prediction"] is None:
            missing.append("attack transaction risk prediction")
        if not results["network_snapshot_ready"]:
            missing.append("network_risks snapshot")
        if results["case"] is None or not results["is_case_verified"]:
            missing.append("verified attack case")
        elif results["evidence_count"] <= 0:
            missing.append("case evidence")
        results["timed_out"] = True
        results["timeout_error"] = (
            f"Timed out after {max_wait_sec:.1f}s waiting for: {', '.join(missing)}"
        )

    return results


def print_demo_summary(
    customer_id: uuid.UUID,
    transactions: List[Dict[str, Any]],
    attack_tx: Dict[str, Any],
    api_result: Dict[str, Any],
    pipeline_result: Dict[str, Any]
):
    """Print standard formatted demo summary distinguishing all pipeline components."""
    start_time = transactions[0]["occurred_at"].strftime("%Y-%m-%d %H:%M:%S UTC")
    end_time = transactions[-1]["occurred_at"].strftime("%Y-%m-%d %H:%M:%S UTC")

    print("\n" + "=" * 40)
    print("SENTINELGRAPH LIVE FRAUD DEMO")
    print("=============================\n")
    print(f"Customer: {customer_id}")
    print(f"Transactions generated: {len(transactions)}")
    print(f"Attack window: {start_time} -> {end_time}\n")

    print("Attack transaction:")
    print(f"ID: {attack_tx['transaction_id']}")
    print(f"Amount: ${float(attack_tx['amount']):.2f}")
    print(f"Occurred: {attack_tx['occurred_at'].strftime('%Y-%m-%d %H:%M:%S UTC')}\n")

    print("Temporal signals (associated with attack burst):")
    print(f"anomalies count: {pipeline_result.get('anomalies_count', 0)}")
    print(f"temporal risk: {pipeline_result.get('temporal_risk', 0.0):.4f}\n")

    print("Graph signals (current customer network snapshot):")
    print(f"current graph risk: {pipeline_result.get('network_risk', 0.0):.4f}")
    print(f"current network size: {pipeline_result.get('network_size', 0)} nodes\n")
    if pipeline_result.get("timed_out"):
        print(f"pipeline verification: TIMEOUT ({pipeline_result.get('timeout_error', 'incomplete results')})\n")

    ml_score = api_result.get("risk_score", 0.0)
    ml_tier = api_result.get("risk_tier", "UNKNOWN")
    ml_dec = api_result.get("decision", "UNKNOWN")
    ml_model = api_result.get("model_version", "xgb-graph-v1")
    print("ML prediction (for attack transaction):")
    print(f"risk score: {ml_score:.4f}")
    print(f"tier: {ml_tier}")
    print(f"decision: {ml_dec}")
    print(f"model: {ml_model}\n")

    case_info = pipeline_result.get("case")
    tx_r = case_info.get("transaction_risk", ml_score) if case_info else ml_score
    net_r = case_info.get("network_risk", pipeline_result.get("network_risk", 0.0)) if case_info else pipeline_result.get("network_risk", 0.0)
    temp_r = case_info.get("temporal_risk", pipeline_result.get("temporal_risk", 0.0)) if case_info else pipeline_result.get("temporal_risk", 0.0)
    exp_overall, exp_tier = compute_expected_risk(tx_r, net_r, temp_r)
    print("Risk Aggregation (Formula Verification):")
    print(f"expected aggregate risk: {exp_overall:.4f} ({exp_tier})")
    print(f"formula: clamp(0.50*{tx_r:.4f} + 0.30*{net_r:.4f} + 0.20*{temp_r:.4f}, 0, 1)\n")

    if case_info:
        print("Case for attack transaction:")
        print(f"case ID: {case_info['case_id']}")
        print(f"customer ID: {case_info.get('customer_id', customer_id)}")
        print(f"associated transaction ID: {case_info.get('associated_transaction_id', attack_tx['transaction_id'])}")
        print(f"case network risk: {case_info['network_risk']:.4f}")
        print(f"overall risk: {case_info['overall_risk']:.4f}")
        print(f"tier: {case_info['tier']}")
        print(f"status: {case_info['status']}")
        print(f"case reason: {pipeline_result.get('case_reason', 'N/A')}")
        print(f"Evidence: {pipeline_result.get('evidence_count', 0)} evidence records")
        if pipeline_result.get("is_case_verified"):
            print("verification: PASSED (exact transaction linked, customer matched, risk score & tier validated)\n")
        else:
            print(f"verification: FAILED ({pipeline_result.get('verification_error')})\n")
    else:
        print("CASE FOR ATTACK TRANSACTION: NOT CREATED")
        print(f"ML risk: {tx_r:.4f}")
        print(f"temporal risk: {temp_r:.4f}")
        print(f"current graph risk: {net_r:.4f}")
        print(f"expected aggregate risk: {exp_overall:.4f} ({exp_tier})")
        print("reason: threshold for case creation is >= 0.60 or cooldown active\n")

        latest_cust_case = pipeline_result.get("latest_customer_case")
        if latest_cust_case:
            print("Separate latest customer case (unrelated to this attack transaction):")
            print(f"case ID: {latest_cust_case['case_id']}")
            print(f"overall risk: {latest_cust_case['overall_risk']:.4f}")
            print(f"tier: {latest_cust_case['tier']}")
            print(f"status: {latest_cust_case['status']}")
            print(f"created: {latest_cust_case['created_at']}\n")

    print("=" * 40 + "\n")


async def run_demo(
    db_url: str,
    kafka_broker: str,
    api_url: str,
    count: int = 25,
    interval_ms: int = 50,
    attack_amount: float = 4.98,
    customer_id: Optional[str] = None,
    dry_run: bool = False,
    api_username: Optional[str] = None,
    api_password: Optional[str] = None,
    auth_token: Optional[str] = None
):
    """Execute the full demo attack scenario."""
    from sqlalchemy.ext.asyncio import create_async_engine
    from sqlalchemy import insert
    from app.models.transaction import Transaction

    # Fail fast on invalid configurations
    if count < 2:
        raise ValueError(f"--transactions must be >= 2, got {count}")
    if interval_ms < 0:
        raise ValueError(f"--interval-ms must be >= 0, got {interval_ms}")
    if attack_amount <= 0:
        raise ValueError(f"--amount must be > 0, got {attack_amount}")

    engine = create_async_engine(db_url)
    producer = None

    try:
        # 1. Fetch customer and associated entities
        if dry_run:
            if customer_id:
                try:
                    cust_uuid = uuid.UUID(str(customer_id))
                except Exception as e:
                    raise ValueError(f"Invalid customer UUID '{customer_id}': {e}")
                try:
                    entities = await fetch_demo_customer_and_entities(engine, str(cust_uuid))
                except Exception:
                    entities = {
                        "customer_id": cust_uuid,
                        "merchant_id": uuid.uuid4(),
                        "device_id": uuid.uuid4(),
                        "instrument_id": uuid.uuid4(),
                        "ip_id": uuid.uuid4()
                    }
            else:
                # Synthetic placeholder UUID and entities for in-memory dry-run
                cust_uuid = uuid.UUID("00000000-0000-0000-0000-000000000001")
                entities = {
                    "customer_id": cust_uuid,
                    "merchant_id": uuid.UUID("00000000-0000-0000-0000-000000000002"),
                    "device_id": uuid.UUID("00000000-0000-0000-0000-000000000003"),
                    "instrument_id": uuid.UUID("00000000-0000-0000-0000-000000000004"),
                    "ip_id": uuid.UUID("00000000-0000-0000-0000-000000000005")
                }
        else:
            entities = await fetch_demo_customer_and_entities(engine, customer_id)
        cust_id = entities["customer_id"]

        # 2. Generate transactions
        transactions = generate_burst_transactions(
            entities=entities,
            count=count,
            attack_amount=attack_amount,
            window_seconds=60
        )

        if dry_run:
            print("\n" + "=" * 40)
            print("SENTINELGRAPH LIVE FRAUD DEMO (DRY RUN)")
            print("=======================================\n")
            print(f"Customer: {cust_id}")
            print(f"Transactions generated (in-memory): {len(transactions)}")
            print(f"Attack transaction ID: {transactions[-1]['transaction_id']}")
            print(f"Attack amount: ${float(transactions[-1]['amount']):.2f}")
            print("Mode: Dry run - NO changes written to PostgreSQL or Kafka.")
            print("\n" + "=" * 40 + "\n")
            return

        # Authenticate with Risk API before side effects
        token = auth_token
        if not token:
            effective_user = api_username or os.environ.get("SENTINEL_API_USER") or os.environ.get("API_USERNAME") or os.environ.get("API_USER") or "admin"
            print(f"Authenticating to SentinelGraph API as '{effective_user}'...")
            token = login_for_access_token(api_url, username=effective_user, password=api_password)

        from confluent_kafka import Producer

        producer = Producer({
            "bootstrap.servers": kafka_broker,
            "client.id": "sentinelgraph-demo-attack"
        })

        print(f"Starting live demo attack for customer: {cust_id}...")
        print(f"Persisting and publishing {len(transactions) - 1} warmup burst transactions...")

        # 3. Persist and publish warmup transactions (0 to N-2)
        async with engine.begin() as conn:
            for tx in transactions[:-1]:
                await conn.execute(insert(Transaction).values(tx))

        for tx in transactions[:-1]:
            payload = {
                "transaction_id": str(tx["transaction_id"]),
                "customer_id": str(tx["customer_id"]),
                "merchant_id": str(tx["merchant_id"]),
                "device_id": str(tx["device_id"]) if tx["device_id"] else None,
                "instrument_id": str(tx["instrument_id"]) if tx["instrument_id"] else None,
                "ip_id": str(tx["ip_id"]) if tx["ip_id"] else None,
                "amount": float(tx["amount"]),
                "occurred_at": tx["occurred_at"].isoformat()
            }
            producer.produce("payment.events", key=str(cust_id), value=json.dumps(payload))
            producer.poll(0)
            if interval_ms > 0:
                await asyncio.sleep(interval_ms / 1000.0)

        producer.flush()

        # Brief wait for Temporal Worker to ingest initial burst
        await asyncio.sleep(0.5)

        # 4. Final Attack Transaction
        attack_tx = transactions[-1]
        attack_tx["occurred_at"] = datetime.now(timezone.utc)

        print(f"Persisting attack transaction {attack_tx['transaction_id']} (${float(attack_tx['amount']):.2f})...")
        async with engine.begin() as conn:
            await conn.execute(insert(Transaction).values(attack_tx))

        # 5. Risk Scoring via authenticated API
        print(f"Scoring attack transaction via Risk API ({api_url})...")
        api_result = call_risk_score_api(api_url, attack_tx["transaction_id"], auth_token=token)

        # 6. Publish attack transaction to Kafka
        payload_attack = {
            "transaction_id": str(attack_tx["transaction_id"]),
            "customer_id": str(attack_tx["customer_id"]),
            "merchant_id": str(attack_tx["merchant_id"]),
            "device_id": str(attack_tx["device_id"]) if attack_tx["device_id"] else None,
            "instrument_id": str(attack_tx["instrument_id"]) if attack_tx["instrument_id"] else None,
            "ip_id": str(attack_tx["ip_id"]) if attack_tx["ip_id"] else None,
            "amount": float(attack_tx["amount"]),
            "occurred_at": attack_tx["occurred_at"].isoformat()
        }
        producer.produce("payment.events", key=str(cust_id), value=json.dumps(payload_attack))
        producer.flush()

        # 7. Await downstream Temporal, Graph, and Case Worker pipeline
        print("Awaiting downstream worker processing (Temporal, Graph, Case Worker)...")
        pipeline_result = await poll_pipeline_results(engine, cust_id, attack_tx["transaction_id"], max_wait_sec=45.0)

        # 8. Print formatted summary
        print_demo_summary(cust_id, transactions, attack_tx, api_result, pipeline_result)

    finally:
        if producer is not None:
            try:
                producer.flush(timeout=5.0)
            except Exception:
                pass
            try:
                if hasattr(producer, "close"):
                    producer.close()
            except Exception:
                pass
        await engine.dispose()


def main():
    parser = argparse.ArgumentParser(
        description="SentinelGraph Live Demo - Isolated Current-Time Fraud Attack Generator."
    )
    parser.add_argument(
        "--transactions",
        type=int,
        default=25,
        help="Number of transactions in the card-testing velocity burst (default: 25, min: 2)."
    )
    parser.add_argument(
        "--interval-ms",
        type=int,
        default=50,
        help="Interval in milliseconds between published transactions (default: 50, min: 0)."
    )
    parser.add_argument(
        "--amount",
        type=float,
        default=4.98,
        help="Amount in USD for the final attack transaction (default: 4.98, must be > 0)."
    )
    parser.add_argument(
        "--customer-id",
        type=str,
        default=None,
        help="Specific existing customer UUID to target (default: auto-select an active customer)."
    )
    parser.add_argument(
        "--api-url",
        type=str,
        default=os.environ.get("API_URL", "http://localhost:8000"),
        help="Risk API base URL (default: http://localhost:8000)."
    )
    parser.add_argument(
        "--api-username",
        type=str,
        default=os.environ.get("SENTINEL_API_USER") or os.environ.get("API_USERNAME") or os.environ.get("API_USER") or "admin",
        help="API username for authentication (default: admin or API_USERNAME env var)."
    )
    parser.add_argument(
        "--api-password",
        type=str,
        default=os.environ.get("SENTINEL_API_PASSWORD") or os.environ.get("API_PASSWORD") or os.environ.get("DEMO_API_PASSWORD"),
        help="API password for authentication (default: API_PASSWORD env var)."
    )
    parser.add_argument(
        "--auth-token",
        type=str,
        default=os.environ.get("API_TOKEN") or os.environ.get("AUTH_TOKEN"),
        help="Pre-existing JWT auth token to bypass login (default: AUTH_TOKEN env var)."
    )
    parser.add_argument(
        "--kafka-broker",
        type=str,
        default=os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "localhost:29092"),
        help="Kafka bootstrap server (default: localhost:29092)."
    )
    parser.add_argument(
        "--db-url",
        type=str,
        default=os.environ.get("DATABASE_URL", "postgresql+asyncpg://sentinel_user:sentinel_password@localhost:5432/sentinelgraph"),
        help="PostgreSQL connection URL (default: postgresql+asyncpg://sentinel_user:sentinel_password@localhost:5432/sentinelgraph)."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate burst transaction generation without modifying PostgreSQL or publishing to Kafka."
    )

    args = parser.parse_args()

    if args.transactions < 2:
        parser.error("--transactions must be >= 2 (requires at least 1 warmup transaction and 1 attack transaction)")
    if args.interval_ms < 0:
        parser.error("--interval-ms must be >= 0")
    if args.amount <= 0:
        parser.error("--amount must be > 0")

    asyncio.run(run_demo(
        db_url=args.db_url,
        kafka_broker=args.kafka_broker,
        api_url=args.api_url,
        count=args.transactions,
        interval_ms=args.interval_ms,
        attack_amount=args.amount,
        customer_id=args.customer_id,
        dry_run=args.dry_run,
        api_username=args.api_username,
        api_password=args.api_password,
        auth_token=args.auth_token
    ))


if __name__ == "__main__":
    main()
