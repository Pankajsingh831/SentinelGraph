import json
import os
import signal
import sys
import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List
from confluent_kafka import Consumer, Producer, KafkaError, KafkaException
from sqlalchemy import create_engine, text
import structlog
import numpy as np

from anomaly_detector import TemporalAnomalyDetector

logger = structlog.get_logger()

TOPIC_PAYMENT_EVENTS = os.environ.get("KAFKA_INPUT_TOPIC", "payment.events")
TOPIC_TEMPORAL_UPDATES = os.environ.get("KAFKA_OUTPUT_TOPIC", "temporal.updates")


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
    else:
        s = str(val).replace('Z', '+00:00')
        dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def extract_features_and_baselines(tx_list: List[Dict[str, Any]], event_time: datetime, current_amount: float, detector: TemporalAnomalyDetector):
    """Compute 5m, 1h, 24h rolling observation counts and historical baselines up to event_time."""
    # Ensure all timestamps have timezone
    for tx in tx_list:
        if tx['occurred_at'].tzinfo is None:
            tx['occurred_at'] = tx['occurred_at'].replace(tzinfo=timezone.utc)

    # Filter to transactions within observation windows
    w5m = [tx for tx in tx_list if event_time - timedelta(minutes=5) <= tx['occurred_at'] <= event_time]
    w1h = [tx for tx in tx_list if event_time - timedelta(hours=1) <= tx['occurred_at'] <= event_time]
    w24h = [tx for tx in tx_list if event_time - timedelta(hours=24) <= tx['occurred_at'] <= event_time]

    tx_count_5m = len(w5m)
    tx_count_1h = len(w1h)
    tx_count_24h = len(w24h)

    refund_count_24h = sum(1 for tx in w24h if str(tx.get('transaction_type', '')).lower() == 'refund')
    refund_rate = (refund_count_24h / tx_count_24h) if tx_count_24h > 0 else 0.0

    amounts_24h = [float(tx['amount']) for tx in w24h]
    avg_amount = float(np.mean(amounts_24h)) if amounts_24h else float(current_amount)

    current_stats = {
        'tx_count_5m': tx_count_5m,
        'tx_count_1h': tx_count_1h,
        'tx_count_24h': tx_count_24h,
        'refund_rate': refund_rate,
        'avg_amount': avg_amount,
        'amount': float(current_amount)
    }

    # Baselines from history strictly before the current 24-hour observation window
    prior_txs = [tx for tx in tx_list if tx['occurred_at'] < event_time - timedelta(hours=24)]
    prior_amounts = [float(tx['amount']) for tx in tx_list if tx['occurred_at'] < event_time]

    if prior_txs:
        # Group prior transactions into daily buckets
        day_buckets: Dict[str, int] = {}
        for tx in prior_txs:
            day_key = tx['occurred_at'].strftime('%Y-%m-%d')
            day_buckets[day_key] = day_buckets.get(day_key, 0) + 1
        
        daily_counts = list(day_buckets.values())
        b_24h = detector.compute_baseline_stats(daily_counts)
        mean_tx_24h = b_24h['mean']
        std_tx_24h = b_24h['std']
        mean_tx_1h = max(0.1, mean_tx_24h / 24.0)
        std_tx_1h = max(0.2, std_tx_24h / 12.0)
        mean_tx_5m = max(0.05, mean_tx_24h / 288.0)
        std_tx_5m = max(0.1, std_tx_24h / 24.0)
    else:
        # Defaults for customer with no long-term history
        mean_tx_24h = 1.0
        std_tx_24h = 1.0
        mean_tx_1h = 0.5
        std_tx_1h = 1.0
        mean_tx_5m = 0.1
        std_tx_5m = 0.5

    if len(prior_amounts) >= 3:
        b_amt = detector.compute_baseline_stats(prior_amounts)
        mean_amount = b_amt['mean']
        std_amount = b_amt['std']
        amount_sample_count = len(prior_amounts)
    else:
        mean_amount = float(current_amount)
        std_amount = 1.0
        amount_sample_count = len(prior_amounts)

    baseline_stats = {
        'mean_tx_5m': mean_tx_5m,
        'std_tx_5m': std_tx_5m,
        'mean_tx_1h': mean_tx_1h,
        'std_tx_1h': std_tx_1h,
        'mean_tx_24h': mean_tx_24h,
        'std_tx_24h': std_tx_24h,
        'mean_refund_rate': 0.0,
        'std_refund_rate': 0.1,
        'mean_amount': mean_amount,
        'std_amount': std_amount,
        'amount_sample_count': amount_sample_count
    }

    return current_stats, baseline_stats


