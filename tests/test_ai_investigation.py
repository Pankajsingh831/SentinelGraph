"""Automated tests for Phase 1 AI Case Investigation.

Covers:
- TEST 1: Event-Time-Safe Context (CaseInvestigationContextService)
- TEST 2: AI Evidence Grounding (AIInvestigator)
- TEST 3: Investigation Endpoint (POST /api/v1/cases/{case_id}/investigate)
- TEST 4: SHAP Safety & Feature Explanations
"""

import asyncio
import json
import os
import sys
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Ensure apps/api is on sys.path
api_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "apps", "api"))
if api_dir not in sys.path:
    sys.path.insert(0, api_dir)

# Mock heavy/external ML packages if not installed in current environment
for mod in ["xgboost", "shap"]:
    if mod not in sys.modules:
        sys.modules[mod] = MagicMock()

from fastapi import FastAPI, HTTPException, status
from fastapi.testclient import TestClient

from app.models.case_entity import CaseEntity
from app.models.case_evidence import CaseEvidence
from app.models.entity_relationship import EntityRelationship
from app.models.risk_case import RiskCase
from app.models.risk_prediction import RiskPrediction
from app.models.temporal_anomaly import TemporalAnomaly
from app.models.transaction import Transaction
from app.models.user import User

from app.schemas.ai import (
    InvestigateRequest,
    InvestigateResponse,
    InvestigationReport,
)
from app.repositories import risk_repo
from app.repositories.case_repo import CaseRepository
from app.services.ai_investigator import AIInvestigator
from app.services.case_investigation_context import CaseInvestigationContextService
from app.api.cases import investigate_case, router as cases_router, get_case_service
from app.database import get_db
from app.middleware.auth import get_current_user


# ---------------------------------------------------------------------------
# Helpers & Mocks
# ---------------------------------------------------------------------------

class MockQueryResult:
    """Simulates SQLAlchemy async query result with .scalars().first() and .all()."""

    def __init__(self, items: Any):
        if items is None:
            self._items = []
        elif isinstance(items, list):
            self._items = items
        else:
            self._items = [items]

    def scalars(self):
        return self

    def first(self):
        return self._items[0] if self._items else None

    def all(self):
        return list(self._items)


def create_mock_case(
    case_id: uuid.UUID | None = None,
    customer_id: uuid.UUID | None = None,
    created_at: datetime | None = None,
) -> RiskCase:
    cid = case_id or uuid.uuid4()
    cust_id = customer_id or uuid.uuid4()
    ts = created_at or datetime.now(timezone.utc)
    return RiskCase(
        case_id=cid,
        primary_entity_type="customer",
        primary_entity_id=cust_id,
        overall_risk_score=0.85,
        risk_tier="CRITICAL",
        transaction_risk_score=0.90,
        network_risk_score=0.70,
        temporal_risk_score=0.95,
        status="open",
        created_at=ts,
        updated_at=ts,
    )


def create_mock_transaction(
    transaction_id: uuid.UUID | None = None,
    customer_id: uuid.UUID | None = None,
    amount: float = 4.50,
    occurred_at: datetime | None = None,
) -> Transaction:
    tid = transaction_id or uuid.uuid4()
    cid = customer_id or uuid.uuid4()
    ts = occurred_at or datetime.now(timezone.utc)
    return Transaction(
        transaction_id=tid,
        customer_id=cid,
        amount=amount,
        currency="USD",
        transaction_type="purchase",
        status="completed",
        occurred_at=ts,
    )


def create_mock_prediction(
    transaction_id: uuid.UUID,
    risk_score: float = 0.92,
    risk_tier: str = "CRITICAL",
    predicted_at: datetime | None = None,
) -> RiskPrediction:
    ts = predicted_at or datetime.now(timezone.utc)
    return RiskPrediction(
        prediction_id=uuid.uuid4(),
        transaction_id=transaction_id,
        model_version="xgb-graph-v1",
        risk_score=risk_score,
        risk_tier=risk_tier,
        prediction_latency_ms=12,
        predicted_at=ts,
    )


def create_mock_case_data(case_id: uuid.UUID) -> dict:
    return {
        "case_id": str(case_id),
        "overall_risk_score": 0.85,
        "transaction_risk_score": 0.90,
        "network_risk_score": 0.70,
        "temporal_risk_score": 0.95,
    }


# ===========================================================================
# TEST 1 — EVENT-TIME-SAFE CONTEXT
# ===========================================================================

@pytest.mark.asyncio
async def test_1_trigger_transaction_is_exact_case_reference():
    """Verify trigger transaction query joins CaseEntity with role='trigger_transaction'."""
    case_id = uuid.uuid4()
    trigger_tx_id = uuid.uuid4()
    customer_id = uuid.uuid4()
    event_time = datetime(2026, 9, 1, 12, 0, 0, tzinfo=timezone.utc)

    exact_trigger_tx = create_mock_transaction(
        transaction_id=trigger_tx_id, customer_id=customer_id, occurred_at=event_time
    )

    captured_stmts = []

    async def mock_execute(stmt):
        captured_stmts.append(stmt)
        return MockQueryResult(exact_trigger_tx)

    mock_db = MagicMock()
    mock_db.execute = AsyncMock(side_effect=mock_execute)
    mock_repo = MagicMock(spec=CaseRepository)

    service = CaseInvestigationContextService(mock_db, mock_repo)
    result = await service._get_trigger_transaction(case_id)

    assert result is exact_trigger_tx
    assert len(captured_stmts) == 1
    query_str = str(captured_stmts[0])
    assert "case_entities.case_id = :case_id" in query_str
    assert "case_entities.entity_type = :entity_type" in query_str
    assert "case_entities.role = :role" in query_str


