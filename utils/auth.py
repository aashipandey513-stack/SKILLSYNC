# SkillSync/utils/auth.py

import bcrypt
from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import jwt
import os

# --- NEW: Load JWT settings from secrets ---
JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7 # 7 days

if not JWT_SECRET_KEY:
    print("CRITICAL: JWT_SECRET_KEY secret is not set. Auth will fail.")

# --- Existing Password Functions ---

def hash_password(password: str) -> str:
    """Hashes a password using bcrypt."""
    pwd_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(pwd_bytes, salt)
    return hashed_password.decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plain password against a hashed one."""
    plain_pwd_bytes = plain_password.encode('utf-8')
    hashed_pwd_bytes = hashed_password.encode('utf-8')
    return bcrypt.checkpw(plain_pwd_bytes, hashed_pwd_bytes)

# --- NEW: JWT Token Creation ---

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Creates a new JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    
    if not JWT_SECRET_KEY:
        raise ValueError("JWT_SECRET_KEY is not set")
        
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt