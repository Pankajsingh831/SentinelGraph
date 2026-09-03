import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.transaction import Transaction

async def get_transaction(db: AsyncSession, transaction_id: uuid.UUID) -> Transaction | None:
    result = await db.execute(select(Transaction).where(Transaction.transaction_id == transaction_id))
    return result.scalars().first()

async def get_customer_transactions(db: AsyncSession, customer_id: uuid.UUID, limit: int = 100) -> list[Transaction]:
    result = await db.execute(
        select(Transaction)
        .where(Transaction.customer_id == customer_id)
        .order_by(Transaction.occurred_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())
