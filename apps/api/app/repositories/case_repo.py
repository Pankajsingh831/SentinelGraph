from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from app.models.risk_case import RiskCase
from app.models.case_evidence import CaseEvidence
from app.models.analyst_decision import AnalystDecision
from app.models.case_entity import CaseEntity
from app.models.customer import Customer
from app.models.transaction import Transaction
from app.models.device import Device
from app.models.payment_instrument import PaymentInstrument
from app.models.ip_address import IPAddress
from app.models.merchant import Merchant
from app.schemas.entity_resolution import (
    EntityResolutionResponse, CanonicalEntity, ResolvedIdentifier, CorrelatedCase
)
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

    async def get_entity_resolution(self, case_id: uuid.UUID) -> Optional[EntityResolutionResponse]:
        case = await self.get_case(case_id)
        if not case:
            return None

        # 1. Canonical Entity Details
        cust_id = case.primary_entity_id
        customer = await self.db.get(Customer, cust_id) if case.primary_entity_type == 'customer' else None

        # 2. Activity / Correlation metrics for Canonical Customer
        tx_stats_query = select(
            func.count(Transaction.transaction_id),
            func.count(func.distinct(Transaction.device_id)),
            func.count(func.distinct(Transaction.instrument_id)),
            func.count(func.distinct(Transaction.ip_id))
        ).where(Transaction.customer_id == cust_id)
        tx_stats_res = await self.db.execute(tx_stats_query)
        total_txs, dev_count, inst_count, ip_count = tx_stats_res.first() or (0, 0, 0, 0)

        # 3. Correlated cases for this customer
        cases_query = select(RiskCase).where(
            RiskCase.primary_entity_id == cust_id
        ).order_by(RiskCase.created_at.desc())
        cases_res = await self.db.execute(cases_query)
        all_cases = list(cases_res.scalars().all())

        correlated_cases = [
            CorrelatedCase(
                case_id=str(c.case_id),
                risk_tier=c.risk_tier,
                overall_risk_score=float(c.overall_risk_score),
                status=c.status,
                created_at=c.created_at.isoformat() if hasattr(c.created_at, 'isoformat') else str(c.created_at)
            )
            for c in all_cases
        ]

        canonical_entity = CanonicalEntity(
            canonical_id=str(cust_id),
            entity_type=case.primary_entity_type,
            country=customer.country if customer else None,
            status=customer.status if customer else 'active',
            account_created_at=customer.account_created_at.isoformat() if customer and hasattr(customer.account_created_at, 'isoformat') else None,
            total_transactions=total_txs or 0,
            total_cases=len(all_cases),
            correlated_devices_count=dev_count or 0,
            correlated_instruments_count=inst_count or 0,
            correlated_ips_count=ip_count or 0
        )

        # 4. Resolve identifiers linked to this specific case
        entities = await self.get_case_entities(case_id)
        resolved_identifiers: list[ResolvedIdentifier] = []
        suspicious_shared_count = 0

        for ent in entities:
            e_type = ent.entity_type.lower()
            e_id = ent.entity_id
            e_role = ent.role or "associated_entity"

            if e_type == "customer":
                continue

            elif e_type == "transaction":
                tx = await self.db.get(Transaction, e_id)
                details = {}
                if tx:
                    details = {
                        "amount": float(tx.amount),
                        "currency": tx.currency,
                        "transaction_type": tx.transaction_type,
                        "occurred_at": tx.occurred_at.isoformat() if hasattr(tx.occurred_at, 'isoformat') else str(tx.occurred_at)
                    }
                resolved_identifiers.append(ResolvedIdentifier(
                    identifier_type="transaction",
                    identifier_value=str(e_id),
                    role=e_role,
                    resolution_method="EXACT_EVENT_MATCH",
                    status="RESOLVED",
                    confidence=1.0,
                    details=details,
                    shared_with_customers_count=1
                ))

            elif e_type == "device":
                dev = await self.db.get(Device, e_id)
                q_shared = select(func.count(func.distinct(Transaction.customer_id))).where(Transaction.device_id == e_id)
                shared_count = await self.db.scalar(q_shared) or 1
                is_shared = shared_count > 1
                if is_shared:
                    suspicious_shared_count += 1
                details = {}
                if dev:
                    details = {
                        "device_type": dev.device_type,
                        "first_seen_at": dev.first_seen_at.isoformat() if hasattr(dev.first_seen_at, 'isoformat') else str(dev.first_seen_at),
                        "last_seen_at": dev.last_seen_at.isoformat() if hasattr(dev.last_seen_at, 'isoformat') else str(dev.last_seen_at)
                    }
                resolved_identifiers.append(ResolvedIdentifier(
                    identifier_type="device",
                    identifier_value=str(e_id),
                    role=e_role,
                    resolution_method="EXACT_TELEMETRY_LINK",
                    status="SUSPICIOUS_SHARED" if is_shared else "RESOLVED",
                    confidence=1.0,
                    details=details,
                    shared_with_customers_count=shared_count
                ))

            elif e_type in ("instrument", "payment_instrument"):
                inst = await self.db.get(PaymentInstrument, e_id)
                q_shared = select(func.count(func.distinct(Transaction.customer_id))).where(Transaction.instrument_id == e_id)
                shared_count = await self.db.scalar(q_shared) or 1
                is_shared = shared_count > 1
                if is_shared:
                    suspicious_shared_count += 1
                details = {}
                if inst:
                    details = {
                        "instrument_type": inst.instrument_type,
                        "issuer_country": inst.issuer_country,
                        "first_seen_at": inst.first_seen_at.isoformat() if hasattr(inst.first_seen_at, 'isoformat') else str(inst.first_seen_at),
                        "last_seen_at": inst.last_seen_at.isoformat() if hasattr(inst.last_seen_at, 'isoformat') else str(inst.last_seen_at)
                    }
                resolved_identifiers.append(ResolvedIdentifier(
                    identifier_type="payment_instrument",
                    identifier_value=str(e_id),
                    role=e_role,
                    resolution_method="EXACT_TOKEN_MATCH",
                    status="SUSPICIOUS_SHARED" if is_shared else "RESOLVED",
                    confidence=1.0,
                    details=details,
                    shared_with_customers_count=shared_count
                ))

            elif e_type in ("ip", "ip_address"):
                ip_obj = await self.db.get(IPAddress, e_id)
                q_shared = select(func.count(func.distinct(Transaction.customer_id))).where(Transaction.ip_id == e_id)
                shared_count = await self.db.scalar(q_shared) or 1
                is_shared = shared_count > 1
                if is_shared:
                    suspicious_shared_count += 1
                details = {}
                if ip_obj:
                    details = {
                        "ip_hash": ip_obj.ip_hash,
                        "country": ip_obj.country,
                        "first_seen_at": ip_obj.first_seen_at.isoformat() if hasattr(ip_obj.first_seen_at, 'isoformat') else str(ip_obj.first_seen_at),
                        "last_seen_at": ip_obj.last_seen_at.isoformat() if hasattr(ip_obj.last_seen_at, 'isoformat') else str(ip_obj.last_seen_at)
                    }
                resolved_identifiers.append(ResolvedIdentifier(
                    identifier_type="ip_address",
                    identifier_value=str(e_id),
                    role=e_role,
                    resolution_method="NETWORK_SUBNET_HASH_MATCH",
                    status="SUSPICIOUS_SHARED" if is_shared else "RESOLVED",
                    confidence=1.0,
                    details=details,
                    shared_with_customers_count=shared_count
                ))

            elif e_type == "merchant":
                merch = await self.db.get(Merchant, e_id)
                details = {}
                if merch:
                    details = {
                        "merchant_name": merch.merchant_name,
                        "category": merch.category,
                        "country": merch.country
                    }
                resolved_identifiers.append(ResolvedIdentifier(
                    identifier_type="merchant",
                    identifier_value=str(e_id),
                    role=e_role,
                    resolution_method="MERCHANT_TERMINAL_LINK",
                    status="RESOLVED",
                    confidence=1.0,
                    details=details,
                    shared_with_customers_count=1
                ))

        # 5. Summary
        if suspicious_shared_count > 0:
            summary = (
                f"Resolved {len(resolved_identifiers)} case identifiers to canonical Customer {cust_id}. "
                f"HIGH RISK: Detected {suspicious_shared_count} shared identifier(s) across multiple customer accounts, "
                f"indicating synthetic identity collusion or device/card recycling."
            )
        else:
            summary = (
                f"Deterministically resolved {len(resolved_identifiers)} case identifiers to canonical Customer {cust_id}. "
                f"All telemetry, token, and network identifiers match ground truth without external cross-account conflicts."
            )

        return EntityResolutionResponse(
            case_id=str(case_id),
            canonical_entity=canonical_entity,
            resolved_identifiers=resolved_identifiers,
            correlated_cases=correlated_cases,
            resolution_strategy="DETERMINISTIC_GRAPH_LINKING",
            confidence_model="RULE_BASED_GROUND_TRUTH",
            summary=summary
        )
