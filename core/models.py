from sqlalchemy import Column, Integer, String, ForeignKey, JSON, DateTime, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base # Or however you import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    name = Column(String)
    hashed_password = Column(String)
    
    # NEW: Link the user to their charts
    saved_charts = relationship("SavedChart", back_populates="owner")
    chat_sessions = relationship("ChatSession", back_populates="owner", cascade="all, delete-orphan")

# NEW TABLE: The Saved Charts
class SavedChart(Base):
    __tablename__ = "saved_charts"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id")) # This links to the user!
    name = Column(String, index=True) # The name of the person the chart is for
    chart_data = Column(JSON) # We can save the whole calculated JSON here
    ai_reading = Column(Text, nullable=True) # Save the Gemini reading
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Link the chart back to the user
    owner = relationship("User", back_populates="saved_charts")


class TimeTestAnswers(Base):
    __tablename__ = "time_test_answers"
    id = Column(Integer, primary_key=True, index=True)
    answers = Column(String)


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    title = Column(String, nullable=True)  # auto-derived from the first message
    skill_id = Column(String, nullable=True)  # last skill used in this session
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    owner = relationship("User", back_populates="chat_sessions")
    messages = relationship(
        "ChatMessage", back_populates="session",
        cascade="all, delete-orphan", order_by="ChatMessage.created_at",
    )


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("chat_sessions.id"))
    role = Column(String)  # "user" or "assistant"
    content = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    session = relationship("ChatSession", back_populates="messages")