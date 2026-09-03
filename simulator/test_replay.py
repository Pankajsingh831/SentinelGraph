import pytest
import datetime
import uuid
import decimal
import json
import importlib.util
from unittest.mock import patch, MagicMock

from simulator.replay_events import json_serializer

# Dynamically import graph-worker/pg_ops.py
spec = importlib.util.spec_from_file_location("pg_ops", "services/graph-worker/pg_ops.py")
pg_ops = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pg_ops)

def test_json_serializer():
    uid = uuid.uuid4()
    dt = datetime.datetime(2024, 1, 1, 12, 0, 0, tzinfo=datetime.timezone.utc)
    dec = decimal.Decimal("150.50")
    
    assert json_serializer(uid) == str(uid)
    assert json_serializer(dt) == "2024-01-01T12:00:00+00:00"
    assert json_serializer(dec) == 150.5
    
    with pytest.raises(TypeError):
        json_serializer(object())

@patch.object(pg_ops.psycopg2, 'connect')
def test_pg_upsert_first_seen_at(mock_connect):
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_connect.return_value.__enter__.return_value = mock_conn
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    
    event = {
        'occurred_at': "2024-01-01T12:00:00+00:00",
        'customer_id': "c1",
        'device_id': "d1",
        'ip_id': "ip1",
        'instrument_id': None
    }
    
    pg_ops.upsert_entity_relationships("fake_db", event)
    
    # Extract the executed query and args
    call_args = mock_cursor.execute.call_args_list
    assert len(call_args) == 2 # 1 for device, 1 for IP
    
    # Check that first_seen_at and LEAST logic is in the query
    query = call_args[0][0][0]
    assert "first_seen_at, last_seen_at" in query
    assert "first_seen_at = LEAST(entity_relationships.first_seen_at, EXCLUDED.first_seen_at)" in query
    assert "last_seen_at = GREATEST(entity_relationships.last_seen_at, EXCLUDED.last_seen_at)" in query
    
    # Check args contain the timestamp correctly
    args = call_args[0][0][1]
    assert isinstance(args[-1], datetime.datetime) # The last parameter is occurred_at
    assert isinstance(args[-2], datetime.datetime) # The second to last parameter is occurred_at
    assert len(args) == 8 # rel_id, src_type, src_id, rel_type, dst_type, dst_id, occurred_at, occurred_at

def test_replay_query_ordering():
    from simulator.replay_events import replay_events
    import inspect
    source = inspect.getsource(replay_events)
    assert "ORDER BY occurred_at ASC" in source
