from neo4j import AsyncGraphDatabase, AsyncDriver
import structlog

logger = structlog.get_logger()

class Neo4jGraphOps:
    def __init__(self, uri: str, user: str, password: str):
        self.driver = AsyncGraphDatabase.driver(uri, auth=(user, password))
    
    async def close(self):
        await self.driver.close()
    
    async def merge_transaction_graph(self, event: dict):
        """MERGE all nodes and relationships for a transaction event.
        
        Creates/updates:
        - Customer node
        - Merchant node  
        - Transaction node
        - Device node (if present)
        - PaymentInstrument node (if present)
        - IPAddress node (if present)
        - Relationships: (Customer)-[:MADE]->(Transaction)-[:PAID_TO]->(Merchant)
        - Relationships: (Transaction)-[:USED_DEVICE]->(Device) etc.
        - Relationships: (Customer)-[:USES]->(Device) etc.
        """
        async with self.driver.session() as session:
            # MERGE Customer
            await session.run(
                "MERGE (c:Customer {id: $customer_id}) SET c.updated_at = datetime()",
                customer_id=str(event['customer_id'])
            )
            # MERGE Merchant
            await session.run(
                "MERGE (m:Merchant {id: $merchant_id}) SET m.updated_at = datetime()",
                merchant_id=str(event['merchant_id'])
            )
            # MERGE Transaction
            await session.run(
                """MERGE (t:Transaction {id: $tx_id})
                   SET t.amount = $amount, t.occurred_at = datetime($occurred_at)""",
                tx_id=str(event['transaction_id']),
                amount=event['amount'],
                occurred_at=event['occurred_at'].isoformat() if hasattr(event['occurred_at'], 'isoformat') else event['occurred_at']
            )
            # MERGE Customer-MADE->Transaction
            await session.run(
                """MATCH (c:Customer {id: $cid}), (t:Transaction {id: $tid})
                   MERGE (c)-[:MADE]->(t)""",
                cid=str(event['customer_id']), tid=str(event['transaction_id'])
            )
            # MERGE Transaction-PAID_TO->Merchant
            await session.run(
                """MATCH (t:Transaction {id: $tid}), (m:Merchant {id: $mid})
                   MERGE (t)-[:PAID_TO]->(m)""",
                tid=str(event['transaction_id']), mid=str(event['merchant_id'])
            )
            # Device
            if event.get('device_id'):
                await session.run(
                    "MERGE (d:Device {id: $did}) SET d.updated_at = datetime()",
                    did=str(event['device_id'])
                )
                await session.run(
                    """MATCH (t:Transaction {id: $tid}), (d:Device {id: $did})
                       MERGE (t)-[:USED_DEVICE]->(d)""",
                    tid=str(event['transaction_id']), did=str(event['device_id'])
                )
                await session.run(
                    """MATCH (c:Customer {id: $cid}), (d:Device {id: $did})
                       MERGE (c)-[:USES]->(d)""",
                    cid=str(event['customer_id']), did=str(event['device_id'])
                )
            # PaymentInstrument
            if event.get('instrument_id'):
                await session.run(
                    "MERGE (i:PaymentInstrument {id: $iid}) SET i.updated_at = datetime()",
                    iid=str(event['instrument_id'])
                )
                await session.run(
                    """MATCH (t:Transaction {id: $tid}), (i:PaymentInstrument {id: $iid})
                       MERGE (t)-[:USED_INSTRUMENT]->(i)""",
                    tid=str(event['transaction_id']), iid=str(event['instrument_id'])
                )
                await session.run(
                    """MATCH (c:Customer {id: $cid}), (i:PaymentInstrument {id: $iid})
                       MERGE (c)-[:USES]->(i)""",
                    cid=str(event['customer_id']), iid=str(event['instrument_id'])
                )
            # IPAddress
            if event.get('ip_id'):
                await session.run(
                    "MERGE (ip:IPAddress {id: $ipid}) SET ip.updated_at = datetime()",
                    ipid=str(event['ip_id'])
                )
                await session.run(
                    """MATCH (t:Transaction {id: $tid}), (ip:IPAddress {id: $ipid})
                       MERGE (t)-[:FROM_IP]->(ip)""",
                    tid=str(event['transaction_id']), ipid=str(event['ip_id'])
                )
                await session.run(
                    """MATCH (c:Customer {id: $cid}), (ip:IPAddress {id: $ipid})
                       MERGE (c)-[:USES]->(ip)""",
                    cid=str(event['customer_id']), ipid=str(event['ip_id'])
                )
    
    async def get_customer_network_stats(self, customer_id: str) -> dict:
        """Get connected component stats for a customer's network."""
        # Find all nodes connected within 3 hops
        result = await self.driver.execute_query(
            """MATCH (c:Customer {id: $cid})
               OPTIONAL MATCH (c)-[*1..3]-(connected)
               WITH c, COLLECT(DISTINCT connected) AS connected_nodes
               WITH [c] + [x IN connected_nodes WHERE x IS NOT NULL] AS nodes
               UNWIND nodes AS n
               WITH nodes, n
               OPTIONAL MATCH (n)-[r]-(other) WHERE other IN nodes
               RETURN COUNT(DISTINCT n) AS node_count, 
                      COUNT(DISTINCT r) AS edge_count""",
            cid=customer_id,
            database_='neo4j'
        )
        if result.records:
            r = result.records[0]
            nc = r['node_count']
            ec = r['edge_count']
            density = (2 * ec) / (nc * (nc - 1)) if nc > 1 else 0.0
            return {'node_count': nc, 'edge_count': ec, 'density': density}
        return {'node_count': 1, 'edge_count': 0, 'density': 0.0}
