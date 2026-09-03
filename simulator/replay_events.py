import os
import sys
import json
import uuid
import datetime
import decimal
import argparse
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from confluent_kafka import Producer

def json_serializer(obj):
    if isinstance(obj, uuid.UUID):
        return str(obj)
    if isinstance(obj, datetime.datetime):
        return obj.isoformat()
    if isinstance(obj, decimal.Decimal):
        return float(obj)
    raise TypeError(f"Type {type(obj)} not serializable")

async def replay_events(limit=None, offset=0, topic='payment.events', dry_run=False):
    db_url = os.environ.get(
        'DATABASE_URL',
        'postgresql+asyncpg://sentinel_user:sentinel_pass@postgres:5432/sentinelgraph'
    )
    if db_url.startswith('postgresql://'):
        db_url = db_url.replace('postgresql://', 'postgresql+asyncpg://')

    kafka_broker = os.environ.get('KAFKA_BOOTSTRAP_SERVERS', 'kafka:9092')

    engine = create_async_engine(db_url)
    
    producer = None
    if not dry_run:
        producer = Producer({
            'bootstrap.servers': kafka_broker,
            'client.id': 'simulator-replay'
        })
    
    query = """
        SELECT transaction_id, customer_id, merchant_id, device_id, instrument_id, ip_id, amount, occurred_at
        FROM transactions
        ORDER BY occurred_at ASC
    """
    if limit is not None:
        query += f" LIMIT {limit} OFFSET {offset}"

    print(f"Connecting to database to fetch transactions (Limit: {limit or 'All'}, Offset: {offset})...")
    
    count = 0
    async with engine.connect() as conn:
        result = await conn.execute(text(query))
        
        for row in result:
            row_dict = row._mapping
            event = {
                'transaction_id': row_dict['transaction_id'],
                'customer_id': row_dict['customer_id'],
                'merchant_id': row_dict['merchant_id'],
                'device_id': row_dict['device_id'],
                'instrument_id': row_dict['instrument_id'],
                'ip_id': row_dict['ip_id'],
                'amount': row_dict['amount'],
                'occurred_at': row_dict['occurred_at']
            }
            
            payload = json.dumps(event, default=json_serializer)
            
            if dry_run:
                if count < 5:
                    print(payload)
            else:
                producer.produce(topic, value=payload)
                producer.poll(0)
                
            count += 1
            if count % 1000 == 0:
                if not dry_run:
                    producer.flush()
                print(f"Replayed {count} events...")
                
    if not dry_run:
        producer.flush()
    print(f"Finished replaying {count} events.")

def main():
    parser = argparse.ArgumentParser(description="Replay simulated transactions to Kafka")
    parser.add_argument('--limit', type=int, default=None, help='Maximum number of transactions to replay')
    parser.add_argument('--offset', type=int, default=0, help='Offset for transaction replay')
    parser.add_argument('--topic', type=str, default='payment.events', help='Kafka topic')
    parser.add_argument('--dry-run', action='store_true', help='Print events without publishing')
    args = parser.parse_args()

    asyncio.run(replay_events(
        limit=args.limit,
        offset=args.offset,
        topic=args.topic,
        dry_run=args.dry_run
    ))

if __name__ == '__main__':
    main()
