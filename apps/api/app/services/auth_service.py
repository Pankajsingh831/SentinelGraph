from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta, timezone
from app.config import get_settings

pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto')

class AuthService:
    def __init__(self):
        self.settings = get_settings()
        self.secret_key = self.settings.JWT_SECRET
        self.algorithm = "HS256"
        self.access_token_expire_minutes = 30
        
    def hash_password(self, password: str) -> str:
        return pwd_context.hash(password)
        
    def verify_password(self, plain: str, hashed: str) -> bool:
        return pwd_context.verify(plain, hashed)
        
    def create_token(self, user_id: str, username: str, role: str) -> str:
        expire = datetime.now(timezone.utc) + timedelta(minutes=self.access_token_expire_minutes)
        to_encode = {
            "sub": str(user_id),
            "username": username,
            "role": role,
            "exp": expire
        }
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt
        
    def verify_token(self, token: str) -> dict:
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except JWTError:
            return None
