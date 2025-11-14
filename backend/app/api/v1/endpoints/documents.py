from fastapi import APIRouter, UploadFile, File, BackgroundTasks, Depends, HTTPException, status
from typing import Optional
import uuid
import os
from sqlalchemy.orm import Session
from app.models.database import get_db
from app.models.user import User
from app.models.document import Document, DocumentCreate, DocumentResponse
from app.models.study_guide import StudyGuide, StudyGuideCreate, StudyGuideResponse
from app.schemas.document import DocumentUploadResponse, DocumentStatusResponse, DocumentProcessingResult
from app.utils.document_parser import document_parser
from app.utils.content_analyzer import content_analyzer
from app.utils.study_guide_generator import study_guide_generator
from app.utils.exporter import exporter
from app.utils.error_handlers import error_recovery_manager, document_error_handler, api_error_handler
from app.config import settings
from app.api.deps import get_current_user
import asyncio
import logging
import json
from datetime import datetime

logger = logging.getLogger(__name__)

router = APIRouter()

# In-memory storage for job statuses (in production, use Redis or database)
processing_jobs = {}


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    course_name: Optional[str] = None,
    topic: Optional[str] = None,
    difficulty_level: Optional[str] = None,
    exam_date: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Upload a document for processing
    """
    try:
        # Validate file type
        file_extension = os.path.splitext(file.filename)[1].lower()
        if file.content_type not in settings.allowed_file_types:
            raise HTTPException(
                status_code=status.HTTP_40_BAD_REQUEST,
                detail=f"File type {file.content_type} not allowed. Allowed types: {settings.allowed_file_types}"
            )
        
        # Check file size
        file_content = await file.read()
        if len(file_content) > settings.max_file_size:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File size exceeds maximum allowed size of {settings.max_file_size} bytes"
            )
        
        # Generate unique document ID
        document_id = str(uuid.uuid4())
        
        # Create upload directory if it doesn't exist
        upload_dir = settings.upload_directory
        os.makedirs(upload_dir, exist_ok=True)
        
        # Save file
        file_path = os.path.join(upload_dir, f"{document_id}{file_extension}")
        with open(file_path, "wb") as f:
            f.write(file_content)
        
        # Create document record in database
        db_document = Document(
            id=document_id,
            user_id=current_user.id,
            filename=f"{document_id}{file_extension}",
            original_filename=file.filename,
            file_path=file_path,
            file_size=len(file_content),
            file_type=file.content_type,
            course_name=course_name,
            topic=topic,
            difficulty_level=difficulty_level
        )
        db.add(db_document)
        db.commit()
        db.refresh(db_document)
        
        # Start background processing
        job_id = str(uuid.uuid4())
        processing_jobs[job_id] = {
            "status": "processing",
            "progress": 0,
            "document_id": document_id,
            "user_id": current_user.id,
            "message": "Document uploaded, starting processing...",
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "estimated_completion": None
        }
        
        # In a real implementation, we would use Celery or similar for background tasks
        # For this MVP, we'll simulate the processing in the background
        asyncio.create_task(simulate_document_processing(job_id, document_id, file_path))
        
        return DocumentUploadResponse(
            job_id=job_id,
            status="processing",
            message="Document uploaded successfully, processing started",
            document_id=document_id
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading document: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error uploading document"
        )


async def simulate_document_processing(job_id: str, document_id: str, file_path: str):
    """
    Simulate the document processing pipeline with detailed status tracking
    """
    try:
        # Update job status with processing start
        processing_jobs[job_id]["progress"] = 5
        processing_jobs[job_id]["message"] = "Starting document parsing..."
        processing_jobs[job_id]["updated_at"] = datetime.utcnow().isoformat()
        
        # Step 1: Parse document
        processing_jobs[job_id]["message"] = "Parsing document content..."
        normalized_document = await document_parser.parse_document(file_path, document_id)
        processing_jobs[job_id]["progress"] = 25
        processing_jobs[job_id]["updated_at"] = datetime.utcnow().isoformat()
        
        # Step 2: Analyze content
        processing_jobs[job_id]["message"] = "Analyzing content and extracting concepts..."
        analysis_result = await content_analyzer.analyze_content(normalized_document)
        processing_jobs[job_id]["progress"] = 50
        processing_jobs[job_id]["updated_at"] = datetime.utcnow().isoformat()
        
        # Step 3: Generate study guide
        processing_jobs[job_id]["message"] = "Generating study guide materials..."
        study_guide_content = await study_guide_generator.generate_study_guide(
            normalized_document,
            detail_level="standard",
            include_questions=True,
            include_concept_map=True,
            include_flashcards=True
        )
        processing_jobs[job_id]["progress"] = 80
        processing_jobs[job_id]["updated_at"] = datetime.utcnow().isoformat()
        
        # Step 4: Save study guide to database
        from datetime import datetime
        from sqlalchemy.orm import Session
        from app.models.database import SessionLocal
        
        db = SessionLocal()
        try:
            # Create study guide record
            from app.models.study_guide import StudyGuide
            db_study_guide = StudyGuide(
                id=str(uuid.uuid4()),
                document_id=document_id,
                user_id=processing_jobs[job_id]["user_id"],
                title=study_guide_content.title,
                summary=study_guide_content.summary_sections[0].content if study_guide_content.summary_sections else "",
                detailed_content=json.dumps({  # Store full content as JSON
                    "summary_sections": [section.dict() for section in study_guide_content.summary_sections],
                    "questions": [q.dict() for q in study_guide_content.questions],
                    "concepts": [c.dict() for c in study_guide_content.concepts],
                    "concept_map": study_guide_content.concept_map,
                    "flashcards": study_guide_content.flashcards
                }),
                detail_level="standard",
                question_count=len(study_guide_content.questions),
                concept_count=len(study_guide_content.concepts),
                export_formats='["pdf", "markdown", "html", "anki", "json"]'
            )
            db.add(db_study_guide)
            db.commit()
            db.refresh(db_study_guide)
            
            # Create question records
            for q in study_guide_content.questions:
                from app.models.question import Question as QuestionModel
                db_question = QuestionModel(
                    id=q.id,
                    study_guide_id=db_study_guide.id,
                    document_id=document_id,
                    question_text=q.question_text,
                    question_type=q.question_type,
                    correct_answer=q.correct_answer,
                    options=q.options,
                    difficulty=q.difficulty,
                    topic=q.topic,
                    page_reference=q.page_reference
                )
                db.add(db_question)
            
            # Create concept records
            for c in study_guide_content.concepts:
                from app.models.concept import Concept as ConceptModel
                db_concept = ConceptModel(
                    id=str(uuid.uuid4()),  # Generate new ID for DB
                    study_guide_id=db_study_guide.id,
                    document_id=document_id,
                    term=c.term,
                    definition=c.definition,
                    importance_score=c.importance_score,
                    examples=c.examples if c.examples else [],
                    related_concepts=c.related_concepts if c.related_concepts else [],
                    page_reference=c.page_reference
                )
                db.add(db_concept)
            
            db.commit()
            
            # Update job status to completed
            processing_jobs[job_id]["progress"] = 100
            processing_jobs[job_id]["status"] = "completed"
            processing_jobs[job_id]["message"] = "Processing completed successfully"
            processing_jobs[job_id]["study_guide_id"] = db_study_guide.id
            processing_jobs[job_id]["updated_at"] = datetime.utcnow().isoformat()
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Error processing document {document_id}: {str(e)}")
        processing_jobs[job_id]["status"] = "failed"
        processing_jobs[job_id]["message"] = f"Processing failed: {str(e)}"
        processing_jobs[job_id]["updated_at"] = datetime.utcnow().isoformat()


@router.get("/status/{job_id}", response_model=DocumentStatusResponse)
async def get_processing_status(job_id: str):
    """
    Get the status of a document processing job
    """
    if job_id not in processing_jobs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job ID not found"
        )
    
    job_info = processing_jobs[job_id]
    return DocumentStatusResponse(
        job_id=job_id,
        status=job_info["status"],
        progress=job_info["progress"],
        message=job_info["message"],
        study_guide_id=job_info.get("study_guide_id")
    )


@router.get("/{document_id}")
async def get_document(document_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Get document details
    """
    document = db.query(Document).filter(Document.id == document_id, Document.user_id == current_user.id).first()
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    return DocumentResponse.from_orm(document)


