import asyncio, urllib.request, json
from neo4j import AsyncGraphDatabase
from app.config import get_settings

async def verify_parity():
    settings = get_settings()
    driver = AsyncGraphDatabase.driver(settings.NEO4J_URI, auth=(settings.NEO4J_USERNAME, settings.NEO4J_PASSWORD))
    cid = '5c5001a1-887e-45e7-8ae8-f1c53fa808b0'
    
    # Direct Neo4j query
    cypher = """
    MATCH (root:Customer {id: $cid})
    OPTIONAL MATCH path = (root)-[*1..2]-(connected)
    WITH root, collect(path) AS paths
    RETURN root, paths
    """
    res, _, _ = await driver.execute_query(cypher, cid=cid)
    root = res[0]['root']
    paths = res[0]['paths']
    neo4j_nodes = {root['id']: list(root.labels)[0]}
    neo4j_edges = set()
    for p in paths:
        if not p: continue
        for n in p.nodes:
            neo4j_nodes[n['id']] = list(n.labels)[0]
        for r in p.relationships:
            neo4j_edges.add((r.start_node['id'], r.end_node['id'], r.type))
            
    await driver.close()
    
    print(f"Neo4j Direct: {len(neo4j_nodes)} nodes, {len(neo4j_edges)} edges")
    for nid, l in neo4j_nodes.items():
        print(f"  Neo4j Node: {l} ({nid})")
    for (s, t, r) in neo4j_edges:
        print(f"  Neo4j Edge: {s} -[:{r}]-> {t}")
        
    # Graph API call: /entity/customer/{cid}
    url = f"http://127.0.0.1:8000/api/v1/graph/entity/customer/{cid}"
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req) as resp:
        api_data = json.loads(resp.read().decode())
        
    api_nodes = {n['id']: n['type'] for n in api_data['nodes']}
    api_edges = {(e['source'], e['target'], e['type']) for e in api_data['edges']}
    
    print(f"Graph API: {len(api_nodes)} nodes, {len(api_edges)} edges")
    for nid, l in api_nodes.items():
        print(f"  API Node: {l} ({nid})")
    for (s, t, r) in api_edges:
        print(f"  API Edge: {s} -[:{r}]-> {t}")
        
    # Strict parity checks
    assert neo4j_nodes.keys() == api_nodes.keys(), "Node IDs mismatch between Neo4j and API!"
    assert neo4j_edges == api_edges, "Edges mismatch between Neo4j and API!"
    print("SUCCESS: 100% PARITY BETWEEN NEO4J AND GRAPH API!")

asyncio.run(verify_parity())
