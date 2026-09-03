from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime
from typing import Optional
import uuid

class CaseListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    case_id: uuid.UUID
    primary_entity_type: str
    primary_entity_id: uuid.UUID
    overall_risk_score: float
    risk_tier: str
    status: str
    case_reason: str
    created_at: datetime

class CaseDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    case_id: uuid.UUID
    primary_entity_type: str
    primary_entity_id: uuid.UUID
    transaction_risk_score: float
    network_risk_score: float
    temporal_risk_score: float
    overall_risk_score: float
    risk_tier: str
    status: str
    case_reason: str
    created_at: datetime
    updated_at: datetime
    resolved_at: Optional[datetime] = None

class CaseEvidenceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    evidence_id: uuid.UUID
    case_id: uuid.UUID
    evidence_type: str
    entity_type: Optional[str] = None
    entity_id: Optional[uuid.UUID] = None
    description: str
    severity: str
    evidence_data: Optional[dict] = None
    created_at: datetime

class TimelineEvent(BaseModel):
    event_type: str  # 'transaction', 'account_created', 'case_created', 'network_growth', 'decision'
    timestamp: datetime
    description: str
    entity_type: Optional[str] = None
    entity_id: Optional[uuid.UUID] = None
    metadata: Optional[dict] = None

class CaseTimelineResponse(BaseModel):
    case_id: uuid.UUID
    events: list[TimelineEvent]

class DecisionRequest(BaseModel):
    decision: str = Field(..., pattern='^(MONITOR|ESCALATE|CONFIRMED_ABUSE|FALSE_POSITIVE)$')
    reason: Optional[str] = None

class DecisionResponse(BaseModel):
    case_id: uuid.UUID
    status: str
    decision_id: uuid.UUID