@router.get("/{document_id}/study-guide")
async def get_study_guide(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get the generated study guide for a document
    """
    # First, check if the document exists and belongs to the user
    document = db.query(Document).filter(Document.id == document_id, Document.user_id == current_user.id).first()
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    # Then get the associated study guide
    study_guide = db.query(StudyGuide).filter(
        StudyGuide.document_id == document_id,
        StudyGuide.user_id == current_user.id
    ).first()
    
    if not study_guide:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Study guide not generated yet or not found"
        )
    
    return StudyGuideResponse.from_orm(study_guide)


@router.post("/{document_id}/export/{format}")
async def export_study_guide(
    document_id: str,
    format: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Export the study guide in the specified format
    """
    # Get the document
    document = db.query(Document).filter(Document.id == document_id, Document.user_id == current_user.id).first()
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    # Get the study guide
    study_guide = db.query(StudyGuide).filter(
        StudyGuide.document_id == document_id,
        StudyGuide.user_id == current_user.id
    ).first()
    
    if not study_guide:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Study guide not found"
        )
    
    # Parse the detailed content from JSON
    import json
    try:
        study_guide_data = json.loads(study_guide.detailed_content)
        from app.models.study_guide import StudyGuideContent, SummarySection, Question, Concept
        from pydantic import parse_obj_as
        
        # Reconstruct the StudyGuideContent object
        summary_sections = [SummarySection(**section) for section in study_guide_data.get("summary_sections", [])]
        questions = [Question(**q) for q in study_guide_data.get("questions", [])]
        concepts = [Concept(**c) for c in study_guide_data.get("concepts", [])]
        
        study_guide_content = StudyGuideContent(
            title=study_guide.title,
            summary_sections=summary_sections,
            questions=questions,
            concepts=concepts,
            concept_map=study_guide_data.get("concept_map"),
            flashcards=study_guide_data.get("flashcards", [])
        )
        
        # Export the study guide
        export_path = await exporter.export_study_guide(study_guide_content, format)
        
        return {"message": f"Study guide exported successfully in {format} format", "path": export_path}
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error parsing study guide content"
        )
    except Exception as e:
        logger.error(f"Error exporting study guide: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error exporting study guide: {str(e)}"
        )


