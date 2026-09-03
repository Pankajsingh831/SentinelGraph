from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

class GraphNode(BaseModel):
    id: str
    type: str
    properties: Dict[str, Any] = Field(default_factory=dict)

class GraphEdge(BaseModel):
    source: str
    target: str
    type: str

class EntityGraphResponse(BaseModel):
    nodes: List[GraphNode]
    edges: List[GraphEdge]
    degraded: bool = False

class NeighborResponse(BaseModel):
    neighbors: List[GraphNode]
    edges: List[GraphEdge]
    depth: int
    limit: int
    degraded: bool = False
