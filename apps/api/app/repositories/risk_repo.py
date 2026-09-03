import uuid
from sqlalchemy.ext.asyncio import AsyncSession
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