@pytest.mark.asyncio
async def test_2_no_fallback_to_latest_customer_transaction():
    """Verify that if no trigger_transaction entity exists, it does NOT fall back to customer txs."""
    case = create_mock_case()

    async def mock_execute(stmt):
        return MockQueryResult(None)

    mock_db = MagicMock()
    mock_db.execute = AsyncMock(side_effect=mock_execute)

    mock_repo = MagicMock(spec=CaseRepository)
    mock_repo.get_case_entities = AsyncMock(return_value=[])
    mock_repo.get_case_evidence = AsyncMock(return_value=[])

    service = CaseInvestigationContextService(mock_db, mock_repo)
    context = await service.build(case)

    # Must report unavailable with explicit reason, NOT fall back to customer's latest transaction
    assert context["trigger_transaction"]["available"] is False
    assert "No explicit trigger_transaction" in context["trigger_transaction"]["reason"]
    assert context["transaction_prediction"]["available"] is False
    assert context["shap_features"]["available"] is False
    assert context["graph_statistics"]["available"] is False
    assert context["temporal_anomalies"] == []
    assert context["timeline"] == []


@pytest.mark.asyncio
async def test_3_risk_prediction_retrieval_exact_transaction_and_event_time_cutoff():
    """Verify get_prediction_for_transaction_at_or_before strictly filters transaction_id and predicted_at <= event_time."""
    tx_id = uuid.uuid4()
    event_time = datetime(2026, 9, 1, 12, 0, 0, tzinfo=timezone.utc)
    valid_pred = create_mock_prediction(transaction_id=tx_id, predicted_at=event_time)

    captured_stmts = []

    async def mock_execute(stmt):
        captured_stmts.append(stmt)
        return MockQueryResult(valid_pred)

    mock_db = MagicMock()
    mock_db.execute = AsyncMock(side_effect=mock_execute)

    result = await risk_repo.get_prediction_for_transaction_at_or_before(mock_db, tx_id, event_time)

    assert result is valid_pred
    assert len(captured_stmts) == 1
    query_str = str(captured_stmts[0])
    assert "risk_predictions.transaction_id = :transaction_id_1" in query_str
    assert "risk_predictions.predicted_at <= :predicted_at_1" in query_str
    assert "ORDER BY risk_predictions.predicted_at DESC" in query_str


@pytest.mark.asyncio
async def test_4_future_prediction_ignored():
    """Verify a prediction generated after event_time is ignored by the event-time-safe query."""
    tx_id = uuid.uuid4()
    event_time = datetime(2026, 9, 1, 12, 0, 0, tzinfo=timezone.utc)

    # When the database enforces predicted_at <= event_time, a future prediction is not returned
    async def mock_execute(stmt):
        return MockQueryResult(None)

    mock_db = MagicMock()
    mock_db.execute = AsyncMock(side_effect=mock_execute)

    result = await risk_repo.get_prediction_for_transaction_at_or_before(mock_db, tx_id, event_time)
    assert result is None

    # In context assembly, missing/future prediction is noted as unavailable with reason
    trigger_tx = create_mock_transaction(transaction_id=tx_id, occurred_at=event_time)
    case = create_mock_case()

    mock_repo = MagicMock(spec=CaseRepository)
    mock_repo.get_case_entities = AsyncMock(return_value=[])
    mock_repo.get_case_evidence = AsyncMock(return_value=[])

    service = CaseInvestigationContextService(mock_db, mock_repo)
    with patch.object(service, "_get_trigger_transaction", AsyncMock(return_value=trigger_tx)), \
         patch.object(risk_repo, "get_prediction_for_transaction_at_or_before", AsyncMock(return_value=None)), \
         patch.object(service, "_get_temporal_anomalies", AsyncMock(return_value=[])), \
         patch.object(service, "_get_case_transactions", AsyncMock(return_value=[])), \
         patch.object(service, "_get_graph_statistics", AsyncMock(return_value={"available": True})), \
         patch.object(service, "_get_shap_features", AsyncMock(return_value={"available": False})):

        context = await service.build(case)
        assert context["transaction_prediction"]["available"] is False
        assert "No prediction for the exact trigger transaction exists at or before" in context["transaction_prediction"]["reason"]


