import psycopg2
import structlog
from datetime import datetime

logger = structlog.get_logger()

def upsert_entity_relationships(db_url: str, event: dict):
    """
    For each entity pair in the transaction (customer-device, customer-IP, customer-instrument), 
    upsert into entity_relationships table.
    """
    try:
        with psycopg2.connect(db_url) as conn:
            with conn.cursor() as cur:
                occurred_at = event.get('occurred_at')
                if isinstance(occurred_at, str):
                    occurred_at = datetime.fromisoformat(occurred_at)
                    
                pairs = []
                customer_id = event.get('customer_id')
                
                if customer_id:
                    if event.get('device_id'):
                        pairs.append(('customer', customer_id, 'uses', 'device', event['device_id']))
                    if event.get('ip_id'):
                        pairs.append(('customer', customer_id, 'uses', 'ip', event['ip_id']))
                    if event.get('instrument_id'):
                        pairs.append(('customer', customer_id, 'uses', 'instrument', event['instrument_id']))

                import uuid
                for src_type, src_id, rel_type, dst_type, dst_id in pairs:
                    rel_id = str(uuid.uuid4())
                    cur.execute("""
                        INSERT INTO entity_relationships (
                            relationship_id, source_type, source_id, relationship_type, target_type, target_id, interaction_count, first_seen_at, last_seen_at
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, 1, %s, %s)
                        ON CONFLICT (source_type, source_id, relationship_type, target_type, target_id)
                        DO UPDATE SET 
                            interaction_count = entity_relationships.interaction_count + 1,
                            first_seen_at = LEAST(entity_relationships.first_seen_at, EXCLUDED.first_seen_at),
                            last_seen_at = GREATEST(entity_relationships.last_seen_at, EXCLUDED.last_seen_at);
                    """, (rel_id, src_type, str(src_id), rel_type, dst_type, str(dst_id), occurred_at, occurred_at))
            conn.commit()
    except Exception as e:
        logger.error('pg_upsert_relationships_failed', error=str(e))

def insert_network_risk(db_url: str, network_data: dict):
    """Insert/update network_risks table"""
    try:
        with psycopg2.connect(db_url) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO network_risks (
                        network_id, node_count, edge_count, 
                        network_density, community_id, graph_risk_score, detected_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (network_id)
                    DO UPDATE SET
                        node_count = EXCLUDED.node_count,
                        edge_count = EXCLUDED.edge_count,
                        network_density = EXCLUDED.network_density,
                        community_id = EXCLUDED.community_id,
                        graph_risk_score = EXCLUDED.graph_risk_score,
                        detected_at = EXCLUDED.detected_at;
                """, (
                    str(network_data['network_id']),
                    network_data.get('node_count', 0),
                    network_data.get('edge_count', 0),
                    network_data.get('network_density', 0.0),
                    network_data.get('community_id'),
                    network_data.get('graph_risk_score', 0.0),
                    network_data['updated_at']
                ))
            conn.commit()
    except Exception as e:
        logger.error('pg_insert_network_risk_failed', error=str(e))
