from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
import uuid
from app.database import get_db
from app.schemas.transaction import TransactionResponse
from app.repositories import transaction_repo

router = APIRouter(prefix="/api/v1/transactions", tags=["transactions"])

@router.get("/{transaction_id}", response_model=TransactionResponse)
async def get_transaction(transaction_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    transaction = await transaction_repo.get_transaction(db, transaction_id)
    if not transaction:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")
    return transaction
