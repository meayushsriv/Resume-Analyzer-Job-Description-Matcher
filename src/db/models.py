# Location: /src/db/models.py
import uuid
from sqlalchemy import Column, String, Integer, TIMESTAMP, Text, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from src.db.session import Base

class Resume(Base):
    """
    Database model for the 'resumes' table.
    """
    __tablename__ = "resumes"

    # Columns based on the hackathon spec
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    file_name = Column(String(255), nullable=False)
    file_size = Column(Integer, nullable=False)
    file_type = Column(String(255), nullable=False)
    file_hash = Column(String(128), unique=True, nullable=False)
    file_path = Column(String(512), nullable=True)
    
    uploaded_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    processed_at = Column(TIMESTAMP(timezone=True), nullable=True)
    
    processing_status = Column(String(50), default='pending') # e.g., pending, processing, completed, failed
    
    raw_text = Column(Text, nullable=True)
    structured_data = Column(JSON, nullable=True)
    ai_enhancements = Column(JSON, nullable=True)
    
    # We can add a 'metadata' JSONB column if needed later
    # metadata = Column(JSON, nullable=True)

    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())