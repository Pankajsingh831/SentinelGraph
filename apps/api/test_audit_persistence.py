import asyncio
import uuid
import httpx
import pytest
from sqlalchemy import text
from app.database import async_session_maker, engine
from app.models.risk_case import RiskCase
from app.services.auth_service import AuthService

BASE_URL = "http://127.0.0.1:8000"

def get_client():
    auth_service = AuthService()
    token = auth_service.create_token(user_id="analyst-1", username="test_analyst", role="ANALYST")
    return httpx.Client(
        base_url=BASE_URL,
        headers={"Authorization": f"Bearer {token}"},
        timeout=30.0
    )

def test_1_analyst_decision_and_audit_log_persistence():
    """Verify terminal decision closes case, persists decision, and persists audit log."""
    async def run():
        client = get_client()
        test_case_id = uuid.uuid4()
        cust_id = uuid.uuid4()
        
        async with async_session_maker() as s:
            test_case = RiskCase(
                case_id=test_case_id,
                primary_entity_type="customer",
                primary_entity_id=cust_id,
                transaction_risk_score=0.9,
                network_risk_score=0.1,
                temporal_risk_score=0.5,
                overall_risk_score=0.85,
                risk_tier="CRITICAL",
                status="open",
                case_reason="Audit log persistence test case"
            )
            s.add(test_case)
            await s.commit()
            
        try:
            resp = client.post(
                f"/api/v1/cases/{test_case_id}/decision",
                json={
                    "decision": "CONFIRMED_ABUSE",
                    "reason": "Test audit log durable persistence"
                }
            )
            assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
            data = resp.json()
            assert data["case_id"] == str(test_case_id)
            assert data["status"] == "closed"
            decision_id = data["decision_id"]
            
            async with async_session_maker() as s:
                # Verify decision persisted
                dec_res = await s.execute(
                    text("SELECT * FROM analyst_decisions WHERE decision_id = :did"),
                    {"did": decision_id}
                )
                dec_row = dec_res.mappings().first()
                assert dec_row is not None, "Analyst decision not found in database!"
                assert str(dec_row["case_id"]) == str(test_case_id)
                assert dec_row["decision"] == "CONFIRMED_ABUSE"
                
                # Verify case status & resolved_at persisted
                case_res = await s.execute(
                    text("SELECT status, resolved_at FROM risk_cases WHERE case_id = :cid"),
                    {"cid": test_case_id}
                )
                case_row = case_res.mappings().first()
                assert case_row is not None
                assert case_row["status"] == "closed"
                assert case_row["resolved_at"] is not None
                
                # Verify audit_logs persisted
                audit_res = await s.execute(
                    text("SELECT * FROM audit_logs WHERE resource_id = :cid AND action = 'MAKE_DECISION'"),
                    {"cid": str(test_case_id)}
                )
                audit_row = audit_res.mappings().first()
                assert audit_row is not None, "Audit log row was NOT persisted in database!"
                assert audit_row["actor_type"] == "USER"
                assert audit_row["resource_type"] == "CASE"
                assert audit_row["metadata"]["decision"] == "CONFIRMED_ABUSE"
                
            # Verify 5m duplicate idempotency returns 409
            dup_resp = client.post(
                f"/api/v1/cases/{test_case_id}/decision",
                json={"decision": "CONFIRMED_ABUSE", "reason": "Duplicate attempt"}
            )
            assert dup_resp.status_code == 409
            
        finally:
            async with async_session_maker() as s:
                await s.execute(text("DELETE FROM audit_logs WHERE resource_id = :cid"), {"cid": str(test_case_id)})
                await s.execute(text("DELETE FROM analyst_decisions WHERE case_id = :cid"), {"cid": test_case_id})
                await s.execute(text("DELETE FROM risk_cases WHERE case_id = :cid"), {"cid": test_case_id})
                await s.commit()
            await engine.dispose()

    asyncio.run(run())

def test_2_non_terminal_decision_audit_log_persistence():
    """Verify non-terminal decision keeps case open, persists decision, and persists audit log."""
    async def run():
        client = get_client()
        test_case_id = uuid.uuid4()
        cust_id = uuid.uuid4()
        
        async with async_session_maker() as s:
            test_case = RiskCase(
                case_id=test_case_id,
                primary_entity_type="customer",
                primary_entity_id=cust_id,
                transaction_risk_score=0.4,
                network_risk_score=0.2,
                temporal_risk_score=0.3,
                overall_risk_score=0.35,
                risk_tier="MEDIUM",
                status="open",
                case_reason="Non-terminal decision test case"
            )
            s.add(test_case)
            await s.commit()
            
        try:
            resp = client.post(
                f"/api/v1/cases/{test_case_id}/decision",
                json={
                    "decision": "MONITOR",
                    "reason": "Monitoring customer account"
                }
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["case_id"] == str(test_case_id)
            assert data["status"] == "open"
            decision_id = data["decision_id"]
            
            async with async_session_maker() as s:
                # Case remains open
                case_res = await s.execute(
                    text("SELECT status, resolved_at FROM risk_cases WHERE case_id = :cid"),
                    {"cid": test_case_id}
                )
                case_row = case_res.mappings().first()
                assert case_row["status"] == "open"
                assert case_row["resolved_at"] is None
                
                # Decision persisted
                dec_res = await s.execute(
                    text("SELECT * FROM analyst_decisions WHERE decision_id = :did"),
                    {"did": decision_id}
                )
                assert dec_res.mappings().first() is not None
                
                # Audit log persisted
                audit_res = await s.execute(
                    text("SELECT * FROM audit_logs WHERE resource_id = :cid AND action = 'MAKE_DECISION'"),
                    {"cid": str(test_case_id)}
                )
                audit_row = audit_res.mappings().first()
                assert audit_row is not None
                assert audit_row["metadata"]["decision"] == "MONITOR"
                
        finally:
            async with async_session_maker() as s:
                await s.execute(text("DELETE FROM audit_logs WHERE resource_id = :cid"), {"cid": str(test_case_id)})
                await s.execute(text("DELETE FROM analyst_decisions WHERE case_id = :cid"), {"cid": test_case_id})
                await s.execute(text("DELETE FROM risk_cases WHERE case_id = :cid"), {"cid": test_case_id})
                await s.commit()
            await engine.dispose()

    asyncio.run(run())
