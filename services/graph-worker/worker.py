import asyncio
import json
import os
import signal
import sys
from datetime import datetime, timezone
from confluent_kafka import Consumer, Producer, KafkaException
import structlog
from pydantic import BaseModel, Field
import uuid

from neo4j_ops import Neo4jGraphOps
from pg_ops import upsert_entity_relationships, insert_network_risk

logger = structlog.get_logger()

KAFKA_BROKERS = os.getenv('KAFKA_BROKERS', 'localhost:9092')
NEO4J_URI = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
NEO4J_USER = os.getenv('NEO4J_USER', 'neo4j')
NEO4J_PASSWORD = os.getenv('NEO4J_PASSWORD', 'password')
PG_URL = os.getenv('DATABASE_URL', 'postgresql://postgres:postgres@localhost:5432/sentinelgraph')
if PG_URL.startswith('postgresql+asyncpg://'):
    PG_URL = PG_URL.replace('postgresql+asyncpg://', 'postgresql://')

TOPIC_PAYMENT_EVENTS = 'payment.events'
TOPIC_GRAPH_UPDATES = 'graph.updates'

class GraphUpdate(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    entity_type: str
    entity_id: uuid.UUID
    network_id: str | None = None
    node_count: int = 0
    edge_count: int = 0
    network_density: float = 0.0
    graph_risk_score: float = 0.0
    updated_at: datetime

class Worker:
    def __init__(self):
        self.consumer = Consumer({
            'bootstrap.servers': KAFKA_BROKERS,
            'group.id': 'graph-worker-group',
            'auto.offset.reset': 'earliest'
        })
        self.producer = Producer({
            'bootstrap.servers': KAFKA_BROKERS,
            'client.id': 'graph-worker-producer'
        })
        self.neo4j_ops = Neo4jGraphOps(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
        self.running = False
    
    def _publish_update(self, update: GraphUpdate):
        try:
            self.producer.produce(
                topic=TOPIC_GRAPH_UPDATES,
                key=str(update.entity_id).encode('utf-8'),
                value=update.model_dump_json().encode('utf-8')
            )
            self.producer.poll(0)
        except Exception as e:
            logger.error('failed_to_publish_graph_update', error=str(e))
            
    async def process_event(self, event: dict):
        try:
            # 1. Update Neo4j Graph
            await self.neo4j_ops.merge_transaction_graph(event)
            
            # 2. Upsert Postgres relationships
            upsert_entity_relationships(PG_URL, event)
            
            # 3. Compute Connected Component Stats
            customer_id = event.get('customer_id')
            if customer_id:
                stats = await self.neo4j_ops.get_customer_network_stats(customer_id)
                
                update = GraphUpdate(
                    entity_type='customer',
                    entity_id=uuid.UUID(customer_id),
                    network_id=customer_id,
                    node_count=stats['node_count'],
                    edge_count=stats['edge_count'],
                    network_density=stats['density'],
                    graph_risk_score=0.0, # Placeholder
                    updated_at=datetime.now(timezone.utc)
                )
                
                # 4. Insert Network Risk to Postgres
                insert_network_risk(PG_URL, json.loads(update.model_dump_json()))
                
                # 5. Publish to Kafka
                self._publish_update(update)
                
        except Exception as e:
            logger.error('failed_to_process_event', event_id=event.get('event_id'), error=str(e))
            # Basic DLQ: Log to file
            with open('dlq.log', 'a') as f:
                f.write(json.dumps({'event': event, 'error': str(e)}) + '\n')

    async def run(self):
        self.running = True
        self.consumer.subscribe([TOPIC_PAYMENT_EVENTS])
        logger.info('graph_worker_started')
        
        while self.running:
            msg = self.consumer.poll(1.0)
            if msg is None:
                await asyncio.sleep(0.1)
                continue
            if msg.error():
                logger.error('kafka_consumer_error', error=str(msg.error()))
                continue
            
            try:
                event_data = json.loads(msg.value().decode('utf-8'))
                await self.process_event(event_data)
            except Exception as e:
                logger.error('kafka_message_decode_failed', error=str(e))

        self.consumer.close()
        self.producer.flush()
        await self.neo4j_ops.close()
        logger.info('graph_worker_stopped')

    def stop(self):
        self.running = False


worker_instance = None

def signal_handler(sig, frame):
    logger.info('shutting_down_graph_worker')
    if worker_instance:
        worker_instance.stop()

if __name__ == '__main__':
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    worker_instance = Worker()
    asyncio.run(worker_instance.run())
