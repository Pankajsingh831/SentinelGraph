from fastapi import Depends, HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.config import get_settings
from pydantic import BaseModel
from app.services.auth_service import AuthService

security = HTTPBearer()
auth_service = AuthService()

class User(BaseModel):
    user_id: str
    username: str
    role: str

async def get_current_user(credentials: HTTPAuthorizationCredentials = Security(security)) -> User:
    settings = get_settings()
    if settings.JWT_SECRET == 'development':
        return User(user_id="dev-user-1", username="dev_analyst", role="ANALYST")
        
    payload = auth_service.verify_token(credentials.credentials)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
        
    return User(
        user_id=payload.get("sub"),
        username=payload.get("username"),
        role=payload.get("role")
    )

def require_role(role: str):
    async def role_checker(user: User = Depends(get_current_user)) -> User:
        if user.role != role and user.role != "ADMIN":
            raise HTTPException(status_code=403, detail="Not enough permissions")
        return user
    return role_checker
