import json
import os
import signal
import sys
import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional
from confluent_kafka import Consumer, KafkaError
from sqlalchemy import create_engine, text
import structlog
import numpy as np

from evidence_generator import EvidenceGenerator

logger = structlog.get_logger()

TOPICS = ['graph.updates', 'temporal.updates']


def get_pg_engine():
    pg_url = os.environ.get(
        "DATABASE_URL",
        "postgresql://sentinel_user:sentinel_password@postgres:5432/sentinelgraph"
    )
    if pg_url.startswith("postgresql+asyncpg://"):
        pg_url = pg_url.replace("postgresql+asyncpg://", "postgresql://")
    return create_engine(
        pg_url,
        pool_size=5,
        max_overflow=5,
        pool_pre_ping=True
    )


def parse_datetime(val: Any) -> datetime:
    if isinstance(val, datetime):
        dt = val
    elif val:
        s = str(val).replace('Z', '+00:00')
        dt = datetime.fromisoformat(s)
    else:
        dt = datetime.now(timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def compute_overall_risk(tx_risk: float, net_risk: float, temp_risk: float) -> tuple[float, str]:
    """Aggregate risk signals: 0.50*tx + 0.30*net + 0.20*temp, clamp to [0,1], return tier."""
    score = 0.50 * float(tx_risk) + 0.30 * float(net_risk) + 0.20 * float(temp_risk)
    clamped = float(np.clip(score, 0.0, 1.0))
    if clamped >= 0.80:
        tier = "CRITICAL"
    elif clamped >= 0.60:
        tier = "HIGH"
    elif clamped >= 0.30:
        tier = "MEDIUM"
    else:
        tier = "LOW"
    return round(clamped, 4), tier


def main():
    kafka_brokers = os.environ.get("KAFKA_BROKERS", "kafka:9092")
    
    conf = {
        'bootstrap.servers': kafka_brokers,
        'group.id': 'case-worker',
        'auto.offset.reset': 'earliest',
        'enable.auto.commit': False
    }
    
    consumer = Consumer(conf)
    consumer.subscribe(TOPICS)
    
    engine = get_pg_engine()
    evidence_gen = EvidenceGenerator()
    
    running = True

    def shutdown(signum, frame):
        nonlocal running
        logger.info("shutting_down_case_worker")
        running = False

    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)

    logger.info("case_worker_started", brokers=kafka_brokers, topics=TOPICS)

    while running:
        msg = consumer.poll(timeout=1.0)
        
        if msg is None:
            continue
        if msg.error():
            if msg.error().code() == KafkaError._PARTITION_EOF:
                continue
            else:
                logger.error("kafka_error", error=str(msg.error()))
                continue

        try:
            val = msg.value().decode('utf-8')
            event = json.loads(val)
        except Exception as e:
            logger.error("malformed_event_json", error=str(e))
            consumer.commit(msg, asynchronous=False)
            continue

        # 1. Normalize identifiers
        raw_cust = event.get("customer_id")
        if not raw_cust and event.get("entity_type") == "customer":
            raw_cust = event.get("entity_id")
        if not raw_cust:
            raw_cust = event.get("entity_id")

        if not raw_cust:
            logger.warning("skipping_event_no_customer_id", event=event)
            consumer.commit(msg, asynchronous=False)
            continue

        try:
            cust_id = uuid.UUID(str(raw_cust))
        except Exception as e:
            logger.warning("invalid_customer_uuid", customer_id=raw_cust, error=str(e))
            consumer.commit(msg, asynchronous=False)
            continue

        raw_tx = event.get("transaction_id") or event.get("id")
        tx_id = None
        if raw_tx:
            try:
                tx_id = uuid.UUID(str(raw_tx))
            except Exception:
                tx_id = None

        event_time = parse_datetime(event.get("detected_at") or event.get("updated_at") or event.get("occurred_at"))

        try:
            with engine.connect() as conn:
                # 2. Transaction Risk Signal (risk_predictions WHERE predicted_at <= event_time)
                tx_risk = 0.0
                if tx_id:
                    q_tx_pred = text("""
                        SELECT risk_score, risk_tier
                        FROM risk_predictions
                        WHERE transaction_id = :tx_id
                          AND predicted_at <= :event_time
                        ORDER BY predicted_at DESC
                        LIMIT 1;
                    """)
                    row = conn.execute(q_tx_pred, {"tx_id": tx_id, "event_time": event_time}).first()
                    if row:
                        tx_risk = float(row[0])

                if tx_risk == 0.0:
                    # Fallback to customer's most recent transaction risk prediction
                    q_cust_pred = text("""
                        SELECT rp.risk_score, t.transaction_id
                        FROM risk_predictions rp
                        JOIN transactions t ON rp.transaction_id = t.transaction_id
                        WHERE t.customer_id = :cust_id
                          AND rp.predicted_at <= :event_time
                        ORDER BY rp.predicted_at DESC
                        LIMIT 1;
                    """)
                    row = conn.execute(q_cust_pred, {"cust_id": cust_id, "event_time": event_time}).first()
                    if row:
                        tx_risk = float(row[0])
                        if not tx_id:
                            tx_id = uuid.UUID(str(row[1]))

                # 3. Network Risk Signal
                net_risk = 0.0
                graph_stats: Dict[str, Any] = {}
                if "graph_risk_score" in event:
                    net_risk = float(event.get("graph_risk_score", 0.0))
                    graph_stats = {
                        'node_count': event.get('node_count', 0),
                        'edge_count': event.get('edge_count', 0),
                        'network_density': event.get('network_density', 0.0),
                        'network_growth': event.get('edge_count', 0)
                    }
                else:
                    q_net = text("""
                        SELECT graph_risk_score, node_count, edge_count, network_density
                        FROM network_risks
                        WHERE network_id = :cust_id
                          AND detected_at <= :event_time
                        ORDER BY detected_at DESC
                        LIMIT 1;
                    """)
                    row = conn.execute(q_net, {"cust_id": cust_id, "event_time": event_time}).first()
                    if row:
                        net_risk = float(row[0])
                        graph_stats = {
                            'node_count': int(row[1]),
                            'edge_count': int(row[2]),
                            'network_density': float(row[3]),
                            'network_growth': int(row[2])
                        }

                # 4. Temporal Risk Signal
                temp_risk = 0.0
                anomalies_list = []
                if "temporal_risk_score" in event:
                    temp_risk = float(event.get("temporal_risk_score", 0.0))
                    anomalies_list = event.get("anomalies", [])
                else:
                    q_temp = text("""
                        SELECT anomaly_id, anomaly_type, baseline_value, observed_value, anomaly_score, window_start, window_end, detected_at
                        FROM temporal_anomalies
                        WHERE entity_id = :cust_id
                          AND detected_at <= :event_time
                        ORDER BY detected_at DESC
                        LIMIT 10;
                    """)
                    rows = conn.execute(q_temp, {"cust_id": cust_id, "event_time": event_time}).fetchall()
                    if rows:
                        for r in rows:
                            anomalies_list.append({
                                'anomaly_id': str(r[0]),
                                'anomaly_type': str(r[1]),
                                'baseline_value': float(r[2]) if r[2] is not None else 0.0,
                                'observed_value': float(r[3]) if r[3] is not None else 0.0,
                                'anomaly_score': float(r[4]),
                                'window_start': r[5].isoformat() if r[5] else None,
                                'window_end': r[6].isoformat() if r[6] else None,
                                'detected_at': r[7].isoformat() if r[7] else None
                            })
                        max_score = max(a['anomaly_score'] for a in anomalies_list)
                        temp_risk = round(min(1.0, max_score / 5.0), 4)

            # 5. Risk Aggregation & Classification
            overall_score, risk_tier = compute_overall_risk(tx_risk, net_risk, temp_risk)

            # 6. Case Creation Policy (Only create/update if overall_score >= 0.60)
            if overall_score < 0.60:
                logger.info(
                    "below_case_threshold",
                    customer_id=str(cust_id),
                    overall_risk=overall_score,
                    risk_tier=risk_tier
                )
                consumer.commit(msg, asynchronous=False)
                continue

            # 7. Check Cooldown Deduplication
            with engine.begin() as conn:
                q_cooldown = text("""
                    SELECT case_id, created_at, status
                    FROM risk_cases
                    WHERE primary_entity_type = 'customer'
                      AND primary_entity_id = :cust_id
                      AND status = 'open'
                      AND created_at >= :event_time - INTERVAL '24 hours'
                    ORDER BY created_at DESC
                    LIMIT 1;
                """)
                existing_case = conn.execute(q_cooldown, {
                    "cust_id": cust_id,
                    "event_time": event_time
                }).first()

                if existing_case:
                    target_case_id = uuid.UUID(str(existing_case[0]))
                    is_new_case = False
                else:
                    target_case_id = uuid.uuid4()
                    is_new_case = True

                # 8. Generate Evidence
                evidence_records = evidence_gen.generate_evidence(
                    case_id=target_case_id,
                    graph_stats=graph_stats,
                    temporal_anomalies=anomalies_list,
                    shap_features=None,
                    entity_id=cust_id,
                    entity_type='customer'
                )

                # Fallback evidence if none generated by rubrics
                if not evidence_records:
                    ev_id = evidence_gen.generate_deterministic_evidence_id(
                        target_case_id, 'overall_risk', cust_id, f"risk:{overall_score}:{risk_tier}"
                    )
                    evidence_records.append({
                        'evidence_id': ev_id,
                        'case_id': target_case_id,
                        'evidence_type': 'risk_score',
                        'entity_type': 'customer',
                        'entity_id': cust_id,
                        'description': f"Elevated aggregate risk score: {overall_score:.2f} ({risk_tier} tier)",
                        'severity': risk_tier,
                        'evidence_data': {
                            'overall_risk_score': overall_score,
                            'transaction_risk': tx_risk,
                            'network_risk': net_risk,
                            'temporal_risk': temp_risk
                        },
                        'created_at': datetime.now(timezone.utc)
                    })

                now_utc = datetime.now(timezone.utc)

                # 9. Atomic Transactional Persistence
                if is_new_case:
                    case_reason = f"Automated risk detection triggered {risk_tier} risk tier (score: {overall_score:.2f})"
                    ins_case = text("""
                        INSERT INTO risk_cases (
                            case_id, primary_entity_type, primary_entity_id,
                            transaction_risk_score, network_risk_score, temporal_risk_score,
                            overall_risk_score, risk_tier, status, case_reason,
                            created_at, updated_at
                        ) VALUES (
                            :case_id, 'customer', :cust_id,
                            :tx_risk, :net_risk, :temp_risk,
                            :overall_score, :risk_tier, 'open', :case_reason,
                            :now_utc, :now_utc
                        );
                    """)
                    conn.execute(ins_case, {
                        "case_id": target_case_id,
                        "cust_id": cust_id,
                        "tx_risk": tx_risk,
                        "net_risk": net_risk,
                        "temp_risk": temp_risk,
                        "overall_score": overall_score,
                        "risk_tier": risk_tier,
                        "case_reason": case_reason,
                        "now_utc": now_utc
                    })

                    # Case Entities
                    q_entities = text("""
                        SELECT transaction_id, merchant_id, device_id, instrument_id, ip_id
                        FROM transactions
                        WHERE customer_id = :cust_id
                          AND occurred_at <= :event_time
                        ORDER BY occurred_at DESC
                        LIMIT 1;
                    """)
                    tx_row = conn.execute(q_entities, {"cust_id": cust_id, "event_time": event_time}).first()

                    ins_entity = text("""
                        INSERT INTO case_entities (case_id, entity_type, entity_id, role, added_at)
                        VALUES (:case_id, :entity_type, :entity_id, :role, :now_utc);
                    """)
                    # Link customer
                    conn.execute(ins_entity, {
                        "case_id": target_case_id,
                        "entity_type": "customer",
                        "entity_id": cust_id,
                        "role": "primary_suspect",
                        "now_utc": now_utc
                    })

                    if tx_row:
                        if tx_row[0]:
                            conn.execute(ins_entity, {"case_id": target_case_id, "entity_type": "transaction", "entity_id": tx_row[0], "role": "trigger_transaction", "now_utc": now_utc})
                        if tx_row[1]:
                            conn.execute(ins_entity, {"case_id": target_case_id, "entity_type": "merchant", "entity_id": tx_row[1], "role": "target_merchant", "now_utc": now_utc})
                        if tx_row[2]:
                            conn.execute(ins_entity, {"case_id": target_case_id, "entity_type": "device", "entity_id": tx_row[2], "role": "associated_device", "now_utc": now_utc})
                        if tx_row[3]:
                            conn.execute(ins_entity, {"case_id": target_case_id, "entity_type": "instrument", "entity_id": tx_row[3], "role": "payment_instrument", "now_utc": now_utc})
                        if tx_row[4]:
                            conn.execute(ins_entity, {"case_id": target_case_id, "entity_type": "ip", "entity_id": tx_row[4], "role": "associated_ip", "now_utc": now_utc})

                    # Audit log for creation
                    ins_audit = text("""
                        INSERT INTO audit_logs (audit_id, actor_type, actor_id, action, resource_type, resource_id, metadata, created_at)
                        VALUES (:audit_id, 'SYSTEM', 'case-worker', 'CREATE_CASE', 'CASE', :res_id, :meta, :now_utc);
                    """)
                    conn.execute(ins_audit, {
                        "audit_id": uuid.uuid4(),
                        "res_id": str(target_case_id),
                        "meta": json.dumps({"overall_risk_score": overall_score, "risk_tier": risk_tier}),
                        "now_utc": now_utc
                    })

                else:
                    # Update existing case
                    upd_case = text("""
                        UPDATE risk_cases
                        SET updated_at = :now_utc,
                            overall_risk_score = GREATEST(overall_risk_score, :overall_score),
                            transaction_risk_score = GREATEST(transaction_risk_score, :tx_risk),
                            network_risk_score = GREATEST(network_risk_score, :net_risk),
                            temporal_risk_score = GREATEST(temporal_risk_score, :temp_risk)
                        WHERE case_id = :case_id;
                    """)
                    conn.execute(upd_case, {
                        "now_utc": now_utc,
                        "overall_score": overall_score,
                        "tx_risk": tx_risk,
                        "net_risk": net_risk,
                        "temp_risk": temp_risk,
                        "case_id": target_case_id
                    })

                    # Audit log for append
                    ins_audit = text("""
                        INSERT INTO audit_logs (audit_id, actor_type, actor_id, action, resource_type, resource_id, metadata, created_at)
                        VALUES (:audit_id, 'SYSTEM', 'case-worker', 'APPEND_EVIDENCE', 'CASE', :res_id, :meta, :now_utc);
                    """)
                    conn.execute(ins_audit, {
                        "audit_id": uuid.uuid4(),
                        "res_id": str(target_case_id),
                        "meta": json.dumps({"overall_risk_score": overall_score, "evidence_appended": len(evidence_records)}),
                        "now_utc": now_utc
                    })

                # Insert evidence records with deduplication
                ins_evidence = text("""
                    INSERT INTO case_evidence (
                        evidence_id, case_id, evidence_type, entity_type, entity_id,
                        description, severity, evidence_data, created_at
                    ) VALUES (
                        :evidence_id, :case_id, :evidence_type, :entity_type, :entity_id,
                        :description, :severity, :evidence_data, :created_at
                    )
                    ON CONFLICT (evidence_id) DO NOTHING;
                """)
                for ev in evidence_records:
                    conn.execute(ins_evidence, {
                        "evidence_id": ev['evidence_id'],
                        "case_id": ev['case_id'],
                        "evidence_type": ev['evidence_type'],
                        "entity_type": ev['entity_type'],
                        "entity_id": ev['entity_id'],
                        "description": ev['description'],
                        "severity": ev['severity'],
                        "evidence_data": json.dumps(ev.get('evidence_data', {})),
                        "created_at": ev['created_at']
                    })

            # 10. Commit Kafka offset
            consumer.commit(msg, asynchronous=False)

            logger.info(
                "processed_case_event",
                case_id=str(target_case_id),
                is_new_case=is_new_case,
                customer_id=str(cust_id),
                overall_risk=overall_score,
                risk_tier=risk_tier,
                evidence_count=len(evidence_records)
            )

        except Exception as e:
            logger.error("case_processing_error", customer_id=str(cust_id), error=str(e))
            # On database or processing failure, rollback is automatic; do not commit Kafka offset
            continue

    consumer.close()
    engine.dispose()
    logger.info("case_worker_shutdown_complete")


if __name__ == "__main__":
    main()
