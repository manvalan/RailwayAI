import os
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer, APIKeyHeader
from python.integration.user_service import UserService
import logging
logger = logging.getLogger(__name__)

# Configurazione (in produzione usare variabili d'ambiente)
SECRET_KEY = os.getenv("RAILWAY_AI_SECRET_KEY", "7b292195a86d4356ab70f04e187eca8e")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 # 24 ore

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token", auto_error=False)
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(
    request: Request,
    token: Optional[str] = Depends(oauth2_scheme),
    api_key: Optional[str] = Depends(api_key_header)
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # DEBUG LOGGING
    logger.info(f"Auth Attempt - Headers: {request.headers}")
    logger.info(f"Auth Attempt - Token: {token is not None}, API Key: {api_key}")

    # Fallback: Check header manually if dependency failed
    if not api_key:
        api_key = request.headers.get("X-API-Key")

    # 1. Verifica API Key (Priorità alta per automazione)
    if api_key:
        user_data = UserService.validate_api_key(api_key)
        if user_data:
            return user_data
        
        logger.warning(f"Invalid API Key provided: {api_key}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid, expired or disabled API Key"
        )

    # 2. Verifica JWT Token
    if token:
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            username: str = payload.get("sub")
            if username is None:
                raise credentials_exception
            
            user = UserService.get_user(username)
            if not user or not user.get('is_active', True):
                raise credentials_exception
            return user
        except JWTError as e:
            logger.warning(f"JWT Validation Error: {e}")
            raise credentials_exception
            
    logger.warning("No credentials provided")
    raise credentials_exception
