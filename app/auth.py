from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status, Depends
from fastapi.security import OAuth2PasswordBearer
from .database import SessionLocal, engine
from . import models, utils

# Secret key for signing the JWT
SECRET_KEY = "your-secret-key"  # Use a strong secret key
ALGORITHM = "HS256"  # Algorithm for encoding the JWT
ACCESS_TOKEN_EXPIRE_MINUTES = 30  # Token validity in minutes

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2PasswordBearer instance (token URL to obtain tokens)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Fake user database for demonstration purposes
fake_users_db = {
    "user@example.com": {
        "email": "user@example.com",
        "full_name": "John Doe",
        "hashed_password": pwd_context.hash("password"),
        "disabled": False,
    }
}


# Utility function to verify password


# Utility function to hash passwords
def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


# Utility function to get a user from the fake database
def get_user(db, email: str, user_type: str):
    user_model_map = {
        "investor": models.Investor,
        "admin": models.Admin,
        "founder": models.Founder
    }
    user_model = user_model_map.get(user_type)
    with SessionLocal() as db:
        result =  db.query(user_model).filter(user_model.email == email).first()
    # print(result.__dict__)
    return result


# Authenticate user and verify credentials
def authenticate_user(email: str, password: str, user_type: str):
    user = get_user(fake_users_db, email, user_type)
    print("Here are the results for user query", user)
    if not user or not utils.verify_password(password, user.password):
        return False
    return user


# Create a JWT access token
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


# Get current user based on the token
async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = get_user(fake_users_db, email)
    if user is None:
        raise credentials_exception
    return user


# Ensure the current user is active
async def get_current_active_user(current_user: dict = Depends(get_current_user)):
    if current_user.get("disabled"):
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user
