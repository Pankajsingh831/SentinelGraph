from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.database import get_db
from app.config import get_settings
from starlette.requests import Request
import structlog

logger = structlog.get_logger()
router = APIRouter(prefix="/health", tags=["health"])
settings = get_settings()

@router.get("")
async def check_health(request: Request, db: AsyncSession = Depends(get_db)):
    services = {"postgres": False, "redis": False, "neo4j": False}
    
    try:
        await db.execute(text("SELECT 1"))
        services["postgres"] = True
    except Exception as e:
        logger.error(f"Postgres health check failed: {e}")
        
    try:
        if await request.app.state.redis.ping():
            services["redis"] = True
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        
    try:
        await request.app.state.neo4j.verify_connectivity()
        services["neo4j"] = True
    except Exception as e:
        logger.error(f"Neo4j health check failed: {e}")

    all_healthy = all(services.values())
    
    return {
        "status": "healthy" if all_healthy else "degraded",
        "services": services,
        "version": "1.0.0"
    }
