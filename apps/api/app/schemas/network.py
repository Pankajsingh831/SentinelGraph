from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from uuid import UUID
from .graph import GraphNode, GraphEdge

class NetworkResponse(BaseModel):
    network_id: UUID
    node_count: int
    edge_count: int
    network_density: float
    community_id: Optional[str] = None
    graph_risk_score: float
    detected_at: datetime

class NetworkGraphResponse(BaseModel):
    nodes: List[GraphNode]
    edges: List[GraphEdge]
    stats: NetworkResponse
