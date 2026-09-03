from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.schemas.graph import EntityGraphResponse, NeighborResponse
from app.services.graph_service import GraphService

router = APIRouter(prefix="/api/v1/graph", tags=["graph"])
graph_service = GraphService()

@router.get("/entity/{entity_type}/{entity_id}", response_model=EntityGraphResponse)
async def get_entity_graph(
    entity_type: str,
    entity_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    neo4j_driver = getattr(request.app.state, "neo4j", None)
    return await graph_service.get_entity_graph(entity_type, entity_id, neo4j_driver, db)

@router.get("/entity/{entity_type}/{entity_id}/neighbors", response_model=NeighborResponse)
async def get_neighbors(
    entity_type: str,
    entity_id: str,
    request: Request,
    depth: int = Query(1, ge=1, le=3),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db)
):
    neo4j_driver = getattr(request.app.state, "neo4j", None)
    return await graph_service.get_neighbors(entity_type, entity_id, depth, limit, neo4j_driver, db)
