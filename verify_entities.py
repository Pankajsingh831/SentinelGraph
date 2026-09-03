import asyncio, urllib.request, json
from sqlalchemy import text
from app.database import async_session_maker

async def check():
    cid = '0adbb74e-2715-490e-9beb-b6b910466f4e'
    async with async_session_maker() as s:
        res = await s.execute(text('SELECT id, case_id, entity_type, entity_id, role, added_at FROM case_entities WHERE case_id = :cid ORDER BY id'), {'cid': cid})
        db_rows = [dict(r) for r in res.mappings().all()]
        
    print('DB CASE_ENTITIES COUNT:', len(db_rows))
    for r in db_rows:
        print(f"  DB: {r['entity_type']} ({r['role']}) -> {r['entity_id']}")
        
    url = f'http://127.0.0.1:8000/api/v1/cases/{cid}/entities'
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req) as resp:
        api_data = json.loads(resp.read().decode())
        
    print('API CASE_ENTITIES COUNT:', len(api_data))
    for r in api_data:
        print(f"  API: {r['entity_type']} ({r['role']}) -> {r['entity_id']}")
        
    assert len(db_rows) == len(api_data), f'Count mismatch: DB {len(db_rows)} vs API {len(api_data)}'
    for db_r, api_r in zip(db_rows, api_data):
        assert str(db_r['entity_id']) == api_r['entity_id']
        assert db_r['entity_type'] == api_r['entity_type']
        assert db_r['role'] == api_r['role']
    print('SUCCESS: ALL CASE ENTITIES MATCH 100% PERFECTLY!')

asyncio.run(check())
