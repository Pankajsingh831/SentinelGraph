from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import redis.asyncio as redis
from neo4j import AsyncGraphDatabase
import structlog

from app.config import get_settings
from app.api.health import router as health_router
from app.middleware.request_id import RequestIDMiddleware

logger = structlog.get_logger()
settings = get_settings()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting up services")
    
    app.state.redis = redis.from_url(settings.REDIS_URL)
    
    app.state.neo4j = AsyncGraphDatabase.driver(
        settings.NEO4J_URI, 
        auth=(settings.NEO4J_USERNAME, settings.NEO4J_PASSWORD)
    )
    await app.state.neo4j.verify_connectivity()
    
    yield
    
    # Shutdown
    logger.info("Shutting down services")
    from app.database import engine
    await engine.dispose()
    await app.state.redis.close()
    await app.state.neo4j.close()

app = FastAPI(
    title='SentinelGraph API',
    version='1.0.0',
    description='SentinelGraph Core API',
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=['http://localhost:3000'],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestIDMiddleware)

from app.api.risk import router as risk_router
from app.api.transactions import router as transactions_router
from app.api.customers import router as customers_router
from app.api.graph import router as graph_router
from app.api.networks import router as networks_router
from app.api.auth import router as auth_router
from app.api.cases import router as cases_router

app.include_router(health_router)
app.include_router(auth_router)
app.include_router(cases_router)
app.include_router(risk_router)
app.include_router(transactions_router)
app.include_router(customers_router)
app.include_router(graph_router)
app.include_router(networks_router)
