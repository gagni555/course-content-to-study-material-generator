from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, JSON
from sqlalchemy.sql import func
from app.models.database import Base
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import uuid


class Question(Base):
    __tablename__ = "questions"

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    study_guide_id = Column(String, ForeignKey("study_guides.id"), nullable=False)
    document_id = Column(String, ForeignKey("documents.id"), nullable=False)
    question_text = Column(Text, nullable=False)
    question_type = Column(String, nullable=False)  # multiple_choice, short_answer, essay, true_false
    correct_answer = Column(Text, nullable=False)
    options = Column(JSON, nullable=True)  # JSON array of options for multiple choice
    explanation = Column(Text, nullable=True)  # Explanation of the answer
    difficulty = Column(String, default="medium")  # easy, medium, hard
    topic = Column(String, nullable=True)  # Associated topic
    bloom_level = Column(String, nullable=True)  # remember, understand, apply, analyze, evaluate, create
    page_reference = Column(String, nullable=True)  # Page number reference
    created_at = Column(DateTime, default=func.now())


class QuestionCreate(BaseModel):
    study_guide_id: str
    question_text: str
    question_type: str
    correct_answer: str
    options: Optional[List[str]] = None
    explanation: Optional[str] = None
    difficulty: str = "medium"
    topic: Optional[str] = None
    bloom_level: Optional[str] = None
    page_reference: Optional[str] = None


class QuestionResponse(BaseModel):
    id: str
    study_guide_id: str
    question_text: str
    question_type: str
    correct_answer: str
    options: Optional[List[str]] = None
    explanation: Optional[str] = None
    difficulty: str
    topic: Optional[str] = None
    bloom_level: Optional[str] = None
    page_reference: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True