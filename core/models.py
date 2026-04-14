from sqlalchemy import Column, Integer, String
from core.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    # We never save raw passwords, only the scrambled hash!
    hashed_password = Column(String, nullable=False)
    name = Column(String, nullable=True)