import uuid
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import desc
from sqlalchemy.future import select
from app.models.risk_prediction import RiskPrediction

async def create_prediction(db: AsyncSession, prediction_data: dict) -> RiskPrediction:
    prediction = RiskPrediction(**prediction_data)
    db.add(prediction)
    await db.commit()
    await db.refresh(prediction)
    return prediction

async def get_prediction(db: AsyncSession, prediction_id: uuid.UUID) -> RiskPrediction | None:
    result = await db.execute(select(RiskPrediction).where(RiskPrediction.prediction_id == prediction_id))
    return result.scalars().first()

async def get_prediction_by_transaction(db: AsyncSession, transaction_id: uuid.UUID) -> RiskPrediction | None:
    result = await db.execute(select(RiskPrediction).where(RiskPrediction.transaction_id == transaction_id))
    return result.scalars().first()


async def get_prediction_for_transaction_at_or_before(
    db: AsyncSession,
    transaction_id: uuid.UUID,
    event_time: datetime,
) -> RiskPrediction | None:
    """Return only the latest prediction that existed at the event-time cutoff.

    This is intentionally separate from ``get_prediction_by_transaction``. The
    latter has no ordering or time constraint and must not be used to rebuild
    historical case context.
    """
    result = await db.execute(
        select(RiskPrediction)
        .where(
            RiskPrediction.transaction_id == transaction_id,
            RiskPrediction.predicted_at <= event_time,
        )
        .order_by(desc(RiskPrediction.predicted_at))
        .limit(1)
    )
    return result.scalars().first()
