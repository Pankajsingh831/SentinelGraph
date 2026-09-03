from neo4j import AsyncGraphDatabase, AsyncDriver
from typing import Any, Dict, List, Optional
import structlog

logger = structlog.get_logger()

class Neo4jClient:
    def __init__(self, uri: str, user: str, password: str):
        self.driver: AsyncDriver = AsyncGraphDatabase.driver(
            uri, auth=(user, password), max_connection_pool_size=50
        )
        self._available = True
    
    async def verify(self):
        try:
            await self.driver.verify_connectivity()
            self._available = True
        except Exception:
            self._available = False
    
    @property
    def is_available(self) -> bool:
        return self._available
    
    async def close(self):
        await self.driver.close()
    
    async def query(self, cypher: str, params: dict = None) -> List[Dict]:
        """Execute a Cypher query. Marks service as unavailable on connection error."""
        try:
            records, _, _ = await self.driver.execute_query(
                cypher, parameters_=(params or {}), database_='neo4j'
            )
            self._available = True
            return [r.data() for r in records]
        except Exception as e:
            logger.error('neo4j_query_failed', error=str(e))
            self._available = False
            raise
