from functools import lru_cache
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    DATABASE_URL: str
    REDIS_URL: str
    KAFKA_BROKERS: str = 'kafka:9092'
    NEO4J_URI: str
    NEO4J_USERNAME: str = 'neo4j'
    NEO4J_PASSWORD: str
    JWT_SECRET: str
    JWT_ALGORITHM: str = 'HS256'
    JWT_EXPIRATION_MINUTES: int = 480
    ANTHROPIC_API_KEY: str = ''
    MODEL_ACTIVE_VERSION: str = 'xgb-graph-v1'
    RISK_TIER_THRESHOLDS: str = '0.30,0.60,0.80'
    RISK_AGGREGATION_WEIGHTS: str = '0.50,0.30,0.20'
    ENABLE_AI_INVESTIGATOR: bool = True
    ENABLE_DETECTION_REPLAY: bool = True
    RISK_CASE_COOLDOWN_HOURS: int = 24
    LOG_LEVEL: str = 'INFO'
    
    @property
    def risk_tier_thresholds_list(self) -> List[float]:
        return [float(x) for x in self.RISK_TIER_THRESHOLDS.split(',')]
        
    @property
    def risk_aggregation_weights_list(self) -> List[float]:
        return [float(x) for x in self.RISK_AGGREGATION_WEIGHTS.split(',')]

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

@lru_cache
def get_settings() -> Settings:
    return Settings()