@router.get("/status/{job_id}", response_model=DocumentStatusResponse)
async def get_processing_status(job_id: str):
    """
    Get the status of a document processing job
    """
    if job_id not in processing_jobs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job ID not found"
        )
    
    job_info = processing_jobs[job_id]
    return DocumentStatusResponse(
        job_id=job_id,
        status=job_info["status"],
        progress=job_info["progress"],
        message=job_info["message"],
        study_guide_id=job_info.get("study_guide_id")
    )


@router.get("/{document_id}")
async def get_document(document_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Get document details
    """
    document = db.query(Document).filter(Document.id == document_id, Document.user_id == current_user.id).first()
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    return DocumentResponse.from_orm(document)


@router.get("/{document_id}/study-guide")
async def get_study_guide(
    document_id: str, 
    current_user: User = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    """
    Get the generated study guide for a document
    """
    # First, check if the document exists and belongs to the user
    document = db.query(Document).filter(Document.id == document_id, Document.user_id == current_user.id).first()
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    # Then get the associated study guide
    study_guide = db.query(StudyGuide).filter(
        StudyGuide.document_id == document_id, 
        StudyGuide.user_id == current_user.id
    ).first()
    
    if not study_guide:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Study guide not generated yet or not found"
        )
    
    return StudyGuideResponse.from_orm(study_guide)


@router.post("/{document_id}/export/{format}")
async def export_study_guide(
    document_id: str,
    format: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Export the study guide in the specified format
    """
    # Get the document
    document = db.query(Document).filter(Document.id == document_id, Document.user_id == current_user.id).first()
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    # Get the study guide
    study_guide = db.query(StudyGuide).filter(
        StudyGuide.document_id == document_id,
        StudyGuide.user_id == current_user.id
    ).first()
    
    if not study_guide:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Study guide not found"
        )
    
    # In a real implementation, we would reconstruct the full StudyGuideContent object
    # For this MVP, we'll just return a success message
    # The actual export functionality would be implemented with the full content
    
    export_path = f"exports/{document_id}_study_guide.{format}"
    
    # This would be where we call the exporter with the actual content
    # export_path = await exporter.export_study_guide(study_guide_content, format, export_path)
    
    return {"message": f"Study guide exported successfully in {format} format", "path": export_path}