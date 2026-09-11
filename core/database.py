import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker

load_dotenv()

# Local dev falls back to the SQLite file; deployed environments set
# DATABASE_URL to a Postgres connection string.
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./bazi_app.db")

if SQLALCHEMY_DATABASE_URL.startswith("sqlite"):
    # Check_same_thread=False is needed specifically for SQLite in FastAPI
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
    )
else:
    # Managed Postgres drops connections that have been idle for a few minutes.
    # pre_ping swaps a dead connection for a fresh one at checkout instead of
    # surfacing the disconnect as a 500 on whichever request drew it, and
    # recycle retires connections before the provider's own idle timeout.
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL, pool_pre_ping=True, pool_recycle=300
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
