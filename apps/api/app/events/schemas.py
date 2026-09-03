import uuid
from datetime import datetime
from pydantic import BaseModel, Field

class PaymentEvent(BaseModel):
    """Published when a transaction is scored."""
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    transaction_id: uuid.UUID
    customer_id: uuid.UUID
    merchant_id: uuid.UUID
    device_id: uuid.UUID | None = None
    instrument_id: uuid.UUID | None = None
    ip_id: uuid.UUID | None = None
    amount: float
    currency: str
    transaction_type: str
    occurred_at: datetime
    risk_score: float | None = None
    risk_tier: str | None = None

class GraphUpdate(BaseModel):
    """Published when graph worker finishes processing."""
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    entity_type: str
    entity_id: uuid.UUID
    network_id: str | None = None
    node_count: int = 0
    edge_count: int = 0
    network_density: float = 0.0
    graph_risk_score: float = 0.0
    updated_at: datetime

class TemporalUpdate(BaseModel):
    """Published when temporal worker detects anomalies."""
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    entity_type: str
    entity_id: uuid.UUID
    anomaly_count: int = 0
    max_anomaly_score: float = 0.0
    detected_at: datetime
