from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from app.models.risk_case import RiskCase
from app.models.case_evidence import CaseEvidence
from app.models.analyst_decision import AnalystDecision
from app.models.case_entity import CaseEntity
import uuid
from datetime import datetime, timedelta
from typing import Optional

class CaseRepository:
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def list_cases(self, status: str = None, risk_tier: str = None,
                         page: int = 1, limit: int = 20) -> tuple[list[RiskCase], int]:
        """List cases with optional filters, pagination. Returns (cases, total_count)."""
        query = select(RiskCase)
        count_query = select(func.count(RiskCase.case_id))
        
        if status:
            query = query.where(RiskCase.status == status)
            count_query = count_query.where(RiskCase.status == status)
        if risk_tier:
            query = query.where(RiskCase.risk_tier == risk_tier)
            count_query = count_query.where(RiskCase.risk_tier == risk_tier)
            
        offset = (page - 1) * limit
        query = query.offset(offset).limit(limit)
        
        total_count = await self.db.scalar(count_query)
        result = await self.db.execute(query)
        cases = list(result.scalars().all())
        
        return cases, total_count or 0
    
    async def get_case(self, case_id: uuid.UUID) -> Optional[RiskCase]:
        return await self.db.get(RiskCase, case_id)
    
    async def get_case_evidence(self, case_id: uuid.UUID) -> list[CaseEvidence]:
        query = select(CaseEvidence).where(CaseEvidence.case_id == case_id)
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def get_case_entities(self, case_id: uuid.UUID) -> list[CaseEntity]:
        query = select(CaseEntity).where(CaseEntity.case_id == case_id)
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def evidence_ids_exist(self, case_id: uuid.UUID, evidence_ids: list[str]) -> bool:
        """Check if ALL given evidence IDs exist for this case. Used by grounding validator."""
        if not evidence_ids:
            return True
        try:
            parsed_ids = [uuid.UUID(eid) for eid in evidence_ids]
        except ValueError:
            return False
            
        query = select(func.count(CaseEvidence.evidence_id)).where(
            and_(
                CaseEvidence.case_id == case_id,
                CaseEvidence.evidence_id.in_(parsed_ids)
            )
        )
        count = await self.db.scalar(query)
        return count == len(evidence_ids)
    
    async def create_decision(self, case_id: uuid.UUID, analyst_id: str,
                              decision: str, reason: str = None) -> AnalystDecision:
        """Create analyst decision. Update case status for terminal decisions."""
        analyst_decision = AnalystDecision(
            case_id=case_id,
            analyst_id=analyst_id,
            decision=decision,
            reason=reason
        )
        self.db.add(analyst_decision)
        
        # Update case status if terminal
        terminal_decisions = ['CONFIRMED_ABUSE', 'FALSE_POSITIVE']
        if decision in terminal_decisions:
            case = await self.get_case(case_id)
            if case:
                case.status = 'closed'
                case.resolved_at = func.now()
        
        await self.db.commit()
        await self.db.refresh(analyst_decision)
        return analyst_decision
    
    async def check_duplicate_decision(self, case_id: uuid.UUID, analyst_id: str,
                                        decision: str) -> bool:
        """Check for duplicate decision within recent window (idempotency)."""
        time_window = datetime.now() - timedelta(minutes=5)
        query = select(AnalystDecision).where(
            and_(
                AnalystDecision.case_id == case_id,
                AnalystDecision.analyst_id == analyst_id,
                AnalystDecision.decision == decision,
                AnalystDecision.created_at >= time_window
            )
        )
        result = await self.db.execute(query)
        return result.first() is not None
