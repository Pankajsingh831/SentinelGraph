QUERY_ENTITY_GRAPH = """
    MATCH (e:{entity_type} {{id: $entity_id}})-[r]-(connected)
    RETURN e, r, connected LIMIT $limit
"""

QUERY_NEIGHBORS = """
    MATCH path = (e:{entity_type} {{id: $entity_id}})-[*1..{depth}]-(connected)
    WITH DISTINCT connected, relationships(path) AS rels
    RETURN connected.id AS id, labels(connected)[0] AS type,
           [r IN rels | type(r)] AS relationship_types
    LIMIT $limit
"""

QUERY_NETWORK_GRAPH = """
    MATCH (c:Customer)-[*1..3]-(connected)
    WHERE c.id IN $customer_ids
    WITH COLLECT(DISTINCT connected) + COLLECT(DISTINCT c) AS allNodes
    UNWIND allNodes AS n
    OPTIONAL MATCH (n)-[r]-(other) WHERE other IN allNodes
    RETURN DISTINCT n.id AS id, labels(n)[0] AS type,
           COLLECT(DISTINCT {source: startNode(r).id, target: endNode(r).id, type: type(r)}) AS edges
"""
