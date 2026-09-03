import asyncio, uuid, json, urllib.request
from sqlalchemy import text
from app.database import async_session_maker, engine
from app.services.auth_service import AuthService

CASE_ID = "c1c1c1c1-2222-3333-4444-555555555555"
CUST_ID = "99999999-aaaa-bbbb-cccc-dddddddddddd"

async def step1_create_case():
    print(f"--- Step 1: Creating open test case {CASE_ID} ---")
    async with async_session_maker() as s:
        # Clean up if existed
        await s.execute(text("DELETE FROM audit_logs WHERE resource_id = :cid"), {"cid": CASE_ID})
        await s.execute(text("DELETE FROM analyst_decisions WHERE case_id = :cid"), {"cid": CASE_ID})
        await s.execute(text("DELETE FROM risk_cases WHERE case_id = :cid"), {"cid": CASE_ID})
        
        await s.execute(text("""
            INSERT INTO risk_cases (
                case_id, primary_entity_type, primary_entity_id,
                transaction_risk_score, network_risk_score, temporal_risk_score,
                overall_risk_score, risk_tier, status, case_reason,
                created_at, updated_at
            ) VALUES (
                :cid, 'customer', :cust_id,
                0.95, 0.20, 0.60,
                0.80, 'CRITICAL', 'open', 'Live audit persistence verification test',
                now(), now()
            )
        """), {"cid": CASE_ID, "cust_id": CUST_ID})
        await s.commit()
    await engine.dispose()
    print("Test case created successfully with status = 'open'.")

def step2_submit_decision():
    print("\n--- Step 2: Submitting decision via HTTP POST ---")
    auth_service = AuthService()
    token = auth_service.create_token(user_id="lead-analyst-42", username="lead_analyst", role="ANALYST")
    
    url = f"http://127.0.0.1:8000/api/v1/cases/{CASE_ID}/decision"
    payload = json.dumps({
        "decision": "CONFIRMED_ABUSE",
        "reason": "Live verified audit-log persistence fix"
    }).encode("utf-8")
    
    req = urllib.request.Request(
        url,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}"
        },
        method="POST"
    )
    
    with urllib.request.urlopen(req) as resp:
        print("HTTP Status:", resp.status)
        resp_data = json.loads(resp.read().decode())
        print("Response Body:", resp_data)
        assert resp.status == 200
        assert resp_data["status"] == "closed"
        return resp_data["decision_id"]

async def step3_verify_postgres(decision_id):
    print("\n--- Step 3: Verifying PostgreSQL Records ---")
    async with async_session_maker() as s:
        # 1. analyst_decisions
        dec_r = await s.execute(text("SELECT decision_id, case_id, analyst_id, decision, reason, created_at FROM analyst_decisions WHERE decision_id = :did"), {"did": decision_id})
        dec = dec_r.mappings().first()
        print("1. analyst_decisions record:")
        print("  ", dict(dec) if dec else None)
        assert dec is not None
        assert dec["decision"] == "CONFIRMED_ABUSE"
        assert dec["analyst_id"] == "lead-analyst-42"
        
        # 2. risk_cases.status and resolved_at
        case_r = await s.execute(text("SELECT case_id, status, resolved_at FROM risk_cases WHERE case_id = :cid"), {"cid": CASE_ID})
        case = case_r.mappings().first()
        print("2. risk_cases status and resolved_at:")
        print("  ", dict(case) if case else None)
        assert case is not None
        assert case["status"] == "closed"
        assert case["resolved_at"] is not None
        
        # 3. audit_logs
        audit_r = await s.execute(text("SELECT audit_id, actor_type, actor_id, action, resource_type, resource_id, metadata, created_at FROM audit_logs WHERE resource_id = :cid AND action = 'MAKE_DECISION'"), {"cid": CASE_ID})
        audit = audit_r.mappings().first()
        print("3. audit_logs record:")
        print("  ", dict(audit) if audit else None)
        assert audit is not None
        assert audit["actor_type"] == "USER"
        assert audit["actor_id"] == "lead-analyst-42"
        assert audit["action"] == "MAKE_DECISION"
        assert audit["resource_type"] == "CASE"
        assert audit["metadata"]["decision"] == "CONFIRMED_ABUSE"
        print("\nALL POSTGRESQL CHECKS PASSED!")
    await engine.dispose()

asyncio.run(step1_create_case())
dec_id = step2_submit_decision()
asyncio.run(step3_verify_postgres(dec_id))
