from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Float, JSON
from sqlalchemy.sql import func
from app.models.database import Base
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import uuid


class Concept(Base):
    __tablename__ = "concepts"

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    study_guide_id = Column(String, ForeignKey("study_guides.id"), nullable=False)
    document_id = Column(String, ForeignKey("documents.id"), nullable=False)
    term = Column(String, nullable=False)  # The concept term
    definition = Column(Text, nullable=False)  # Definition of the concept
    importance_score = Column(Float, default=0.5)  # 0.0 to 1.0
    category = Column(String, nullable=True)  # Category of the concept (e.g., definition, theory, procedure)
    examples = Column(JSON, nullable=True)  # JSON array of examples
    related_concepts = Column(JSON, nullable=True)  # JSON array of related concept IDs
    page_reference = Column(String, nullable=True)  # Page number reference
    created_at = Column(DateTime, default=func.now())


class ConceptCreate(BaseModel):
    study_guide_id: str
    term: str
    definition: str
    importance_score: float = 0.5
    category: Optional[str] = None
    examples: Optional[List[str]] = None
    related_concepts: Optional[List[str]] = None
    page_reference: Optional[str] = None


class ConceptResponse(BaseModel):
    id: str
    study_guide_id: str
    term: str
    definition: str
    importance_score: float
    category: Optional[str] = None
    examples: Optional[List[str]] = None
    related_concepts: Optional[List[str]] = None
    page_reference: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True