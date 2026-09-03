import asyncio
from neo4j import AsyncGraphDatabase
from app.config import get_settings

async def main():
    s = get_settings()
    d = AsyncGraphDatabase.driver(s.NEO4J_URI, auth=(s.NEO4J_USERNAME, s.NEO4J_PASSWORD))
    res, _, _ = await d.execute_query("MATCH (n) RETURN labels(n)[0] as l, count(*) as c ORDER BY c DESC")
    print("--- Neo4j Node Counts by Label ---")
    total_nodes = 0
    for r in res:
        print(f"  {r['l']}: {r['c']}")
        total_nodes += r['c']
    print(f"Total Nodes: {total_nodes}")
    
    r2, _, _ = await d.execute_query("MATCH ()-[r]->() RETURN type(r) as t, count(*) as c ORDER BY c DESC")
    print("\n--- Neo4j Relationship Counts by Type ---")
    total_edges = 0
    for r in r2:
        print(f"  {r['t']}: {r['c']}")
        total_edges += r['c']
    print(f"Total Relationships: {total_edges}")
    await d.close()

asyncio.run(main())
