from sqlalchemy.ext.asyncio import AsyncSession
import uuid

class AIToolFunctions:
    """Read-only tool functions exposed to the AI Investigator.
    All functions are scoped to a specific case_id."""
    
    def __init__(self, db: AsyncSession, case_id: uuid.UUID):
        self.db = db
        self.case_id = case_id
    
    async def get_case(self) -> dict:
        return {"case_id": str(self.case_id)}
        
    async def get_case_entities(self) -> list[dict]:
        return []
        
    async def get_case_evidence(self) -> list[dict]:
        return []
        
    async def get_transaction_history(self, entity_id: uuid.UUID) -> list[dict]:
        return []
        
    async def get_device_connections(self, device_id: uuid.UUID) -> list[dict]:
        return []
        
    async def get_network(self, network_id: uuid.UUID) -> dict:
        return {}
        
    async def get_temporal_anomalies(self, entity_id: uuid.UUID) -> list[dict]:
        return []
        
    async def get_model_explanation(self, prediction_id: uuid.UUID) -> dict:
        return {}