@pytest.mark.asyncio
async def test_5_graph_relationships_after_event_time_ignored():
    """Verify graph query excludes relationships first seen after event_time."""
    event_time = datetime(2026, 9, 1, 12, 0, 0, tzinfo=timezone.utc)
    cust_id = uuid.uuid4()
    entities = [CaseEntity(case_id=uuid.uuid4(), entity_type="customer", entity_id=cust_id, role="primary")]

    captured_stmts = []

    async def mock_execute(stmt):
        captured_stmts.append(stmt)
        return MockQueryResult([])

    mock_db = MagicMock()
    mock_db.execute = AsyncMock(side_effect=mock_execute)
    mock_repo = MagicMock(spec=CaseRepository)

    service = CaseInvestigationContextService(mock_db, mock_repo)
    await service._get_graph_statistics(entities, event_time)

    assert len(captured_stmts) == 1
    query_str = str(captured_stmts[0])
    assert "entity_relationships.first_seen_at <= :first_seen_at_1" in query_str


@pytest.mark.asyncio
async def test_6_temporal_anomalies_after_event_time_ignored():
    """Verify temporal anomaly query excludes anomalies with window_end > event_time."""
    event_time = datetime(2026, 9, 1, 12, 0, 0, tzinfo=timezone.utc)
    cust_id = uuid.uuid4()
    entities = [CaseEntity(case_id=uuid.uuid4(), entity_type="customer", entity_id=cust_id, role="primary")]

    captured_stmts = []

    async def mock_execute(stmt):
        captured_stmts.append(stmt)
        return MockQueryResult([])

    mock_db = MagicMock()
    mock_db.execute = AsyncMock(side_effect=mock_execute)
    mock_repo = MagicMock(spec=CaseRepository)

    service = CaseInvestigationContextService(mock_db, mock_repo)
    await service._get_temporal_anomalies(entities, event_time)

    assert len(captured_stmts) == 1
    query_str = str(captured_stmts[0])
    assert "temporal_anomalies.window_end <= :window_end_1" in query_str


@pytest.mark.asyncio
async def test_7_timeline_transactions_after_event_time_ignored():
    """Verify timeline transaction query excludes transactions with occurred_at > event_time."""
    event_time = datetime(2026, 9, 1, 12, 0, 0, tzinfo=timezone.utc)
    cust_id = uuid.uuid4()
    entities = [CaseEntity(case_id=uuid.uuid4(), entity_type="customer", entity_id=cust_id, role="primary")]

    captured_stmts = []

    async def mock_execute(stmt):
        captured_stmts.append(stmt)
        return MockQueryResult([])

    mock_db = MagicMock()
    mock_db.execute = AsyncMock(side_effect=mock_execute)
    mock_repo = MagicMock(spec=CaseRepository)

    service = CaseInvestigationContextService(mock_db, mock_repo)
    await service._get_case_transactions(entities, event_time)

    assert len(captured_stmts) == 1
    query_str = str(captured_stmts[0])
    assert "transactions.occurred_at <= :occurred_at_1" in query_str


@pytest.mark.asyncio
async def test_8_missing_network_risk_represented_as_unavailable():
    """Verify missing network risk record is explicitly marked unavailable rather than fabricated."""
    case = create_mock_case()
    mock_db = MagicMock()
    mock_db.execute = AsyncMock(return_value=MockQueryResult(None))
    mock_repo = MagicMock(spec=CaseRepository)
    mock_repo.get_case_entities = AsyncMock(return_value=[])
    mock_repo.get_case_evidence = AsyncMock(return_value=[])

    service = CaseInvestigationContextService(mock_db, mock_repo)
    context = await service.build(case)

    assert "network_risk_record" in context
    assert context["network_risk_record"]["available"] is False
    assert "Network risk records are not linked to a transaction or entity" in context["network_risk_record"]["reason"]


@pytest.mark.asyncio
async def test_9_case_entities_and_evidence_come_from_actual_case():
    """Verify case entities and case evidence are fetched specifically for the case_id."""
    case = create_mock_case()
    eid = uuid.uuid4()
    evidence_id = uuid.uuid4()

    mock_entities = [
        CaseEntity(case_id=case.case_id, entity_type="customer", entity_id=eid, role="primary")
    ]
    mock_evidence = [
        CaseEvidence(
            evidence_id=evidence_id,
            case_id=case.case_id,
            evidence_type="velocity_spike",
            severity="HIGH",
            entity_type="customer",
            entity_id=eid,
            description="Card testing velocity spike detected",
            evidence_data={"spike_count": 25},
        )
    ]

    mock_db = MagicMock()
    mock_db.execute = AsyncMock(return_value=MockQueryResult(None))
    mock_repo = MagicMock(spec=CaseRepository)
    mock_repo.get_case_entities = AsyncMock(return_value=mock_entities)
    mock_repo.get_case_evidence = AsyncMock(return_value=mock_evidence)

    service = CaseInvestigationContextService(mock_db, mock_repo)
    context = await service.build(case)

    mock_repo.get_case_entities.assert_awaited_once_with(case.case_id)
    mock_repo.get_case_evidence.assert_awaited_once_with(case.case_id)

    assert len(context["case_entities"]) == 1
    assert context["case_entities"][0]["entity_id"] == str(eid)
    assert context["case_entities"][0]["reference"] == f"customer:{eid}"

    assert len(context["case_evidence"]) == 1
    assert context["case_evidence"][0]["evidence_id"] == str(evidence_id)
    assert context["case_evidence"][0]["description"] == "Card testing velocity spike detected"


