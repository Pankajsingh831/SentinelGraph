"""Event-time-safe context assembly for the optional AI investigator."""

import asyncio
from typing import Any

import structlog
from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.risk import extract_features_for_transaction, get_model
from app.models.case_entity import CaseEntity
from app.models.entity_relationship import EntityRelationship
from app.models.temporal_anomaly import TemporalAnomaly
from app.models.transaction import Transaction
from app.repositories import risk_repo
from app.repositories.case_repo import CaseRepository

logger = structlog.get_logger()


class CaseInvestigationContextService:
    """Assemble only persisted, case-linked facts for an AI investigation."""

    def __init__(self, db: AsyncSession, case_repo: CaseRepository):
        self.db = db
        self.case_repo = case_repo

    async def build(self, case) -> dict[str, Any]:
        entities = await self.case_repo.get_case_entities(case.case_id)
        evidence = await self.case_repo.get_case_evidence(case.case_id)
        trigger_transaction = await self._get_trigger_transaction(case.case_id)

        context = {
            "case_id": str(case.case_id),
            "risk_scores": {
                "overall": case.overall_risk_score,
                "transaction": case.transaction_risk_score,
                "network": case.network_risk_score,
                "temporal": case.temporal_risk_score,
            },
            "case_entities": [
                {
                    "reference": f"{entity.entity_type}:{entity.entity_id}",
                    "entity_type": entity.entity_type,
                    "entity_id": str(entity.entity_id),
                    "role": entity.role,
                }
                for entity in entities
            ],
            "case_evidence": [
                {
                    "evidence_id": str(item.evidence_id),
                    "evidence_type": item.evidence_type,
                    "severity": item.severity,
                    "entity_type": item.entity_type,
                    "entity_id": str(item.entity_id) if item.entity_id else None,
                    # Database text is retained as data and treated as untrusted by the prompt.
                    "description": item.description,
                    "evidence_data": item.evidence_data,
                }
                for item in evidence
            ],
            "network_risk_record": {
                "available": False,
                "reason": "Network risk records are not linked to a transaction or entity in the current schema.",
            },
        }
        if not trigger_transaction:
            context.update({
                "trigger_transaction": {"available": False, "reason": "No explicit trigger_transaction case entity exists."},
                "transaction_prediction": {"available": False, "reason": "No exact trigger transaction is available."},
                "shap_features": {"available": False, "reason": "No exact trigger transaction is available."},
                "graph_statistics": {"available": False, "reason": "No event-time cutoff is available."},
                "temporal_anomalies": [],
                "timeline": [],
            })
            return context

        event_time = trigger_transaction.occurred_at
        prediction = await risk_repo.get_prediction_for_transaction_at_or_before(
            self.db, trigger_transaction.transaction_id, event_time
        )
        temporal_anomalies, transactions, graph_statistics = await asyncio.gather(
            self._get_temporal_anomalies(entities, event_time),
            self._get_case_transactions(entities, event_time),
            self._get_graph_statistics(entities, event_time),
        )
        context.update({
            "trigger_transaction": {
                "available": True,
                "transaction_id": str(trigger_transaction.transaction_id),
                "customer_id": str(trigger_transaction.customer_id),
                "amount": float(trigger_transaction.amount),
                "currency": trigger_transaction.currency,
                "transaction_type": trigger_transaction.transaction_type,
                "occurred_at": event_time.isoformat(),
            },
            "transaction_prediction": (
                {
                    "available": True,
                    "prediction_id": str(prediction.prediction_id),
                    "risk_score": prediction.risk_score,
                    "risk_tier": prediction.risk_tier,
                    "model_version": prediction.model_version,
                    "predicted_at": prediction.predicted_at.isoformat(),
                }
                if prediction else {
                    "available": False,
                    "reason": "No prediction for the exact trigger transaction exists at or before the event-time cutoff.",
                }
            ),
            "graph_statistics": graph_statistics,
            "temporal_anomalies": [
                {
                    "anomaly_id": str(item.anomaly_id),
                    "entity_type": item.entity_type,
                    "entity_id": str(item.entity_id),
                    "anomaly_type": item.anomaly_type,
                    "baseline_value": item.baseline_value,
                    "observed_value": item.observed_value,
                    "anomaly_score": item.anomaly_score,
                    "window_start": item.window_start.isoformat(),
                    "window_end": item.window_end.isoformat(),
                }
                for item in temporal_anomalies
            ],
            "timeline": [
                {
                    "event_type": "transaction",
                    "timestamp": item.occurred_at.isoformat(),
                    "transaction_id": str(item.transaction_id),
                    "customer_id": str(item.customer_id),
                    "amount": float(item.amount),
                    "currency": item.currency,
                    "transaction_type": item.transaction_type,
                }
                for item in transactions
            ],
        })
        context["shap_features"] = await self._get_shap_features(trigger_transaction, prediction)
        return context

    async def _get_trigger_transaction(self, case_id):
        result = await self.db.execute(
            select(Transaction)
            .join(CaseEntity, CaseEntity.entity_id == Transaction.transaction_id)
            .where(
                CaseEntity.case_id == case_id,
                CaseEntity.entity_type == "transaction",
                CaseEntity.role == "trigger_transaction",
            )
            .order_by(CaseEntity.added_at.asc())
            .limit(1)
        )
        return result.scalars().first()

    async def _get_temporal_anomalies(self, entities, event_time):
        conditions = [
            and_(TemporalAnomaly.entity_type == item.entity_type, TemporalAnomaly.entity_id == item.entity_id)
            for item in entities
        ]
        if not conditions:
            return []
        result = await self.db.execute(
            select(TemporalAnomaly)
            .where(or_(*conditions), TemporalAnomaly.window_end <= event_time)
            .order_by(TemporalAnomaly.window_end.asc(), TemporalAnomaly.detected_at.asc())
        )
        return list(result.scalars().all())

    async def _get_case_transactions(self, entities, event_time):
        transaction_ids = [item.entity_id for item in entities if item.entity_type == "transaction"]
        customer_ids = [item.entity_id for item in entities if item.entity_type == "customer"]
        conditions = []
        if transaction_ids:
            conditions.append(Transaction.transaction_id.in_(transaction_ids))
        if customer_ids:
            conditions.append(Transaction.customer_id.in_(customer_ids))
        if not conditions:
            return []
        result = await self.db.execute(
            select(Transaction)
            .where(or_(*conditions), Transaction.occurred_at <= event_time)
            .order_by(Transaction.occurred_at.asc())
            .limit(100)
        )
        return list(result.scalars().all())

    async def _get_graph_statistics(self, entities, event_time):
        conditions = []
        for item in entities:
            conditions.extend([
                and_(EntityRelationship.source_type == item.entity_type, EntityRelationship.source_id == item.entity_id),
                and_(EntityRelationship.target_type == item.entity_type, EntityRelationship.target_id == item.entity_id),
            ])
        if not conditions:
            return {"available": False, "reason": "No case entities are available."}
        result = await self.db.execute(
            select(EntityRelationship).where(or_(*conditions), EntityRelationship.first_seen_at <= event_time)
        )
        relationships = list(result.scalars().all())
        connected = {
            f"{item.source_type}:{item.source_id}" for item in relationships
        } | {
            f"{item.target_type}:{item.target_id}" for item in relationships
        }
        return {
            "available": True,
            "relationship_count": len(relationships),
            "connected_entity_count": len(connected),
            "relationship_types": sorted({item.relationship_type for item in relationships}),
            "event_time_cutoff": event_time.isoformat(),
        }

    async def _get_shap_features(self, transaction, prediction):
        if prediction is None:
            return {"available": False, "reason": "No event-time-safe prediction is available."}
        model, explainer, feature_names = get_model()
        if model is None or explainer is None:
            return {"available": False, "reason": "The configured model or SHAP explainer is unavailable."}
        try:
            features = await extract_features_for_transaction(transaction, self.db, feature_names)
            shap_values = await asyncio.to_thread(explainer.shap_values, features)
            values = shap_values[0] if getattr(shap_values, "ndim", 0) == 2 else shap_values
            contributions = [
                {"name": str(name), "value": float(features[0, index]), "contribution": float(values[index])}
                for index, name in enumerate(feature_names)
            ]
            contributions.sort(key=lambda item: abs(item["contribution"]), reverse=True)
            return {"available": True, "top_features": contributions[:5]}
        except Exception as exc:
            logger.warning("case_context_shap_unavailable", error=str(exc), transaction_id=str(transaction.transaction_id))
            return {"available": False, "reason": "SHAP calculation was unavailable for this trigger transaction."}
