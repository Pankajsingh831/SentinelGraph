from pydantic import BaseModel, Field
from typing import Optional
import uuid

class InvestigationReport(BaseModel):
    """AI Investigator output schema - validated server-side."""
    summary: str
    risk_level: str = Field(..., pattern='^(LOW|MEDIUM|HIGH|CRITICAL)$')
    key_evidence: list[str]  # evidence_id strings, validated against real case_evidence
    affected_entities: list[str]
    recommended_action: str = Field(..., pattern='^(MONITOR|ESCALATE|CONFIRMED_ABUSE|FALSE_POSITIVE)$')
    confidence: float = Field(..., ge=0.0, le=1.0)

class InvestigateRequest(BaseModel):
    follow_up_question: Optional[str] = None

class InvestigateResponse(BaseModel):
    case_id: uuid.UUID
    report: Optional[InvestigationReport] = None
    fallback_message: Optional[str] = None
    grounded: bool = True
