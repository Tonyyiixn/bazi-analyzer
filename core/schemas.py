from pydantic import BaseModel
from typing import Optional, Any

class BaziRequest(BaseModel):
    name: str
    gender: str
    city: str
    year: int
    month: int
    day: int
    hour: int
    minute: int

class UserCreate(BaseModel):
    name: str
    email: str
    password: str

class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    
    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

class UserLogin(BaseModel):
    email: str
    password: str

class ChartCreate(BaseModel):
    name: str
    chart_data: dict
    ai_reading: Optional[str] = None