from pydantic import BaseModel, Field
from typing import Optional, Any


class ResolvedIdentifier(BaseModel):
    identifier_type: str = Field(..., description="Type of identifier: device, payment_instrument, ip_address, transaction, merchant")
    identifier_value: str = Field(..., description="Value, token, or UUID of the identifier")
    role: str = Field(..., description="Role within the case: primary_suspect, trigger_transaction, associated_device, etc.")
    resolution_method: str = Field(..., description="Method used to resolve: EXACT_EVENT_MATCH, TELEMETRY_LINK, TOKEN_MATCH, etc.")
    status: str = Field(..., description="Status: RESOLVED, SUSPICIOUS_SHARED, UNRESOLVED")
    confidence: float = Field(1.0, description="Confidence score between 0.0 and 1.0 (1.0 for deterministic)")
    details: dict[str, Any] = Field(default_factory=dict, description="Metadata such as device_type, card_type, country, etc.")
    shared_with_customers_count: int = Field(1, description="Number of distinct customers associated with this identifier")


class CanonicalEntity(BaseModel):
    canonical_id: str = Field(..., description="Canonical entity ID (e.g. customer UUID)")
    entity_type: str = Field("customer", description="Canonical entity type")
    country: Optional[str] = Field(None, description="Country code if available")
    status: str = Field("active", description="Account status")
    account_created_at: Optional[str] = Field(None, description="ISO timestamp of account creation")
    total_transactions: int = Field(0, description="Total transactions associated with this canonical entity")
    total_cases: int = Field(1, description="Total risk cases linked to this canonical entity")
    correlated_devices_count: int = Field(0, description="Number of unique devices used")
    correlated_instruments_count: int = Field(0, description="Number of unique payment instruments used")
    correlated_ips_count: int = Field(0, description="Number of unique IP addresses used")


class CorrelatedCase(BaseModel):
    case_id: str = Field(..., description="Case UUID")
    risk_tier: str = Field(..., description="Risk tier: CRITICAL, HIGH, MEDIUM, LOW")
    overall_risk_score: float = Field(..., description="Overall risk score")
    status: str = Field(..., description="Case status: open, escalated, resolved, closed")
    created_at: str = Field(..., description="ISO timestamp of case creation")


class EntityResolutionResponse(BaseModel):
    case_id: str = Field(..., description="Case UUID")
    canonical_entity: CanonicalEntity
    resolved_identifiers: list[ResolvedIdentifier] = Field(default_factory=list)
    correlated_cases: list[CorrelatedCase] = Field(default_factory=list)
    resolution_strategy: str = Field("DETERMINISTIC_GRAPH_LINKING", description="Strategy used for resolution")
    confidence_model: str = Field("RULE_BASED_GROUND_TRUTH", description="Confidence model designation")
    summary: str = Field(..., description="Human-readable summary of resolution findings")
