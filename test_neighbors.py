import asyncio
from neo4j import AsyncGraphDatabase
from app.config import get_settings

async def test():
    settings = get_settings()
    driver = AsyncGraphDatabase.driver(settings.NEO4J_URI, auth=(settings.NEO4J_USERNAME, settings.NEO4J_PASSWORD))
    
    for depth in [1, 2]:
        cypher = f"""
        MATCH (root:Customer {{id: $entity_id}})
        OPTIONAL MATCH path = (root)-[*1..{depth}]-(connected)
        WITH root, path
        LIMIT 50
        WITH root, collect(path) AS paths
        RETURN root, paths
        """
        res, _, _ = await driver.execute_query(cypher, entity_id='5c5001a1-887e-45e7-8ae8-f1c53fa808b0')
        if res and res[0]['root']:
            root = res[0]['root']
            paths = res[0]['paths']
            nodes = {root['id']: list(root.labels)[0]}
            edges = set()
            for p in paths:
                if p is None:
                    continue
                for n in p.nodes:
                    nodes[n['id']] = list(n.labels)[0]
                for r in p.relationships:
                    edges.add((r.start_node['id'], r.end_node['id'], r.type))
            print(f"Depth {depth}: {len(nodes)} nodes, {len(edges)} edges")
            print("  Node types:", set(nodes.values()))
            print("  Edge types:", {e[2] for e in edges})
            
    await driver.close()

asyncio.run(test())
