import uuid
from app.repositories.case_repo import CaseRepository
from app.repositories.audit_repo import AuditRepository
from app.schemas.case import CaseTimelineResponse, TimelineEvent
from fastapi import HTTPException

class CaseService:
    def __init__(self, case_repo: CaseRepository, audit_repo: AuditRepository):
        self.case_repo = case_repo
        self.audit_repo = audit_repo

    async def list_cases(self, status: str, risk_tier: str, page: int, limit: int):
        return await self.case_repo.list_cases(status, risk_tier, page, limit)

    async def get_case(self, case_id: uuid.UUID):
        return await self.case_repo.get_case(case_id)

    async def get_case_evidence(self, case_id: uuid.UUID):
        return await self.case_repo.get_case_evidence(case_id)

    async def get_case_timeline(self, case_id: uuid.UUID) -> CaseTimelineResponse:
        """Build chronological timeline by merging transactions, account creation,
        network changes, case events, and decisions."""
        case = await self.get_case(case_id)
        if not case:
            raise HTTPException(status_code=404, detail="CASE_NOT_FOUND")

        events = []
        # Add case creation event
        events.append(TimelineEvent(
            event_type='case_created',
            timestamp=case.created_at,
            description=f"Case opened with {case.risk_tier} risk tier",
            entity_type=case.primary_entity_type,
            entity_id=case.primary_entity_id
        ))

        # Add evidence as events
        evidence_list = await self.get_case_evidence(case_id)
        for ev in evidence_list:
            events.append(TimelineEvent(
                event_type=ev.evidence_type,
                timestamp=ev.created_at,
                description=ev.description,
                entity_type=ev.entity_type,
                entity_id=ev.entity_id,
                metadata=ev.evidence_data
            ))

        # Sort chronologically
        events.sort(key=lambda x: x.timestamp)
        return CaseTimelineResponse(case_id=case_id, events=events)

    async def record_decision(self, case_id: uuid.UUID, analyst_id: str, decision: str, reason: str):
        """Record decision with idempotency check (409 on duplicate), audit logging."""
        is_duplicate = await self.case_repo.check_duplicate_decision(case_id, analyst_id, decision)
        if is_duplicate:
            raise HTTPException(status_code=409, detail="DUPLICATE_DECISION")

        analyst_decision = await self.case_repo.create_decision(case_id, analyst_id, decision, reason)

        await self.audit_repo.log_action(
            actor_type="USER",
            actor_id=analyst_id,
            action="MAKE_DECISION",
            resource_type="CASE",
            resource_id=str(case_id),
            metadata={"decision": decision, "reason": reason}
        )

        return analyst_decision

    async def get_case_entity_resolution(self, case_id: uuid.UUID):
        return await self.case_repo.get_entity_resolution(case_id)