@pytest.mark.asyncio
async def test_10_no_future_data_introduced():
    """Verify that all temporal context sections strictly respect event_time cutoff."""
    case = create_mock_case()
    trigger_tx_id = uuid.uuid4()
    event_time = datetime(2026, 9, 1, 12, 0, 0, tzinfo=timezone.utc)
    trigger_tx = create_mock_transaction(transaction_id=trigger_tx_id, occurred_at=event_time)

    # Valid pre-event prediction
    pred = create_mock_prediction(transaction_id=trigger_tx_id, predicted_at=event_time)

    # Valid pre-event temporal anomaly
    anomaly = TemporalAnomaly(
        anomaly_id=uuid.uuid4(),
        entity_type="customer",
        entity_id=uuid.uuid4(),
        anomaly_type="velocity_spike",
        baseline_value=1.0,
        observed_value=25.0,
        anomaly_score=0.95,
        window_start=event_time - timedelta(minutes=5),
        window_end=event_time,
        detected_at=event_time,
    )

    # Valid pre-event timeline transaction
    past_tx = create_mock_transaction(occurred_at=event_time - timedelta(minutes=2))

    mock_db = MagicMock()
    mock_repo = MagicMock(spec=CaseRepository)
    mock_repo.get_case_entities = AsyncMock(return_value=[])
    mock_repo.get_case_evidence = AsyncMock(return_value=[])

    service = CaseInvestigationContextService(mock_db, mock_repo)
    with patch.object(service, "_get_trigger_transaction", AsyncMock(return_value=trigger_tx)), \
         patch.object(risk_repo, "get_prediction_for_transaction_at_or_before", AsyncMock(return_value=pred)), \
         patch.object(service, "_get_temporal_anomalies", AsyncMock(return_value=[anomaly])), \
         patch.object(service, "_get_case_transactions", AsyncMock(return_value=[past_tx])), \
         patch.object(service, "_get_graph_statistics", AsyncMock(return_value={"available": True, "event_time_cutoff": event_time.isoformat()})), \
         patch.object(service, "_get_shap_features", AsyncMock(return_value={"available": True, "top_features": []})):

        context = await service.build(case)

        assert context["trigger_transaction"]["occurred_at"] == event_time.isoformat()
        assert context["transaction_prediction"]["predicted_at"] == event_time.isoformat()
        assert context["temporal_anomalies"][0]["window_end"] <= event_time.isoformat()
        assert context["timeline"][0]["timestamp"] <= event_time.isoformat()
        assert context["graph_statistics"]["event_time_cutoff"] == event_time.isoformat()


# ===========================================================================
# TEST 2 — AI EVIDENCE GROUNDING
# ===========================================================================

@pytest.mark.asyncio
async def test_11_valid_evidence_id_accepted():
    """Verify that a valid evidence ID belonging to the case is accepted."""
    case_id = uuid.uuid4()
    evidence_id = str(uuid.uuid4())
    customer_id = str(uuid.uuid4())

    case_data = {
        "case_id": str(case_id),
        "overall_risk_score": 0.85,
        "transaction_risk_score": 0.90,
        "network_risk_score": 0.70,
        "temporal_risk_score": 0.95,
    }
    evidence = [{"evidence_id": evidence_id, "evidence_type": "velocity_spike", "severity": "HIGH", "description": "Burst"}]
    entities = [{"entity_id": customer_id, "entity_type": "customer"}]

    mock_report_json = json.dumps({
        "summary": "Card testing attack detected on customer.",
        "risk_level": "CRITICAL",
        "key_evidence": [evidence_id],
        "affected_entities": [f"customer:{customer_id}"],
        "recommended_action": "CONFIRMED_ABUSE",
        "confidence": 0.95,
    })

    investigator = AIInvestigator()
    investigator.client = MagicMock()
    investigator.enabled = True

    mock_response = MagicMock()
    mock_response.content = [MagicMock(text=mock_report_json)]
    investigator.client.messages.create = MagicMock(return_value=mock_response)

    res = await investigator.investigate(
        case_id=case_id,
        case_data=case_data,
        evidence=evidence,
        case_entities=entities,
    )

    assert res.report is not None
    assert res.grounded is True
    assert res.report.key_evidence == [evidence_id]
    assert res.report.recommended_action == "CONFIRMED_ABUSE"


