from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Boolean
from sqlalchemy.sql import func
from app.models.database import Base
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import uuid


class Document(Base):
    __tablename__ = "documents"

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    filename = Column(String, nullable=False)
    original_filename = Column(String, nullable=False)
    file_path = Column(String, nullable=False)  # Path to stored file
    file_size = Column(Integer, nullable=False)  # Size in bytes
    file_type = Column(String, nullable=False)  # MIME type
    upload_date = Column(DateTime, default=func.now())
    processing_status = Column(String, default="uploaded")  # uploaded, processing, completed, failed
    processing_started_at = Column(DateTime, nullable=True)
    processing_completed_at = Column(DateTime, nullable=True)
    pages_count = Column(Integer, nullable=True)  # Number of pages in document
    word_count = Column(Integer, nullable=True)  # Estimated word count
    metadata = Column(Text, nullable=True)  # JSON string of extracted metadata
    course_name = Column(String, nullable=True)  # Optional course name
    topic = Column(String, nullable=True)  # Optional topic
    difficulty_level = Column(String, nullable=True)  # beginner, intermediate, advanced
    exam_date = Column(DateTime, nullable=True)  # Optional exam date
    is_deleted = Column(Boolean, default=False)  # Soft delete flag
    deleted_at = Column(DateTime, nullable=True)


class DocumentCreate(BaseModel):
    original_filename: str
    file_type: str
    course_name: Optional[str] = None
    topic: Optional[str] = None
    difficulty_level: Optional[str] = None
    exam_date: Optional[datetime] = None


class DocumentUpdate(BaseModel):
    course_name: Optional[str] = None
    topic: Optional[str] = None
    difficulty_level: Optional[str] = None
    exam_date: Optional[datetime] = None


class DocumentResponse(BaseModel):
    id: str
    user_id: str
    filename: str
    original_filename: str
    file_size: int
    file_type: str
    upload_date: datetime
    processing_status: str
    processing_started_at: Optional[datetime] = None
    processing_completed_at: Optional[datetime] = None
    pages_count: Optional[int] = None
    word_count: Optional[int] = None
    course_name: Optional[str] = None
    topic: Optional[str] = None
    difficulty_level: Optional[str] = None
    exam_date: Optional[datetime] = None

    class Config:
        from_attributes = True