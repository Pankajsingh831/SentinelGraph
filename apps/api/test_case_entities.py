import asyncio
import uuid
import pytest
from app.database import async_session_maker, engine
from app.repositories.case_repo import CaseRepository
from app.models.case_entity import CaseEntity


def test_get_case_entities_returns_persisted_records():
    """Verify get_case_entities returns actual persisted CaseEntity rows rather than an empty list."""
    async def run():
        case_id = uuid.UUID("0adbb74e-2715-490e-9beb-b6b910466f4e")
        async with async_session_maker() as session:
            repo = CaseRepository(session)
            entities = await repo.get_case_entities(case_id)
            
            # Verify exactly 6 persisted entities
            assert len(entities) == 6, f"Expected 6 entities, got {len(entities)}"
            
            # Verify all expected entity types are present
            entity_types = {e.entity_type for e in entities}
            expected_types = {"customer", "transaction", "merchant", "device", "instrument", "ip"}
            assert entity_types == expected_types, f"Entity types mismatch: {entity_types}"
            
            for entity in entities:
                assert isinstance(entity, CaseEntity)
                assert entity.case_id == case_id
                assert entity.entity_id is not None
                assert entity.role is not None
                assert entity.added_at is not None
        await engine.dispose()

    asyncio.run(run())


def test_get_case_entities_nonexistent_case():
    """Verify get_case_entities returns empty list for nonexistent case."""
    async def run():
        nonexistent_id = uuid.uuid4()
        async with async_session_maker() as session:
            repo = CaseRepository(session)
            entities = await repo.get_case_entities(nonexistent_id)
            assert entities == []
        await engine.dispose()

    asyncio.run(run())
