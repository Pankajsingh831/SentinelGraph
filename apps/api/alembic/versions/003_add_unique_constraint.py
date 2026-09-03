"""add unique constraint to entity_relationships

Revision ID: 003
Revises: 002
Create Date: 2024-06-01 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '003'
down_revision: Union[str, None] = '002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # First, we need to clear out duplicates if they exist, but we assume the table is empty (0 records).
    op.execute('DELETE FROM entity_relationships;')
    
    op.create_unique_constraint(
        'uq_entity_relationships_source_target',
        'entity_relationships',
        ['source_type', 'source_id', 'relationship_type', 'target_type', 'target_id']
    )

def downgrade() -> None:
    op.drop_constraint('uq_entity_relationships_source_target', 'entity_relationships', type_='unique')
