from sqlalchemy import Column, Integer, String, DateTime, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime

# 1. The Database Connection String
# For local development, we use SQLite. For production, this becomes a Postgres URL.
DATABASE_URL = "sqlite:///bazi_data.db"

# 2. The Engine and Session
# connect_args is needed for SQLite to work with Streamlit's threading
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 3. The Base Class
Base = declarative_base()

# 4. The Data Model (Your Table)
class Reading(Base):
    __tablename__ = "readings"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    gender = Column(String)
    city = Column(String)
    birth_date = Column(String)
    pillars = Column(String)
    ai_reading = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow)

# 5. Initialize the database tables
Base.metadata.create_all(bind=engine)