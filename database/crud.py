from sqlalchemy.orm import Session
from database.models import Reading

def create_reading(db: Session, name: str, gender: str, city: str, birth_date: str, pillars: str, ai_reading: str):
    """Saves a new reading to the database."""
    new_reading = Reading(
        name=name,
        gender=gender,
        city=city,
        birth_date=birth_date,
        pillars=pillars,
        ai_reading=ai_reading
    )
    db.add(new_reading)
    db.commit()
    db.refresh(new_reading)
    return new_reading

def get_recent_readings(db: Session, limit: int = 50):
    """Fetches the most recent readings, sorted by newest first."""
    return db.query(Reading).order_by(Reading.id.desc()).limit(limit).all()