@pytest.mark.asyncio
async def test_12_invalid_evidence_id_rejected_and_falls_back():
    """Verify that an evidence ID not belonging to the case is rejected, retries, and safely falls back."""
    case_id = uuid.uuid4()
    real_evidence_id = str(uuid.uuid4())
    fake_evidence_id = str(uuid.uuid4())
    customer_id = str(uuid.uuid4())

    case_data = create_mock_case_data(case_id)
    evidence = [{"evidence_id": real_evidence_id, "evidence_type": "velocity_spike"}]
    entities = [{"entity_id": customer_id, "entity_type": "customer"}]

    # Provider outputs an ungrounded evidence ID
    mock_report_json = json.dumps({
        "summary": "Hallucinated evidence report.",
        "risk_level": "HIGH",
        "key_evidence": [fake_evidence_id],
        "affected_entities": [customer_id],
        "recommended_action": "ESCALATE",
        "confidence": 0.80,
    })

    investigator = AIInvestigator()
    investigator.client = MagicMock()
    investigator.enabled = True

    mock_response = MagicMock()
    mock_response.content = [MagicMock(text=mock_report_json)]
    investigator.client.messages.create = MagicMock(return_value=mock_response)

    res = await investigator.investigate(
        case_id=case_id,
        case_data=case_data,
        evidence=evidence,
        case_entities=entities,
    )

    # Validation must fail grounding, retry once, and return safe fallback
    assert investigator.client.messages.create.call_count == 2
    assert res.report is None
    assert res.grounded is False
    assert "AI failed to generate a valid and grounded report" in res.fallback_message


@pytest.mark.asyncio
async def test_13_valid_entity_reference_formats_accepted():
    """Verify both bare entity_id and entity_type:entity_id formats are accepted."""
    case_id = uuid.uuid4()
    evidence_id = str(uuid.uuid4())
    customer_id = str(uuid.uuid4())

    case_data = create_mock_case_data(case_id)
    evidence = [{"evidence_id": evidence_id}]
    entities = [{"entity_id": customer_id, "entity_type": "customer"}]

    # Test bare UUID
    investigator = AIInvestigator()
    investigator.client = MagicMock()
    investigator.enabled = True

    mock_report_json = json.dumps({
        "summary": "Bare entity ID test.",
        "risk_level": "HIGH",
        "key_evidence": [evidence_id],
        "affected_entities": [customer_id],
        "recommended_action": "ESCALATE",
        "confidence": 0.85,
    })
    investigator.client.messages.create = MagicMock(return_value=MagicMock(content=[MagicMock(text=mock_report_json)]))

    res_bare = await investigator.investigate(case_id=case_id, case_data=case_data, evidence=evidence, case_entities=entities)
    assert res_bare.report is not None
    assert res_bare.grounded is True

    # Test typed reference "customer:<id>"
    mock_report_typed = json.dumps({
        "summary": "Typed entity reference test.",
        "risk_level": "HIGH",
        "key_evidence": [evidence_id],
        "affected_entities": [f"customer:{customer_id}"],
        "recommended_action": "ESCALATE",
        "confidence": 0.85,
    })
    investigator.client.messages.create = MagicMock(return_value=MagicMock(content=[MagicMock(text=mock_report_typed)]))

    res_typed = await investigator.investigate(case_id=case_id, case_data=case_data, evidence=evidence, case_entities=entities)
    assert res_typed.report is not None
    assert res_typed.grounded is True


@pytest.mark.asyncio
async def test_14_invalid_entity_reference_rejected_and_falls_back():
    """Verify an entity reference not belonging to the case is rejected and falls back safely."""
    case_id = uuid.uuid4()
    evidence_id = str(uuid.uuid4())
    customer_id = str(uuid.uuid4())
    fake_entity = str(uuid.uuid4())

    case_data = create_mock_case_data(case_id)
    evidence = [{"evidence_id": evidence_id}]
    entities = [{"entity_id": customer_id, "entity_type": "customer"}]

    mock_report_json = json.dumps({
        "summary": "Report with hallucinated entity.",
        "risk_level": "HIGH",
        "key_evidence": [evidence_id],
        "affected_entities": [fake_entity],
        "recommended_action": "ESCALATE",
        "confidence": 0.75,
    })

    investigator = AIInvestigator()
    investigator.client = MagicMock()
    investigator.enabled = True
    investigator.client.messages.create = MagicMock(return_value=MagicMock(content=[MagicMock(text=mock_report_json)]))

    res = await investigator.investigate(case_id=case_id, case_data=case_data, evidence=evidence, case_entities=entities)

    assert res.report is None
    assert res.grounded is False
    assert "AI failed to generate a valid and grounded report" in res.fallback_message


@pytest.mark.asyncio
async def test_15_invalid_provider_json_safe_fallback():
    """Verify that invalid provider JSON safely triggers retry and returns fallback without crashing."""
    case_id = uuid.uuid4()
    evidence = [{"evidence_id": str(uuid.uuid4())}]

    investigator = AIInvestigator()
    investigator.client = MagicMock()
    investigator.enabled = True
    # Non-JSON plain text response
    investigator.client.messages.create = MagicMock(return_value=MagicMock(content=[MagicMock(text="Here is my explanation: suspicious activity.")]))

    res = await investigator.investigate(
        case_id=case_id,
        case_data=create_mock_case_data(case_id),
        evidence=evidence,
    )

    assert investigator.client.messages.create.call_count == 2
    assert res.report is None
    assert res.grounded is False
    assert "AI failed to generate a valid and grounded report" in res.fallback_message


