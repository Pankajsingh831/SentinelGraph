import json
from confluent_kafka import Producer
import structlog
from pydantic import BaseModel
from app.config import get_settings

logger = structlog.get_logger()

class KafkaProducer:
    TOPIC_PAYMENT_EVENTS = 'payment.events'
    TOPIC_GRAPH_UPDATES = 'graph.updates'
    TOPIC_TEMPORAL_UPDATES = 'temporal.updates'
    
    def __init__(self):
        settings = get_settings()
        self.producer = Producer({
            'bootstrap.servers': settings.KAFKA_BROKERS,
            'client.id': 'sentinelgraph-api',
            'acks': 'all',
            'retries': 3,
            'linger.ms': 5,
        })
    
    def publish(self, topic: str, key: str, event: BaseModel):
        """Publish a Pydantic event to a Kafka topic."""
        try:
            self.producer.produce(
                topic=topic,
                key=key.encode('utf-8'),
                value=event.model_dump_json().encode('utf-8'),
                callback=self._delivery_callback
            )
            self.producer.poll(0)
        except Exception as e:
            logger.error('kafka_publish_failed', topic=topic, error=str(e))
    
    def _delivery_callback(self, err, msg):
        if err:
            logger.error('kafka_delivery_failed', error=str(err))
    
    def flush(self):
        self.producer.flush(timeout=10.0)

# Singleton
_producer = None
def get_producer() -> KafkaProducer:
    global _producer
    if _producer is None:
        _producer = KafkaProducer()
    return _producer
