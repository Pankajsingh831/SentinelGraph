from sqlalchemy.sql import func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base
from datetime import datetime

class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

from app.models.customer import Customer
from app.models.merchant import Merchant
from app.models.device import Device
from app.models.payment_instrument import PaymentInstrument
from app.models.ip_address import IPAddress
from app.models.transaction import Transaction
from app.models.entity_relationship import EntityRelationship
from app.models.risk_feature import RiskFeature
from app.models.risk_prediction import RiskPrediction
from app.models.temporal_anomaly import TemporalAnomaly
from app.models.network_risk import NetworkRisk
from app.models.risk_case import RiskCase
from app.models.case_entity import CaseEntity
from app.models.case_evidence import CaseEvidence
from app.models.analyst_decision import AnalystDecision
from app.models.audit_log import AuditLog
from app.models.model_version import ModelVersion
from app.models.ground_truth import GroundTruth