@pytest.mark.asyncio
async def test_16_provider_api_failure_safe_fallback():
    """Verify that provider exception / API error safely returns fallback message."""
    case_id = uuid.uuid4()
    evidence = [{"evidence_id": str(uuid.uuid4())}]

    investigator = AIInvestigator()
    investigator.client = MagicMock()
    investigator.enabled = True
    investigator.client.messages.create = MagicMock(side_effect=RuntimeError("Anthropic connection timeout"))

    res = await investigator.investigate(
        case_id=case_id,
        case_data=create_mock_case_data(case_id),
        evidence=evidence,
    )

    assert res.report is None
    assert res.grounded is False
    assert "AI investigation is temporarily unavailable; the case and its evidence remain available." in res.fallback_message


@pytest.mark.asyncio
async def test_17_missing_provider_configuration_safe_fallback():
    """Verify missing provider / disabled configuration does not break endpoint and returns safe response."""
    case_id = uuid.uuid4()
    evidence = [{"evidence_id": str(uuid.uuid4())}]

    # Case 1: client is None
    inv_no_client = AIInvestigator()
    inv_no_client.client = None
    res1 = await inv_no_client.investigate(case_id=case_id, case_data=create_mock_case_data(case_id), evidence=evidence)
    assert res1.report is None
    assert res1.grounded is False
    assert "AI Investigator is unavailable because no provider is configured." in res1.fallback_message

    # Case 2: enabled is False
    inv_disabled = AIInvestigator()
    inv_disabled.enabled = False
    res2 = await inv_disabled.investigate(case_id=case_id, case_data=create_mock_case_data(case_id), evidence=evidence)
    assert res2.report is None
    assert res2.grounded is False
    assert "AI Investigator is unavailable because no provider is configured." in res2.fallback_message


# ===========================================================================
# TEST 3 — INVESTIGATION ENDPOINT
# ===========================================================================

@pytest.mark.asyncio
async def test_18_endpoint_investigate_existing_case_success():
    """Verify investigate_case endpoint successfully builds context and returns InvestigateResponse."""
    case_id = uuid.uuid4()
    mock_case = create_mock_case(case_id=case_id)
    evidence_id = str(uuid.uuid4())
    customer_id = str(uuid.uuid4())

    mock_case_service = MagicMock()
    mock_case_service.get_case = AsyncMock(return_value=mock_case)
    mock_case_service.case_repo = MagicMock(spec=CaseRepository)

    mock_context = {
        "case_id": str(case_id),
        "case_evidence": [{"evidence_id": evidence_id, "evidence_type": "velocity_spike", "severity": "CRITICAL"}],
        "case_entities": [{"entity_id": customer_id, "entity_type": "customer"}],
    }

    mock_report = InvestigationReport(
        summary="Automated velocity abuse investigation.",
        risk_level="CRITICAL",
        key_evidence=[evidence_id],
        affected_entities=[customer_id],
        recommended_action="CONFIRMED_ABUSE",
        confidence=0.98,
    )
    expected_response = InvestigateResponse(case_id=case_id, report=mock_report, grounded=True)

    mock_user = User(user_id="analyst-1", username="analyst", role="analyst")
    mock_db = MagicMock()

    with patch("app.api.cases.CaseInvestigationContextService") as MockContextService, \
         patch("app.api.cases.AIInvestigator") as MockInvestigator:

        ctx_instance = MockContextService.return_value
        ctx_instance.build = AsyncMock(return_value=mock_context)

        inv_instance = MockInvestigator.return_value
        inv_instance.investigate = AsyncMock(return_value=expected_response)

        response = await investigate_case(
            case_id=case_id,
            request=InvestigateRequest(follow_up_question=None),
            user=mock_user,
            case_service=mock_case_service,
            db=mock_db,
        )

        assert response == expected_response
        inv_instance.investigate.assert_awaited_once_with(
            case_id=case_id,
            case_data=mock_context,
            evidence=mock_context["case_evidence"],
            case_entities=mock_context["case_entities"],
            follow_up_question=None,
        )


@pytest.mark.asyncio
async def test_19_endpoint_follow_up_question_passed():
    """Verify follow-up question is passed to the AIInvestigator."""
    case_id = uuid.uuid4()
    mock_case = create_mock_case(case_id=case_id)
    question = "Is this related to card testing burst?"

    mock_case_service = MagicMock()
    mock_case_service.get_case = AsyncMock(return_value=mock_case)
    mock_case_service.case_repo = MagicMock(spec=CaseRepository)

    mock_context = {
        "case_id": str(case_id),
        "case_evidence": [{"evidence_id": str(uuid.uuid4())}],
        "case_entities": [],
    }

    mock_user = User(user_id="analyst-1", username="analyst", role="analyst")

    with patch("app.api.cases.CaseInvestigationContextService") as MockContextService, \
         patch("app.api.cases.AIInvestigator") as MockInvestigator:

        MockContextService.return_value.build = AsyncMock(return_value=mock_context)
        inv_instance = MockInvestigator.return_value
        inv_instance.investigate = AsyncMock(return_value=InvestigateResponse(case_id=case_id))

        await investigate_case(
            case_id=case_id,
            request=InvestigateRequest(follow_up_question=question),
            user=mock_user,
            case_service=mock_case_service,
            db=MagicMock(),
        )

        assert inv_instance.investigate.call_args.kwargs["follow_up_question"] == question


