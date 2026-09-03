"""add users table

Revision ID: 002
Revises: 001
Create Date: 2024-05-15 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
import uuid

# revision identifiers, used by Alembic.
revision: str = '002'
down_revision: Union[str, None] = '001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    users_table = op.create_table('users',
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('username', sa.String(length=128), nullable=False),
        sa.Column('hashed_password', sa.String(length=255), nullable=False),
        sa.Column('role', sa.String(length=32), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('user_id'),
        sa.UniqueConstraint('username')
    )
    
    # Insert default users
    # analyst123: $2b$12$Nq9T.Yw94K.gM/.c8W4uOOGi2V5O75iYQ0/k/j28.J3vN7Ww7WbW2
    # admin123: $2b$12$R.vCgE55hR2C/aX1/V4Ppe7iF9v9u9Bv9U5x3vPZ5Z5Z5Z5Z5Z5Z5
    from passlib.context import CryptContext
    pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto')
    
    op.bulk_insert(users_table,
        [
            {
                'user_id': uuid.uuid4(),
                'username': 'analyst',
                'hashed_password': pwd_context.hash('analyst123'),
                'role': 'ANALYST'
            },
            {
                'user_id': uuid.uuid4(),
                'username': 'admin',
                'hashed_password': pwd_context.hash('admin123'),
                'role': 'ADMIN'
            }
        ]
    )

def downgrade() -> None:
    op.drop_table('users')
