from sqlalchemy.orm import Session
from app.models.source import Source

def list_active_sources(db: Session) -> list[Source]:
    return (
        db.query(Source).filter(Source.is_active == True).all()
    )   