@pytest.mark.asyncio
async def test_20_endpoint_provider_unavailable_or_failure_fallback():
    """Verify provider fallback response is propagated with HTTP 200."""
    case_id = uuid.uuid4()
    mock_case = create_mock_case(case_id=case_id)

    mock_case_service = MagicMock()
    mock_case_service.get_case = AsyncMock(return_value=mock_case)
    mock_case_service.case_repo = MagicMock(spec=CaseRepository)

    mock_context = {
        "case_id": str(case_id),
        "case_evidence": [{"evidence_id": str(uuid.uuid4())}],
        "case_entities": [],
    }
    fallback_resp = InvestigateResponse(
        case_id=case_id,
        fallback_message="AI investigation is temporarily unavailable; the case and its evidence remain available.",
        grounded=False,
    )

    with patch("app.api.cases.CaseInvestigationContextService") as MockContextService, \
         patch("app.api.cases.AIInvestigator") as MockInvestigator:

        MockContextService.return_value.build = AsyncMock(return_value=mock_context)
        MockInvestigator.return_value.investigate = AsyncMock(return_value=fallback_resp)

        res = await investigate_case(
            case_id=case_id,
            request=InvestigateRequest(),
            user=User(user_id="analyst-1", username="analyst", role="analyst"),
            case_service=mock_case_service,
            db=MagicMock(),
        )

        assert res.report is None
        assert res.grounded is False
        assert "temporarily unavailable" in res.fallback_message


@pytest.mark.asyncio
async def test_21_endpoint_no_evidence_returns_422():
    """Verify case without evidence raises HTTPException 422 NO_EVIDENCE_FOR_INVESTIGATION."""
    case_id = uuid.uuid4()
    mock_case = create_mock_case(case_id=case_id)

    mock_case_service = MagicMock()
    mock_case_service.get_case = AsyncMock(return_value=mock_case)
    mock_case_service.case_repo = MagicMock(spec=CaseRepository)

    # Empty evidence in context
    mock_context = {
        "case_id": str(case_id),
        "case_evidence": [],
        "case_entities": [],
    }

    with patch("app.api.cases.CaseInvestigationContextService") as MockContextService:
        MockContextService.return_value.build = AsyncMock(return_value=mock_context)

        with pytest.raises(HTTPException) as exc_info:
            await investigate_case(
                case_id=case_id,
                request=InvestigateRequest(),
                user=User(user_id="analyst-1", username="analyst", role="analyst"),
                case_service=mock_case_service,
                db=MagicMock(),
            )

        assert exc_info.value.status_code == 422
        assert exc_info.value.detail == "NO_EVIDENCE_FOR_INVESTIGATION"


@pytest.mark.asyncio
async def test_22_endpoint_nonexistent_case_returns_404():
    """Verify requesting investigation for a nonexistent case raises HTTPException 404 CASE_NOT_FOUND."""
    case_id = uuid.uuid4()
    mock_case_service = MagicMock()
    mock_case_service.get_case = AsyncMock(return_value=None)

    with pytest.raises(HTTPException) as exc_info:
        await investigate_case(
            case_id=case_id,
            request=InvestigateRequest(),
            user=User(user_id="analyst-1", username="analyst", role="analyst"),
            case_service=mock_case_service,
            db=MagicMock(),
        )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "CASE_NOT_FOUND"


def test_23_endpoint_auth_enforced():
    """Verify that the investigate route specifies authentication dependency."""
    investigate_route = None
    for route in cases_router.routes:
        if route.path.endswith("/investigate") and "POST" in route.methods:
            investigate_route = route
            break

    assert investigate_route is not None, "Route POST /{case_id}/investigate not found in cases router"

    import inspect
    sig = inspect.signature(investigate_route.endpoint)
    user_param = sig.parameters.get("user")
    assert user_param is not None
    assert user_param.default.dependency == get_current_user


def test_24_endpoint_full_http_testclient():
    """Verify endpoint over HTTP using FastAPI TestClient with auth and unauth requests."""
    test_app = FastAPI()
    test_app.include_router(cases_router)

    case_id = uuid.uuid4()
    evidence_id = str(uuid.uuid4())

    mock_case = create_mock_case(case_id=case_id)
    mock_case_service = MagicMock()
    mock_case_service.get_case = AsyncMock(return_value=mock_case)
    mock_case_service.case_repo = MagicMock(spec=CaseRepository)

    mock_context = {
        "case_id": str(case_id),
        "case_evidence": [{"evidence_id": evidence_id, "evidence_type": "velocity"}],
        "case_entities": [],
    }

    mock_db = MagicMock()

    # 1. Unauthenticated request -> should fail with 401 Unauthorized
    client = TestClient(test_app)
    unauth_resp = client.post(f"/api/v1/cases/{case_id}/investigate", json={})
    assert unauth_resp.status_code == 401

    # 2. Authenticated request with dependency overrides
    test_app.dependency_overrides[get_current_user] = lambda: User(user_id="test-user", username="analyst", role="analyst")
    test_app.dependency_overrides[get_case_service] = lambda: mock_case_service
    test_app.dependency_overrides[get_db] = lambda: mock_db

    with patch("app.api.cases.CaseInvestigationContextService") as MockContextService, \
         patch("app.api.cases.AIInvestigator") as MockInvestigator:

        MockContextService.return_value.build = AsyncMock(return_value=mock_context)
        MockInvestigator.return_value.investigate = AsyncMock(
            return_value=InvestigateResponse(
                case_id=case_id,
                fallback_message="AI Investigator is unavailable because no provider is configured.",
                grounded=False,
            )
        )

        auth_resp = client.post(
            f"/api/v1/cases/{case_id}/investigate",
            json={"follow_up_question": "Check card testing"},
        )
        assert auth_resp.status_code == 200
        data = auth_resp.json()
        assert data["case_id"] == str(case_id)
        assert data["grounded"] is False
        assert "no provider is configured" in data["fallback_message"]

    test_app.dependency_overrides.clear()


