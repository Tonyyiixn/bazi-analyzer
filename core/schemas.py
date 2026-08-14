from pydantic import BaseModel
from typing import Optional, Any
from datetime import datetime

class BaziRequest(BaseModel):
    name: str
    gender: str
    city: str
    year: int
    month: int
    day: int
    hour: int
    minute: int
    skip_true_solar_time: bool = False

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

class PillarsRequest(BaseModel):
    """Just a natal chart's pillars - used by endpoints that derive live,
    time-dependent facts (e.g. current Liu Nian/Liu Yue) from an already-
    computed chart without recalculating the whole thing."""
    pillars: dict[str, str]

class ChartCreate(BaseModel):
    name: str
    chart_data: dict
    ai_reading: Optional[str] = None

class TimeTestAnswers(BaseModel):
    answers: str

class ChatRequest(BaseModel):
    """Send one new message. Omit session_id to start a new session -
    the server loads/persists history, the client no longer resends it."""
    message: str
    session_id: Optional[int] = None
    skill_id: Optional[str] = None

class ChatMessageOut(BaseModel):
    id: int
    role: str
    content: str
    created_at: datetime

    class Config:
        from_attributes = True

class ChatSessionOut(BaseModel):
    id: int
    title: Optional[str] = None
    skill_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class ChatSessionDetailOut(ChatSessionOut):
    messages: list[ChatMessageOut] = []