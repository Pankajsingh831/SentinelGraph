from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
import uuid

from app.database import get_db
from app.middleware.auth import get_current_user, User
from app.schemas.case import (
    CaseListItem, CaseDetailResponse, CaseEvidenceResponse,
    CaseTimelineResponse, DecisionRequest, DecisionResponse
)
from app.schemas.ai import InvestigateRequest, InvestigateResponse
from app.repositories.case_repo import CaseRepository
from app.repositories.audit_repo import AuditRepository
from app.services.case_service import CaseService
from app.services.ai_investigator import AIInvestigator
from app.schemas import PaginatedResponse

router = APIRouter(prefix="/api/v1/cases", tags=["cases"])

def get_case_service(db: AsyncSession = Depends(get_db)) -> CaseService:
    case_repo = CaseRepository(db)
    audit_repo = AuditRepository(db)
    return CaseService(case_repo, audit_repo)

@router.get("", response_model=PaginatedResponse[CaseListItem])
async def list_cases(
    status: Optional[str] = None,
    risk_tier: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    case_service: CaseService = Depends(get_case_service)
):
    cases, total = await case_service.list_cases(status, risk_tier, page, limit)
    
    items = [
        CaseListItem.model_validate(c)
        for c in cases
    ]
    
    pages = (total + limit - 1) // limit
    
    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        limit=limit,
        pages=pages
    )

@router.get("/{case_id}", response_model=CaseDetailResponse)
async def get_case(
    case_id: uuid.UUID,
    user: User = Depends(get_current_user),
    case_service: CaseService = Depends(get_case_service)
):
    case = await case_service.get_case(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="CASE_NOT_FOUND")
    return CaseDetailResponse.model_validate(case)

@router.get("/{case_id}/evidence", response_model=list[CaseEvidenceResponse])
async def get_case_evidence(
    case_id: uuid.UUID,
    user: User = Depends(get_current_user),
    case_service: CaseService = Depends(get_case_service)
):
    evidence = await case_service.get_case_evidence(case_id)
    return [CaseEvidenceResponse.model_validate(e) for e in evidence]

@router.get("/{case_id}/timeline", response_model=CaseTimelineResponse)
async def get_case_timeline(
    case_id: uuid.UUID,
    user: User = Depends(get_current_user),
    case_service: CaseService = Depends(get_case_service)
):
    return await case_service.get_case_timeline(case_id)

@router.post("/{case_id}/investigate", response_model=InvestigateResponse)
async def investigate_case(
    case_id: uuid.UUID,
    request: InvestigateRequest,
    user: User = Depends(get_current_user),
    case_service: CaseService = Depends(get_case_service)
):
    case = await case_service.get_case(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="CASE_NOT_FOUND")
        
    evidence = await case_service.get_case_evidence(case_id)
    if not evidence:
        raise HTTPException(status_code=422, detail="NO_EVIDENCE_FOR_INVESTIGATION")
        
    case_data = {
        "case_id": str(case.case_id),
        "overall_risk_score": case.overall_risk_score,
        "transaction_risk_score": case.transaction_risk_score,
        "network_risk_score": case.network_risk_score,
        "temporal_risk_score": case.temporal_risk_score,
    }
    
    evidence_dicts = [
        {
            "evidence_id": str(e.evidence_id),
            "evidence_type": e.evidence_type,
            "severity": e.severity,
            "description": e.description
        } for e in evidence
    ]
    
    investigator = AIInvestigator()
    return await investigator.investigate(
        case_id=case_id,
        case_data=case_data,
        evidence=evidence_dicts,
        follow_up_question=request.follow_up_question
    )

@router.post("/{case_id}/decision", response_model=DecisionResponse)
async def make_decision(
    case_id: uuid.UUID,
    request: DecisionRequest,
    user: User = Depends(get_current_user),
    case_service: CaseService = Depends(get_case_service)
):
    decision = await case_service.record_decision(
        case_id=case_id,
        analyst_id=user.user_id,
        decision=request.decision,
        reason=request.reason
    )
    
    case = await case_service.get_case(case_id)
    
    return DecisionResponse(
        case_id=case_id,
        status=case.status,
        decision_id=decision.decision_id
    )
