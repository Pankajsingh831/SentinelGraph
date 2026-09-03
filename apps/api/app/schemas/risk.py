from pydantic import BaseModel, ConfigDict
import uuid

class FeatureContribution(BaseModel):
    name: str
    value: float
    contribution: float

class RiskScoreRequest(BaseModel):
    transaction_id: uuid.UUID

class RiskScoreResponse(BaseModel):
    transaction_id: uuid.UUID
    risk_score: float
    risk_tier: str
    decision: str
    model_version: str

    model_config = ConfigDict(from_attributes=True)

class RiskExplanationResponse(BaseModel):
    prediction_id: uuid.UUID
    risk_score: float
    features: list[FeatureContribution]

    model_config = ConfigDict(from_attributes=True)
