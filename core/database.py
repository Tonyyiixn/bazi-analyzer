from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker

# This creates a local file named "bazi_app.db" in your project root
SQLALCHEMY_DATABASE_URL = "sqlite:///./bazi_app.db"

# Check_same_thread=False is needed specifically for SQLite in FastAPI
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Dependency to get the database session in our routes later
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()