def main():
    kafka_brokers = os.environ.get("KAFKA_BROKERS", "kafka:9092")
    
    consumer = Consumer({
        'bootstrap.servers': kafka_brokers,
        'group.id': 'temporal-worker',
        'auto.offset.reset': 'earliest',
        'enable.auto.commit': False
    })
    consumer.subscribe([TOPIC_PAYMENT_EVENTS])
    
    producer = Producer({
        'bootstrap.servers': kafka_brokers,
        'client.id': 'temporal-worker-producer'
    })
    
    engine = get_pg_engine()
    detector = TemporalAnomalyDetector()
    
    running = True

    def shutdown(signum, frame):
        nonlocal running
        logger.info("shutting_down_temporal_worker")
        running = False

    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)

    logger.info("temporal_worker_started", brokers=kafka_brokers, input_topic=TOPIC_PAYMENT_EVENTS, output_topic=TOPIC_TEMPORAL_UPDATES)

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

        # Extract event fields
        tx_id = event.get("transaction_id") or event.get("id")
        cust_id = event.get("customer_id")
        raw_occurred = event.get("occurred_at")
        amount = event.get("amount", 0.0)

        if not tx_id or not cust_id or not raw_occurred:
            logger.error("missing_required_event_fields", event=event)
            consumer.commit(msg, asynchronous=False)
            continue

        try:
            event_time = parse_datetime(raw_occurred)
            amt = float(amount)
        except Exception as e:
            logger.error("invalid_field_values", error=str(e), event=event)
            consumer.commit(msg, asynchronous=False)
            continue

        try:
            # 1. Query historical transactions up to event_time
            query = text("""
                SELECT transaction_id, transaction_type, amount, occurred_at
                FROM transactions
                WHERE customer_id = :cust_id
                  AND occurred_at <= :event_time
                ORDER BY occurred_at ASC;
            """)
            
            tx_list = []
            with engine.connect() as conn:
                res = conn.execute(query, {
                    "cust_id": str(cust_id),
                    "event_time": event_time
                })
                for row in res:
                    tx_list.append({
                        'transaction_id': str(row[0]),
                        'transaction_type': str(row[1]),
                        'amount': float(row[2]),
                        'occurred_at': row[3]
                    })

            # Ensure current event is included at event_time
            tx_id_str = str(tx_id)
            if not any(tx['transaction_id'] == tx_id_str for tx in tx_list):
                tx_list.append({
                    'transaction_id': tx_id_str,
                    'transaction_type': 'sale',
                    'amount': amt,
                    'occurred_at': event_time
                })
                tx_list.sort(key=lambda x: x['occurred_at'])

            # 2. Extract features and baselines
            current_stats, baseline_stats = extract_features_and_baselines(tx_list, event_time, amt, detector)

            # 3. Detect anomalies
            anomalies = detector.detect_anomalies(
                entity_id=str(cust_id),
                entity_type='customer',
                current_stats=current_stats,
                baseline_stats=baseline_stats,
                window_start=event_time - timedelta(hours=24),
                window_end=event_time
            )

            # 4. Database Persistence (transactional)
            if anomalies:
                insert_stmt = text("""
                    INSERT INTO temporal_anomalies (
                        anomaly_id, entity_type, entity_id, anomaly_type,
                        baseline_value, observed_value, anomaly_score,
                        window_start, window_end, detected_at
                    ) VALUES (
                        :anomaly_id, :entity_type, :entity_id, :anomaly_type,
                        :baseline_value, :observed_value, :anomaly_score,
                        :window_start, :window_end, :detected_at
                    )
                    ON CONFLICT (anomaly_id) DO NOTHING;
                """)
                with engine.begin() as conn:
                    for a in anomalies:
                        conn.execute(insert_stmt, {
                            'anomaly_id': a['anomaly_id'],
                            'entity_type': a['entity_type'],
                            'entity_id': a['entity_id'],
                            'anomaly_type': a['anomaly_type'],
                            'baseline_value': a['baseline_value'],
                            'observed_value': a['observed_value'],
                            'anomaly_score': a['anomaly_score'],
                            'window_start': a['window_start'],
                            'window_end': a['window_end'],
                            'detected_at': a['detected_at']
                        })

            # 5. Kafka Output Publish
            max_score = max([a['anomaly_score'] for a in anomalies], default=0.0)
            temporal_risk_score = round(min(1.0, max_score / 5.0), 4) if anomalies else 0.0

            update_payload = {
                "id": str(uuid.uuid4()),
                "event_id": str(uuid.uuid4()),
                "transaction_id": tx_id_str,
                "customer_id": str(cust_id),
                "entity_type": "customer",
                "entity_id": str(cust_id),
                "anomaly_type": anomalies[0]['anomaly_type'] if anomalies else None,
                "anomaly_types": [a['anomaly_type'] for a in anomalies],
                "anomaly_score": max_score,
                "temporal_risk_score": temporal_risk_score,
                "anomalies": [
                    {
                        "anomaly_id": str(a['anomaly_id']),
                        "anomaly_type": a['anomaly_type'],
                        "baseline_value": a['baseline_value'],
                        "observed_value": a['observed_value'],
                        "anomaly_score": a['anomaly_score'],
                        "window_start": a['window_start'].isoformat(),
                        "window_end": a['window_end'].isoformat(),
                        "detected_at": a['detected_at'].isoformat()
                    }
                    for a in anomalies
                ],
                "detected_at": datetime.now(timezone.utc).isoformat()
            }

            def delivery_report(err, msg):
                if err is not None:
                    logger.error("failed_to_deliver_temporal_update", error=str(err))

            producer.produce(
                TOPIC_TEMPORAL_UPDATES,
                key=str(cust_id).encode('utf-8'),
                value=json.dumps(update_payload).encode('utf-8'),
                on_delivery=delivery_report
            )
            producer.poll(0)

            # 6. Commit consumer offset
            consumer.commit(msg, asynchronous=False)

            logger.info(
                "processed_temporal_event",
                transaction_id=tx_id_str,
                customer_id=str(cust_id),
                anomalies_detected=len(anomalies),
                temporal_risk_score=temporal_risk_score
            )

        except Exception as e:
            logger.error("processing_error", transaction_id=tx_id, error=str(e))
            # On unexpected operational errors, avoid tight loop by slight pause
            continue

    producer.flush()
    consumer.close()
    engine.dispose()
    logger.info("temporal_worker_shutdown_complete")


if __name__ == "__main__":
    main()
