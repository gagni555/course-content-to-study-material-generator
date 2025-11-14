from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Boolean
from sqlalchemy.sql import func
from app.models.database import Base
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid


class StudyGuide(Base):
    __tablename__ = "study_guides"

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    document_id = Column(String, ForeignKey("documents.id"), nullable=False)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    title = Column(String, nullable=False)
    summary = Column(Text, nullable=True)  # Brief summary of the content
    detailed_content = Column(Text, nullable=True)  # Detailed content in JSON format
    generated_at = Column(DateTime, default=func.now())
    detail_level = Column(String, default="standard")  # brief, standard, detailed
    question_count = Column(Integer, default=0)  # Number of questions generated
    concept_count = Column(Integer, default=0)  # Number of concepts extracted
    export_formats = Column(String, nullable=True)  # Available export formats (JSON string)
    is_deleted = Column(Boolean, default=False)  # Soft delete flag
    deleted_at = Column(DateTime, nullable=True)


class StudyGuideCreate(BaseModel):
    document_id: str
    detail_level: str = "standard"  # brief, standard, detailed
    include_questions: bool = True
    include_concept_map: bool = True
    include_flashcards: bool = True


class StudyGuideUpdate(BaseModel):
    title: Optional[str] = None
    detail_level: Optional[str] = None


class StudyGuideResponse(BaseModel):
    id: str
    document_id: str
    user_id: str
    title: str
    summary: Optional[str]
    generated_at: datetime
    detail_level: str
    question_count: int
    concept_count: int
    export_formats: Optional[str]

    class Config:
        from_attributes = True


class SummarySection(BaseModel):
    level: str  # remember, understand, apply, analyze, evaluate, create
    content: str
    examples: List[str] = []


class Question(BaseModel):
    id: str
    question_text: str
    question_type: str  # multiple_choice, short_answer, essay, true_false
    correct_answer: str
    options: Optional[List[str]] = None  # For multiple choice
    difficulty: str  # easy, medium, hard
    topic: str
    page_reference: Optional[str] = None


class Concept(BaseModel):
    term: str
    definition: str
    importance_score: float  # 0.0 to 1.0
    related_concepts: List[str] = []
    examples: List[str] = []
    page_reference: Optional[str] = None


class StudyGuideContent(BaseModel):
    title: str
    summary_sections: List[SummarySection] = []
    questions: List[Question] = []
    concepts: List[Concept] = []
    concept_map: Optional[Dict[str, Any]] = None  # JSON representation of concept map
    flashcards: List[Dict[str, str]] = []  # {front: str, back: str}