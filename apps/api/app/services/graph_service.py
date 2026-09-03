from app.schemas.graph import EntityGraphResponse, NeighborResponse, GraphNode, GraphEdge
from typing import Optional, Any
import structlog
import uuid
from fastapi import HTTPException
from sqlalchemy import text
from app.config import get_settings
from neo4j import AsyncGraphDatabase

logger = structlog.get_logger()

LABEL_MAP = {
    "customer": "Customer",
    "merchant": "Merchant",
    "transaction": "Transaction",
    "device": "Device",
    "instrument": "PaymentInstrument",
    "payment_instrument": "PaymentInstrument",
    "paymentinstrument": "PaymentInstrument",
    "ip": "IPAddress",
    "ip_address": "IPAddress",
    "ipaddress": "IPAddress",
}

class GraphService:
    def __init__(self, neo4j_client=None):
        self._neo4j_client = neo4j_client
        self._fallback_driver = None

    async def _get_driver(self, neo4j_client=None):
        if neo4j_client is not None:
            return neo4j_client
        if self._neo4j_client is not None:
            return self._neo4j_client
        if self._fallback_driver is None:
            settings = get_settings()
            self._fallback_driver = AsyncGraphDatabase.driver(
                settings.NEO4J_URI,
                auth=(settings.NEO4J_USERNAME, settings.NEO4J_PASSWORD)
            )
        return self._fallback_driver

    def _validate_inputs(self, entity_type: str, entity_id: str) -> tuple[str, str]:
        normalized_type = entity_type.lower().strip()
        if normalized_type not in LABEL_MAP:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported entity type: '{entity_type}'. Allowed types: {sorted(list(set(LABEL_MAP.keys())))}"
            )
        try:
            clean_id = str(uuid.UUID(str(entity_id).strip()))
        except (ValueError, AttributeError):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid entity ID: '{entity_id}'. Must be a valid UUID."
            )
        return LABEL_MAP[normalized_type], clean_id

    def _extract_graph(self, root_node, paths: list) -> tuple[list[GraphNode], list[GraphEdge]]:
        nodes_map: dict[str, GraphNode] = {}
        edges_set: set[tuple[str, str, str]] = set()
        edges_list: list[GraphEdge] = []

        def add_node(neo4j_node):
            if not neo4j_node:
                return
            nid = neo4j_node.get("id")
            if not nid:
                return
            nid_str = str(nid)
            if nid_str not in nodes_map:
                labels = list(neo4j_node.labels) if hasattr(neo4j_node, "labels") else []
                node_type = labels[0] if labels else "Unknown"
                props = dict(neo4j_node)
                clean_props = {}
                for k, v in props.items():
                    if hasattr(v, "isoformat"):
                        clean_props[k] = v.isoformat()
                    else:
                        clean_props[k] = v
                if "label" not in clean_props:
                    clean_props["label"] = f"{node_type}: {nid_str[:8]}..."
                nodes_map[nid_str] = GraphNode(
                    id=nid_str,
                    type=node_type,
                    properties=clean_props
                )

        add_node(root_node)

        for path in paths:
            if path is None:
                continue
            for node in path.nodes:
                add_node(node)
            for rel in path.relationships:
                start_id = str(rel.start_node.get("id"))
                end_id = str(rel.end_node.get("id"))
                rel_type = rel.type
                edge_key = (start_id, end_id, rel_type)
                if edge_key not in edges_set:
                    edges_set.add(edge_key)
                    edges_list.append(GraphEdge(
                        source=start_id,
                        target=end_id,
                        type=rel_type
                    ))

        return list(nodes_map.values()), edges_list

    async def get_entity_graph(self, entity_type: str, entity_id: str, neo4j_client=None, db=None) -> EntityGraphResponse:
        """Get entity's direct graph. Falls back to Postgres entity_relationships if Neo4j unavailable."""
        label, clean_id = self._validate_inputs(entity_type, entity_id)

        cypher = f"""
        MATCH (root:{label} {{id: $entity_id}})
        OPTIONAL MATCH path = (root)-[*1..2]-(connected)
        WITH root, path
        LIMIT 100
        WITH root, collect(path) AS paths
        RETURN root, paths
        """

        try:
            driver = await self._get_driver(neo4j_client)
            if hasattr(driver, "execute_query"):
                res, _, _ = await driver.execute_query(cypher, entity_id=clean_id)
            elif hasattr(driver, "query"):
                res = await driver.query(cypher, {"entity_id": clean_id})
            else:
                raise RuntimeError("Neo4j driver interface not recognized")

            if not res or not res[0].get("root"):
                return EntityGraphResponse(nodes=[], edges=[], degraded=False)

            nodes, edges = self._extract_graph(res[0]["root"], res[0].get("paths") or [])
            return EntityGraphResponse(nodes=nodes, edges=edges, degraded=False)

        except HTTPException:
            raise
        except Exception as e:
            logger.warning("neo4j_query_failed_fallback_to_postgres", error=str(e), entity_id=clean_id)
            if db is not None:
                return await self._fallback_postgres_graph(entity_type, clean_id, db)
            return EntityGraphResponse(nodes=[], edges=[], degraded=True)

    async def get_neighbors(self, entity_type: str, entity_id: str, depth: int = 1, limit: int = 50, neo4j_client=None, db=None) -> NeighborResponse:
        """Get bounded neighborhood. depth<=3, limit<=200 enforced server-side (FR-010)."""
        label, clean_id = self._validate_inputs(entity_type, entity_id)
        bounded_depth = max(1, min(depth, 3))
        bounded_limit = max(1, min(limit, 200))

        cypher = f"""
        MATCH (root:{label} {{id: $entity_id}})
        OPTIONAL MATCH path = (root)-[*1..{bounded_depth}]-(connected)
        WITH root, path
        LIMIT $limit
        WITH root, collect(path) AS paths
        RETURN root, paths
        """

        try:
            driver = await self._get_driver(neo4j_client)
            if hasattr(driver, "execute_query"):
                res, _, _ = await driver.execute_query(cypher, entity_id=clean_id, limit=bounded_limit)
            elif hasattr(driver, "query"):
                res = await driver.query(cypher, {"entity_id": clean_id, "limit": bounded_limit})
            else:
                raise RuntimeError("Neo4j driver interface not recognized")

            if not res or not res[0].get("root"):
                return NeighborResponse(neighbors=[], edges=[], depth=bounded_depth, limit=bounded_limit, degraded=False)

            nodes, edges = self._extract_graph(res[0]["root"], res[0].get("paths") or [])
            return NeighborResponse(neighbors=nodes, edges=edges, depth=bounded_depth, limit=bounded_limit, degraded=False)

        except HTTPException:
            raise
        except Exception as e:
            logger.warning("neo4j_neighbors_query_failed_fallback_to_postgres", error=str(e), entity_id=clean_id)
            if db is not None:
                fallback_res = await self._fallback_postgres_graph(entity_type, clean_id, db, limit=bounded_limit)
                return NeighborResponse(
                    neighbors=fallback_res.nodes,
                    edges=fallback_res.edges,
                    depth=bounded_depth,
                    limit=bounded_limit,
                    degraded=True
                )
            return NeighborResponse(neighbors=[], edges=[], depth=bounded_depth, limit=bounded_limit, degraded=True)

    async def _fallback_postgres_graph(self, entity_type: str, clean_id: str, db, limit: int = 50) -> EntityGraphResponse:
        """Fallback to PostgreSQL entity_relationships table if Neo4j is unavailable."""
        try:
            query = text("""
                SELECT source_type, source_id, relationship_type, target_type, target_id
                FROM entity_relationships
                WHERE (source_type = :stype AND source_id = :sid)
                   OR (target_type = :stype AND target_id = :sid)
                LIMIT :limit
            """)
            result = await db.execute(query, {
                "stype": entity_type.lower(),
                "sid": clean_id,
                "limit": limit
            })
            rows = result.fetchall()

            nodes_map: dict[str, GraphNode] = {}
            edges_list: list[GraphEdge] = []
            edges_set: set[tuple[str, str, str]] = set()

            root_type = LABEL_MAP.get(entity_type.lower(), entity_type.capitalize())
            nodes_map[clean_id] = GraphNode(
                id=clean_id,
                type=root_type,
                properties={"id": clean_id, "label": f"{root_type}: {clean_id[:8]}..."}
            )

            for row in rows:
                s_type = LABEL_MAP.get(row.source_type.lower(), row.source_type.capitalize())
                s_id = str(row.source_id)
                t_type = LABEL_MAP.get(row.target_type.lower(), row.target_type.capitalize())
                t_id = str(row.target_id)
                rel_type = row.relationship_type

                if s_id not in nodes_map:
                    nodes_map[s_id] = GraphNode(
                        id=s_id,
                        type=s_type,
                        properties={"id": s_id, "label": f"{s_type}: {s_id[:8]}..."}
                    )
                if t_id not in nodes_map:
                    nodes_map[t_id] = GraphNode(
                        id=t_id,
                        type=t_type,
                        properties={"id": t_id, "label": f"{t_type}: {t_id[:8]}..."}
                    )

                edge_key = (s_id, t_id, rel_type)
                if edge_key not in edges_set:
                    edges_set.add(edge_key)
                    edges_list.append(GraphEdge(source=s_id, target=t_id, type=rel_type))

            return EntityGraphResponse(nodes=list(nodes_map.values()), edges=edges_list, degraded=True)
        except Exception as ex:
            logger.error("postgres_fallback_failed", error=str(ex))
            return EntityGraphResponse(nodes=[], edges=[], degraded=True)
