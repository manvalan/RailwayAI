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
    
    # --- RIGOROUS KEY EXTRACTION ---
    final_key = None
    
    # 1. Check X-API-Key (Dependency or Header)
    if api_key:
        final_key = api_key
    else:
        final_key = request.headers.get("X-API-Key")
        
    # 2. Check Authorization Header (Bearer or Simple)
    if not final_key:
        auth_header = request.headers.get("Authorization")
        if auth_header:
            if auth_header.lower().startswith("bearer "):
                final_key = auth_header[7:].strip()
            else:
                final_key = auth_header.strip()
    
    # 3. Use token from oauth2_scheme as last resort
    if not final_key and token:
        final_key = token
        
    # Record activity to stay synchronized with idle manager
    # EXCLUSION: Don't count background polling/monitoring as "activity" 
    # otherwise training will be killed by the dashboard just for being open.
    ignore_paths = ["/api/v1/ai/status", "/api/v1/metrics", "/api/v1/ai/scenarios", "/api/v1/ai/backups", "/api/v1/users/me", "/api/v1/network/topology"]
    if request.method != "GET" or request.url.path not in ignore_paths:
        from python.integration.idle_training import idle_manager
        idle_manager.record_activity(f"API: {request.method} {request.url.path}")

    # DEBUG LOGGING (Sanitized)
    if final_key:
        prefix = final_key[:8] if len(final_key) > 8 else "too_short"
        logger.info(f"Auth Attempt [{request.method} {request.url.path}] - Key found: {prefix}...")
    else:
        logger.warning(f"Auth Attempt [{request.method} {request.url.path}] - NO CREDENTIALS FOUND")
        logger.debug(f"Headers received: {dict(request.headers)}")
        raise credentials_exception

    # --- VALIDATION ---
    
    # 1. Try as API Key (most common for automation/scaling)
    # Check both with and without prefix if necessary
    user_data = UserService.validate_api_key(final_key)
    if not user_data and not final_key.startswith("rw-"):
        # Try prepending prefix just in case client omitted it
        user_data = UserService.validate_api_key(f"rw-{final_key}")
        
    if user_data:
        return user_data

    # 2. Try as JWT (if it doesn't look like our API key)
    if not final_key.startswith("rw-") and final_key.startswith("eyJ"):
        try:
            payload = jwt.decode(final_key, SECRET_KEY, algorithms=[ALGORITHM])
            username: str = payload.get("sub")
            if username:
                user = UserService.get_user(username)
                if user and user.get('is_active', True):
                    return user
                logger.warning(f"JWT valid but user '{username}' not found or inactive")
        except JWTError as e:
            logger.warning(f"JWT Validation Error for prefix {final_key[:12]}: {e}")
            # Se è un JWT palesemente rotto/scaduto, non provare altre strade
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid or expired session: {str(e)}",
                headers={"WWW-Authenticate": "Bearer"},
            )

    logger.warning(f"Auth failed for key prefix: {final_key[:8]}...")
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Invalid, expired or disabled credentials"
    )
