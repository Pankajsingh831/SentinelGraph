import asyncio, uuid, json, urllib.request
from sqlalchemy import text
from app.database import async_session_maker, engine
from app.services.auth_service import AuthService

CASE_ID = "d2d2d2d2-4444-5555-6666-777777777777"
CUST_ID = "11111111-2222-3333-4444-555555555555"

async def setup_disposable_case():
    print(f"Setting up disposable case {CASE_ID}...")
    async with async_session_maker() as s:
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
                0.88, 0.15, 0.70,
                0.75, 'CRITICAL', 'open', 'Frontend decision button verification case',
                now(), now()
            )
        """), {"cid": CASE_ID, "cust_id": CUST_ID})
        await s.commit()
    await engine.dispose()
    print("Disposable case created with status 'open'.")

def test_web_page_rendering():
    print(f"\nVerifying Next.js web page serving http://localhost:3000/cases/{CASE_ID}...")
    url = f"http://web:3000/cases/{CASE_ID}"
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req) as resp:
        print("Web status code:", resp.status)
        assert resp.status == 200
        html = resp.read().decode('utf-8')
        assert "Case Detail" in html or "Risk Assessment" in html or "Decision" in html
        print("Next.js web page successfully rendered!")

def test_frontend_decision_call():
    print("\nSimulating frontend useDecision call (POST /api/v1/cases/{case_id}/decision)...")
    auth_service = AuthService()
    token = auth_service.create_token(user_id="analyst-ui-test", username="ui_analyst", role="ANALYST")
    
    url = f"http://127.0.0.1:8000/api/v1/cases/{CASE_ID}/decision"
    payload = json.dumps({
        "decision": "CONFIRMED_ABUSE",
        "reason": "Verified frontend decision button wiring"
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
        print("API Status:", resp.status)
        assert resp.status == 200
        data = json.loads(resp.read().decode())
        print("API Response:", data)
        assert data["status"] == "closed"
        return data["decision_id"]

async def verify_records_in_db(decision_id):
    print("\nVerifying records in PostgreSQL...")
    async with async_session_maker() as s:
        # Case status
        case_r = await s.execute(text("SELECT status, resolved_at FROM risk_cases WHERE case_id = :cid"), {"cid": CASE_ID})
        case = case_r.mappings().first()
        print("Case in DB:", dict(case))
        assert case["status"] == "closed"
        assert case["resolved_at"] is not None
        
        # Decision
        dec_r = await s.execute(text("SELECT * FROM analyst_decisions WHERE decision_id = :did"), {"did": decision_id})
        dec = dec_r.mappings().first()
        print("Decision in DB:", dict(dec))
        assert dec is not None
        assert dec["decision"] == "CONFIRMED_ABUSE"
        assert dec["reason"] == "Verified frontend decision button wiring"
        
        # Audit Log
        audit_r = await s.execute(text("SELECT * FROM audit_logs WHERE resource_id = :cid AND action = 'MAKE_DECISION'"), {"cid": CASE_ID})
        audit = audit_r.mappings().first()
        print("Audit Log in DB:", dict(audit))
        assert audit is not None
        assert audit["metadata"]["decision"] == "CONFIRMED_ABUSE"
        
        print("\nALL RECORDS PERSISTED AND VERIFIED IN POSTGRESQL!")
    await engine.dispose()

asyncio.run(setup_disposable_case())
test_web_page_rendering()
did = test_frontend_decision_call()
asyncio.run(verify_records_in_db(did))