# ===========================================================================
# TEST 4 — SHAP SAFETY
# ===========================================================================

@pytest.mark.asyncio
async def test_25_shap_requires_event_time_safe_prediction():
    """Verify that if prediction is None, SHAP features are marked unavailable without executing feature extraction."""
    mock_db = MagicMock()
    mock_repo = MagicMock(spec=CaseRepository)
    service = CaseInvestigationContextService(mock_db, mock_repo)

    tx = create_mock_transaction()
    shap_res = await service._get_shap_features(tx, prediction=None)

    assert shap_res["available"] is False
    assert "No event-time-safe prediction is available" in shap_res["reason"]


@pytest.mark.asyncio
async def test_26_shap_unavailable_when_model_or_explainer_missing():
    """Verify context explicitly indicates unavailable if model or explainer cannot be loaded."""
    mock_db = MagicMock()
    mock_repo = MagicMock(spec=CaseRepository)
    service = CaseInvestigationContextService(mock_db, mock_repo)

    tx = create_mock_transaction()
    pred = create_mock_prediction(transaction_id=tx.transaction_id)

    with patch("app.services.case_investigation_context.get_model", return_value=(None, None, [])):
        shap_res = await service._get_shap_features(tx, prediction=pred)

        assert shap_res["available"] is False
        assert "configured model or SHAP explainer is unavailable" in shap_res["reason"]


@pytest.mark.asyncio
async def test_27_shap_error_handling_no_fabrication():
    """Verify that an exception during SHAP extraction marks it unavailable with reason and never fabricates values."""
    mock_db = MagicMock()
    mock_repo = MagicMock(spec=CaseRepository)
    service = CaseInvestigationContextService(mock_db, mock_repo)

    tx = create_mock_transaction()
    pred = create_mock_prediction(transaction_id=tx.transaction_id)

    mock_model = MagicMock()
    mock_explainer = MagicMock()
    feature_names = ["tx_amount", "velocity_5m"]

    with patch("app.services.case_investigation_context.get_model", return_value=(mock_model, mock_explainer, feature_names)), \
         patch("app.services.case_investigation_context.extract_features_for_transaction", side_effect=ValueError("Feature extraction error")):

        shap_res = await service._get_shap_features(tx, prediction=pred)

        assert shap_res["available"] is False
        assert "SHAP calculation was unavailable" in shap_res["reason"]
        assert "top_features" not in shap_res


@pytest.mark.asyncio
async def test_28_shap_successful_top_features_sorted_by_abs_contribution():
    """Verify successful SHAP returns top 5 features strictly sorted by absolute contribution."""
    mock_db = MagicMock()
    mock_repo = MagicMock(spec=CaseRepository)
    service = CaseInvestigationContextService(mock_db, mock_repo)

    tx = create_mock_transaction()
    pred = create_mock_prediction(transaction_id=tx.transaction_id)

    mock_model = MagicMock()
    mock_explainer = MagicMock()

    feature_names = ["f1", "f2", "f3", "f4", "f5", "f6"]
    import numpy as np
    mock_features = np.array([[1.0, 2.0, 3.0, 4.0, 5.0, 6.0]])
    mock_shap_values = np.array([[0.1, -0.7, 0.3, 0.8, -0.2, 0.05]])

    mock_explainer.shap_values = MagicMock(return_value=mock_shap_values)

    with patch("app.services.case_investigation_context.get_model", return_value=(mock_model, mock_explainer, feature_names)), \
         patch("app.services.case_investigation_context.extract_features_for_transaction", AsyncMock(return_value=mock_features)):

        shap_res = await service._get_shap_features(tx, prediction=pred)

        assert shap_res["available"] is True
        top_features = shap_res["top_features"]
        assert len(top_features) == 5

        # Sorted by abs contribution: f4 (0.8), f2 (-0.7), f3 (0.3), f5 (-0.2), f1 (0.1)
        assert top_features[0]["name"] == "f4"
        assert top_features[0]["contribution"] == 0.8
        assert top_features[1]["name"] == "f2"
        assert top_features[1]["contribution"] == -0.7
        assert top_features[2]["name"] == "f3"
        assert top_features[3]["name"] == "f5"
        assert top_features[4]["name"] == "f1"
