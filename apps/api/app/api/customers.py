from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
import uuid
from sqlalchemy.future import select
from app.database import get_db
from app.schemas.customer import CustomerResponse
from app.models.customer import Customer

router = APIRouter(prefix="/api/v1/customers", tags=["customers"])

@router.get("/{customer_id}", response_model=CustomerResponse)
async def get_customer(customer_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Customer).where(Customer.customer_id == customer_id))
    customer = result.scalars().first()
    if not customer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")
    return customer
