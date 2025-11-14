from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime


class DocumentUploadResponse(BaseModel):
    job_id: str
    status: str
    message: str
    document_id: Optional[str] = None


class DocumentStatusResponse(BaseModel):
    job_id: str
    status: str
    progress: int
    message: str
    study_guide_id: Optional[str] = None


class DocumentProcessingResult(BaseModel):
    document_id: str
    title: str
    summary: str
    concepts: List[Dict[str, Any]]
    questions: List[Dict[str, Any]]
    concept_map: Optional[Dict[str, Any]] = None
    flashcards: List[Dict[str, str]]


class NormalizedDocument(BaseModel):
    document_id: str
    metadata: Dict[str, Any]
    sections: List[Dict[str, Any]]  # Each section has type, level, content, position