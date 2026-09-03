import asyncio
from neo4j import AsyncGraphDatabase
from app.config import get_settings

async def check():
    settings = get_settings()
    driver = AsyncGraphDatabase.driver(settings.NEO4J_URI, auth=(settings.NEO4J_USERNAME, settings.NEO4J_PASSWORD))
    
    tids = ['ea4589e0-8bb6-42ae-a88f-093b05bb07a1', 'd552ac26-3908-4358-864c-a15d3ad8b1ca']
    for tid in tids:
        cypher = "MATCH (t:Transaction {id: $tid}) OPTIONAL MATCH (t)-[r]-(n) RETURN t, type(r) as rel_type, labels(n) as labels, n.id as nid"
        res, _, _ = await driver.execute_query(cypher, tid=tid)
        print(f"Transaction {tid} records in Neo4j: {len(res)}")
        for r in res:
            print(f"  rel: {r['rel_type']}, target: {r['labels']}, target_id: {r['nid']}")
            
    # Also check how many total transactions for customer 5c5001a1 exist in Neo4j:
    cypher_cust = "MATCH (c:Customer {id: $cid})-[:MADE]->(t:Transaction) RETURN count(t) as total_txs, collect(t.id)[0..5] as sample_tids"
    res_c, _, _ = await driver.execute_query(cypher_cust, cid='5c5001a1-887e-45e7-8ae8-f1c53fa808b0')
    print("Customer 5c5001a1 total transactions in Neo4j:", res_c[0]['total_txs'])
    print("Sample transaction IDs in Neo4j:", res_c[0]['sample_tids'])
    
    await driver.close()

asyncio.run(check())
