from sqlalchemy import Column, Integer, String, ForeignKey, JSON, DateTime, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base # Or however you import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    
    # NEW: Link the user to their charts
    saved_charts = relationship("SavedChart", back_populates="owner")

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