# Location: /src/db/session.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from src.core.config import settings

# Create the SQLAlchemy engine
engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)

# Create a sessionmaker
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create a base class for our models
Base = declarative_base()

def get_db():
    """
    FastAPI dependency to get a database session.
    Yields a session and closes it after the request.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()