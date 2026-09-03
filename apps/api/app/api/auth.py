from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from app.database import get_db
from app.models.user import User
from app.services.auth_service import AuthService

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])
auth_service = AuthService()

class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    token: str
    user: dict

@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest, db: AsyncSession = Depends(get_db)):
    query = select(User).where(User.username == request.username)
    result = await db.execute(query)
    user = result.scalar_one_or_none()
    
    if not user or not auth_service.verify_password(request.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password"
        )
        
    token = auth_service.create_token(
        user_id=str(user.user_id),
        username=user.username,
        role=user.role
    )
    
    return LoginResponse(
        token=token,
        user={
            "user_id": str(user.user_id),
            "username": user.username,
            "role": user.role
        }
    )
