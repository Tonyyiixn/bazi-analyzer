from datetime import datetime, timedelta
from jose import jwt
from passlib.context import CryptContext

# 1. JWT Configuration
# In a real app, this goes in your .env file! For testing today, we hardcode it.
SECRET_KEY = "super-secret-bazi-key-change-this-later"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # Wristband expires in 7 days

# 2. The Password Hasher
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password: str) -> str:
    """Scrambles a plain text password into a secure hash."""
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Checks if the entered password matches the scrambled hash in the DB."""
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict) -> str:
    """Prints the VIP Wristband (JWT) with an expiration timestamp."""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    
    # This cryptographically signs the token so hackers can't forge it
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt