import asyncio
from neo4j import AsyncGraphDatabase
from app.config import get_settings

async def test():
    settings = get_settings()
    driver = AsyncGraphDatabase.driver(settings.NEO4J_URI, auth=(settings.NEO4J_USERNAME, settings.NEO4J_PASSWORD))
    
    cypher = """
    MATCH (root:Customer {id: $entity_id})
    OPTIONAL MATCH path = (root)-[*1..2]-(connected)
    WITH root, collect(path) AS paths
    RETURN root, paths
    """
    
    res, _, _ = await driver.execute_query(cypher, entity_id='5c5001a1-887e-45e7-8ae8-f1c53fa808b0')
    print('Result count:', len(res))
    if res and res[0]['root']:
        root = res[0]['root']
        paths = res[0]['paths']
        
        nodes_map = {}
        edges_map = {}
        
        # Add root node
        nodes_map[root['id']] = {
            'id': root['id'],
            'type': list(root.labels)[0] if root.labels else 'Unknown',
            'properties': dict(root)
        }
        
        for path in paths:
            if path is None:
                continue
            for node in path.nodes:
                nid = node.get('id')
                if nid and nid not in nodes_map:
                    ntype = list(node.labels)[0] if node.labels else 'Unknown'
                    nodes_map[nid] = {
                        'id': nid,
                        'type': ntype,
                        'properties': dict(node)
                    }
            for rel in path.relationships:
                start_id = rel.start_node.get('id')
                end_id = rel.end_node.get('id')
                edge_key = (start_id, end_id, rel.type)
                if edge_key not in edges_map:
                    edges_map[edge_key] = {
                        'source': start_id,
                        'target': end_id,
                        'type': rel.type
                    }
        
        print(f'Total distinct nodes: {len(nodes_map)}')
        for nid, n in nodes_map.items():
            ntype = n['type']
            print(f'  Node: {ntype} - {nid}')
        print(f'Total distinct edges: {len(edges_map)}')
        for (s, t, r) in edges_map.keys():
            print(f'  Edge: {s} -[:{r}]-> {t}')
            
    await driver.close()

asyncio.run(test())
