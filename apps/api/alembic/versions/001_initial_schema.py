"""initial schema - full SentinelGraph database

Revision ID: 001
Revises:
Create Date: 2024-01-01 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. customers
    op.create_table(
        'customers',
        sa.Column('customer_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('country', sa.CHAR(2), nullable=True),
        sa.Column('status', sa.VARCHAR(32), nullable=False, server_default='active'),
        sa.Column('account_created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('customer_id'),
    )

    # 2. merchants
    op.create_table(
        'merchants',
        sa.Column('merchant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('merchant_name', sa.Text(), nullable=False),
        sa.Column('category', sa.VARCHAR(64), nullable=True),
        sa.Column('country', sa.CHAR(2), nullable=True),
        sa.Column('status', sa.VARCHAR(32), nullable=False, server_default='active'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('merchant_id'),
    )

    # 3. devices
    op.create_table(
        'devices',
        sa.Column('device_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('device_type', sa.VARCHAR(32), nullable=True),
        sa.Column('first_seen_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('last_seen_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('device_id'),
    )

    # 4. payment_instruments
    op.create_table(
        'payment_instruments',
        sa.Column('instrument_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('instrument_type', sa.VARCHAR(32), nullable=False),
        sa.Column('issuer_country', sa.CHAR(2), nullable=True),
        sa.Column('first_seen_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('last_seen_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('instrument_id'),
    )

    # 5. ip_addresses
    op.create_table(
        'ip_addresses',
        sa.Column('ip_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('ip_hash', sa.Text(), nullable=False, unique=True),
        sa.Column('country', sa.CHAR(2), nullable=True),
        sa.Column('first_seen_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('last_seen_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('ip_id'),
    )

    # 6. transactions
    op.create_table(
        'transactions',
        sa.Column('transaction_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('customer_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('merchant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('device_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('instrument_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('ip_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('amount', sa.NUMERIC(18, 2), nullable=False),
        sa.Column('currency', sa.CHAR(3), nullable=False),
        sa.Column('transaction_type', sa.VARCHAR(32), nullable=False),
        sa.Column('status', sa.VARCHAR(32), nullable=False),
        sa.Column('occurred_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['customer_id'], ['customers.customer_id']),
        sa.ForeignKeyConstraint(['merchant_id'], ['merchants.merchant_id']),
        sa.ForeignKeyConstraint(['device_id'], ['devices.device_id']),
        sa.ForeignKeyConstraint(['instrument_id'], ['payment_instruments.instrument_id']),
        sa.ForeignKeyConstraint(['ip_id'], ['ip_addresses.ip_id']),
        sa.PrimaryKeyConstraint('transaction_id'),
    )
    op.create_index('idx_transactions_customer', 'transactions', ['customer_id'])
    op.create_index('idx_transactions_device', 'transactions', ['device_id'])
    op.create_index('idx_transactions_instrument', 'transactions', ['instrument_id'])
    op.create_index('idx_transactions_ip', 'transactions', ['ip_id'])
    op.create_index('idx_transactions_occurred_at', 'transactions', ['occurred_at'])
    op.create_index('idx_transactions_merchant_time', 'transactions', ['merchant_id', 'occurred_at'])

    # 7. entity_relationships
    op.create_table(
        'entity_relationships',
        sa.Column('relationship_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('source_type', sa.VARCHAR(32), nullable=False),
        sa.Column('source_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('relationship_type', sa.VARCHAR(64), nullable=False),
        sa.Column('target_type', sa.VARCHAR(32), nullable=False),
        sa.Column('target_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('first_seen_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('last_seen_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('interaction_count', sa.BigInteger(), nullable=False, server_default='1'),
        sa.PrimaryKeyConstraint('relationship_id'),
    )
    op.create_index('idx_relationship_source', 'entity_relationships', ['source_type', 'source_id'])
    op.create_index('idx_relationship_target', 'entity_relationships', ['target_type', 'target_id'])

    # 8. risk_features
    op.create_table(
        'risk_features',
        sa.Column('feature_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('entity_type', sa.VARCHAR(32), nullable=False),
        sa.Column('entity_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('transaction_count_5m', sa.Integer(), nullable=True),
        sa.Column('transaction_count_1h', sa.Integer(), nullable=True),
        sa.Column('transaction_count_24h', sa.Integer(), nullable=True),
        sa.Column('avg_transaction_amount', sa.NUMERIC(18, 2), nullable=True),
        sa.Column('refund_rate', sa.DOUBLE_PRECISION(), nullable=True),
        sa.Column('account_age_hours', sa.DOUBLE_PRECISION(), nullable=True),
        sa.Column('device_account_count', sa.Integer(), nullable=True),
        sa.Column('ip_account_count', sa.Integer(), nullable=True),
        sa.Column('merchant_connection_count', sa.Integer(), nullable=True),
        sa.Column('network_size', sa.Integer(), nullable=True),
        sa.Column('network_density', sa.DOUBLE_PRECISION(), nullable=True),
        sa.Column('network_growth_rate', sa.DOUBLE_PRECISION(), nullable=True),
        sa.Column('calculated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('feature_id'),
    )

    # 9. risk_predictions
    op.create_table(
        'risk_predictions',
        sa.Column('prediction_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('transaction_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('model_version', sa.VARCHAR(64), nullable=False),
        sa.Column('risk_score', sa.DOUBLE_PRECISION(), nullable=False),
        sa.Column('risk_tier', sa.VARCHAR(16), nullable=False),
        sa.Column('prediction_latency_ms', sa.Integer(), nullable=True),
        sa.Column('predicted_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['transaction_id'], ['transactions.transaction_id']),
        sa.PrimaryKeyConstraint('prediction_id'),
    )
    op.create_index('idx_risk_predictions_entity', 'risk_predictions', ['transaction_id'])

    # 10. temporal_anomalies
    op.create_table(
        'temporal_anomalies',
        sa.Column('anomaly_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('entity_type', sa.VARCHAR(32), nullable=False),
        sa.Column('entity_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('anomaly_type', sa.VARCHAR(64), nullable=False),
        sa.Column('baseline_value', sa.DOUBLE_PRECISION(), nullable=True),
        sa.Column('observed_value', sa.DOUBLE_PRECISION(), nullable=True),
        sa.Column('anomaly_score', sa.DOUBLE_PRECISION(), nullable=False),
        sa.Column('window_start', sa.DateTime(timezone=True), nullable=False),
        sa.Column('window_end', sa.DateTime(timezone=True), nullable=False),
        sa.Column('detected_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('anomaly_id'),
    )

    # 11. network_risks
    op.create_table(
        'network_risks',
        sa.Column('network_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('node_count', sa.Integer(), nullable=False),
        sa.Column('edge_count', sa.Integer(), nullable=False),
        sa.Column('network_density', sa.DOUBLE_PRECISION(), nullable=True),
        sa.Column('community_id', sa.VARCHAR(128), nullable=True),
        sa.Column('graph_risk_score', sa.DOUBLE_PRECISION(), nullable=False),
        sa.Column('detected_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('network_id'),
    )

    # 12. risk_cases
    op.create_table(
        'risk_cases',
        sa.Column('case_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('primary_entity_type', sa.VARCHAR(32), nullable=False),
        sa.Column('primary_entity_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('transaction_risk_score', sa.DOUBLE_PRECISION(), nullable=False),
        sa.Column('network_risk_score', sa.DOUBLE_PRECISION(), nullable=False),
        sa.Column('temporal_risk_score', sa.DOUBLE_PRECISION(), nullable=False),
        sa.Column('overall_risk_score', sa.DOUBLE_PRECISION(), nullable=False),
        sa.Column('risk_tier', sa.VARCHAR(16), nullable=False),
        sa.Column('status', sa.VARCHAR(32), nullable=False, server_default='open'),
        sa.Column('case_reason', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('case_id'),
    )
    op.create_index('idx_cases_status', 'risk_cases', ['status'])
    op.create_index('idx_cases_tier', 'risk_cases', ['risk_tier'])

    # 13. case_entities
    op.create_table(
        'case_entities',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('case_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('entity_type', sa.VARCHAR(32), nullable=False),
        sa.Column('entity_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('role', sa.VARCHAR(50), nullable=True),
        sa.Column('added_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['case_id'], ['risk_cases.case_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )

    # 14. case_evidence
    op.create_table(
        'case_evidence',
        sa.Column('evidence_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('case_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('evidence_type', sa.VARCHAR(64), nullable=False),
        sa.Column('entity_type', sa.VARCHAR(32), nullable=True),
        sa.Column('entity_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('severity', sa.VARCHAR(16), nullable=False),
        sa.Column('evidence_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['case_id'], ['risk_cases.case_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('evidence_id'),
    )

    # 15. analyst_decisions
    op.create_table(
        'analyst_decisions',
        sa.Column('decision_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('case_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('analyst_id', sa.VARCHAR(128), nullable=False),
        sa.Column('decision', sa.VARCHAR(32), nullable=False),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['case_id'], ['risk_cases.case_id']),
        sa.PrimaryKeyConstraint('decision_id'),
    )

    # 16. audit_logs
    op.create_table(
        'audit_logs',
        sa.Column('audit_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('actor_type', sa.VARCHAR(32), nullable=False),
        sa.Column('actor_id', sa.VARCHAR(128), nullable=True),
        sa.Column('action', sa.VARCHAR(64), nullable=False),
        sa.Column('resource_type', sa.VARCHAR(64), nullable=False),
        sa.Column('resource_id', sa.VARCHAR(128), nullable=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('audit_id'),
    )

    # 17. model_versions
    op.create_table(
        'model_versions',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('model_name', sa.VARCHAR(100), nullable=False),
        sa.Column('version', sa.VARCHAR(50), nullable=False),
        sa.Column('model_type', sa.VARCHAR(50), nullable=True),
        sa.Column('training_dataset', sa.VARCHAR(255), nullable=True),
        sa.Column('precision_score', sa.NUMERIC(8, 6), nullable=True),
        sa.Column('recall_score', sa.NUMERIC(8, 6), nullable=True),
        sa.Column('f1_score', sa.NUMERIC(8, 6), nullable=True),
        sa.Column('pr_auc', sa.NUMERIC(8, 6), nullable=True),
        sa.Column('threshold', sa.NUMERIC(8, 6), nullable=True),
        sa.Column('artifact_uri', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )

    # 18. ground_truth
    op.create_table(
        'ground_truth',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('entity_type', sa.VARCHAR(50), nullable=False),
        sa.Column('entity_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('scenario_id', sa.VARCHAR(128), nullable=True),
        sa.Column('is_abuse', sa.Boolean(), nullable=False),
        sa.Column('abuse_type', sa.VARCHAR(100), nullable=True),
        sa.Column('injected_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade() -> None:
    op.drop_table('ground_truth')
    op.drop_table('model_versions')
    op.drop_table('audit_logs')
    op.drop_table('analyst_decisions')
    op.drop_table('case_evidence')
    op.drop_table('case_entities')
    op.drop_table('risk_cases')
    op.drop_table('network_risks')
    op.drop_table('temporal_anomalies')
    op.drop_table('risk_predictions')
    op.drop_table('risk_features')
    op.drop_table('entity_relationships')
    op.drop_table('transactions')
    op.drop_table('ip_addresses')
    op.drop_table('payment_instruments')
    op.drop_table('devices')
    op.drop_table('merchants')
    op.drop_table('customers')
