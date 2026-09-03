from fastapi import APIRouter, Depends
from uuid import UUID
from app.schemas.network import NetworkResponse, NetworkGraphResponse
from app.services.network_service import NetworkService

router = APIRouter(prefix="/api/v1/networks", tags=["networks"])
network_service = NetworkService()

@router.get("/{network_id}", response_model=NetworkResponse)
async def get_network(network_id: UUID):
    return await network_service.get_network(network_id, None)

@router.get("/{network_id}/graph", response_model=NetworkGraphResponse)
async def get_network_graph(network_id: UUID):
    return await network_service.get_network_graph(network_id, None, None)
