# Codebase Infrastructure

## System Overview

The Course-Content-to-Study-Guide Generator follows a **modular pipeline architecture** with clear separation between ingestion, processing, generation, and presentation layers. The system is designed for horizontal scalability and asynchronous processing to handle variable document sizes and user loads.

```
┌─────────────────────────────────────────────────────────────┐
│                      CLIENT LAYER                            │
│  [Web UI] ←→ [Mobile App] ←→ [API Clients]                  │
└─────────────────────────────────────────────────────────────┘
                           ↓ HTTPS/REST
┌─────────────────────────────────────────────────────────────┐
│                    API GATEWAY LAYER                         │
│  • Authentication (JWT)  • Rate Limiting  • Request Routing  │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│                  ORCHESTRATION LAYER                         │
│                  [FastAPI Backend]                           │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   Document   │  │  Processing  │  │  Generation  │      │
│  │   Manager    │→ │   Pipeline   │→ │   Service    │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
         ↓                    ↓                    ↓
┌─────────────────────────────────────────────────────────────┐
│                   PROCESSING MODULES                         │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ INGESTION MODULE                                      │  │
│  │ • PDF Parser    • DOCX Parser   • Image OCR          │  │
│  │ • Format Normalizer   • Metadata Extractor           │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ ANALYSIS MODULE                                       │  │
│  │ • Content Chunker   • Topic Classifier                │  │
│  │ • Concept Extractor • Relationship Mapper             │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ GENERATION MODULE                                     │  │
│  │ • Summary Generator   • Question Generator            │  │
│  │ • Concept Map Builder • Spaced Repetition Scheduler   │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ EXPORT MODULE                                         │  │
│  │ • PDF Renderer   • Markdown Formatter                 │  │
│  │ • Anki Exporter  • Interactive Web Generator          │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
         ↓                                           ↓
┌─────────────────────┐                  ┌──────────────────────┐
│   DATA LAYER        │                  │   AI/ML LAYER        │
│                     │                  │                      │
│ • PostgreSQL        │                  │ • LLM Inference      │
│   (User/Metadata)   │                  │   (GPT-4 / Claude)   │
│ • Redis Cache       │                  │ • Vector Store       │
│ • S3/Blob Storage   │                  │   (Pinecone/Weaviate)│
│   (Documents)       │                  │ • Embedding Models   │
└─────────────────────┘                  └──────────────────────┘
```

## Component Breakdown

### 1. API Gateway Layer

**Responsibilities:**
- User authentication and session management (JWT tokens)
- Request validation and sanitization
- Rate limiting (tier-based: free/premium)
- CORS handling and security headers

**Technology:** NGINX or AWS API Gateway

**Flow:**
```
User Request → Auth Check → Rate Limit Check → Route to Backend → Response
```

---

### 2. Orchestration Layer (FastAPI Backend)

**Core Services:**

#### Document Manager Service
- Handles file uploads (multipart/form-data)
- Validates file types and sizes (max 50MB)
- Generates unique document IDs
- Triggers asynchronous processing pipeline
- Returns job IDs for status tracking

#### Processing Pipeline Service
- Manages state machine for document processing stages
- Coordinates between processing modules
- Handles retries and error recovery
- Emits progress updates via WebSocket

#### Generation Service
- Receives structured data from processing modules
- Orchestrates LLM calls for content generation
- Manages prompt templates and context windows
- Handles output formatting and validation

**API Endpoints:**
```
POST   /api/v1/documents/upload          # Upload document
GET    /api/v1/documents/{id}/status     # Check processing status
GET    /api/v1/documents/{id}/result     # Retrieve study guide
POST   /api/v1/generate/questions        # Generate practice questions
POST   /api/v1/generate/concept-map      # Generate concept map
GET    /api/v1/export/{id}/{format}      # Export in specified format
```

---

### 3. Processing Modules

#### Ingestion Module

**PDF Parser:**
- Library: PyMuPDF (fitz) for text extraction
- Handles: Text, images, tables, annotations
- Preserves: Formatting, page structure, metadata

**DOCX Parser:**
- Library: python-docx
- Extracts: Text, headings hierarchy, lists, tables

**Image OCR:**
- Library: Tesseract + EasyOCR
- Handles: Scanned PDFs, images, handwritten notes
- Preprocessing: Deskewing, noise reduction, contrast enhancement

**Format Normalizer:**
- Converts all inputs to unified JSON structure:
```json
{
  "document_id": "uuid",
  "metadata": {
    "title": "string",
    "author": "string",
    "date": "ISO8601",
    "course": "string"
  },
  "sections": [
    {
      "type": "heading|paragraph|list|table|image",
      "level": 1,
      "content": "string",
      "position": {"page": 1, "order": 1}
    }
  ]
}
```

---

#### Analysis Module

**Content Chunker:**
- Splits documents into semantic chunks (500-1000 tokens)
- Preserves context boundaries (doesn't split mid-sentence)
- Maintains hierarchy (headers with their content)

**Topic Classifier:**
- Uses lightweight classification model (DistilBERT fine-tuned)
- Categorizes: Definition, Example, Theory, Procedure, Case Study
- Confidence scoring for each classification

**Concept Extractor:**
- NER model (spaCy + custom training) for domain-specific terms
- Extracts: Key terms, definitions, formulas, important dates
- Scoring: Term frequency, position weighting, emphasis detection

**Relationship Mapper:**
- Builds knowledge graph using co-occurrence and semantic similarity
- Edge types: "is-a", "part-of", "caused-by", "contrasts-with"
- Uses sentence transformers for semantic relationships

---

#### Generation Module

**Summary Generator:**
- Prompt engineering pattern:
```
You are an expert educational content summarizer.

Input: [Document section]
Task: Create a hierarchical summary following Bloom's Taxonomy
- Remember: Key facts and definitions
- Understand: Main concepts and explanations
- Apply: Examples and applications

Output format: Structured bullet points with examples
Tone: Academic but accessible
```

**Question Generator:**
- Multi-tiered generation based on Bloom's Taxonomy:
  - **Remember**: MCQs and fill-in-the-blank
  - **Understand**: Short answer and explanation prompts
  - **Apply/Analyze**: Case studies and problem-solving
  - **Evaluate/Create**: Essay prompts and project ideas

- Quality filters:
  - Answerability check (can question be answered from content?)
  - Difficulty calibration (adjustable slider)
  - Distractor generation for MCQs (plausible wrong answers)

**Concept Map Builder:**
- Converts knowledge graph to visual format
- Layout algorithm: Force-directed graph (D3.js)
- Node sizing based on concept importance
- Edge thickness based on relationship strength
- Output: SVG or interactive HTML

**Spaced Repetition Scheduler:**
- Implements SuperMemo SM-2 algorithm
- Generates review schedules based on:
  - Initial difficulty assessment
  - User performance history (if available)
  - Content importance weighting

---

#### Export Module

**PDF Renderer:**
- Library: WeasyPrint for HTML-to-PDF conversion
- Templates: LaTeX-quality academic formatting
- Includes: Table of contents, page numbers, headers/footers

**Markdown Formatter:**
- Clean markdown with proper heading hierarchy
- Code blocks for formulas (LaTeX)
- Tables in GitHub-flavored markdown format

**Anki Exporter:**
- Generates .apkg files directly
- Card types: Basic, Cloze, Image Occlusion
- Tags: Auto-tagging by topic and difficulty

**Interactive Web Generator:**
- Single-page HTML application
- Features: Collapsible sections, search, progress tracking
- Framework: Alpine.js (lightweight, no build step)

---

### 4. Data Layer

**PostgreSQL Database:**
- Tables: users, documents, study_guides, questions, user_progress
- Indexes: document_id, user_id, created_at
- Partitioning: By user_id for scalability

**Redis Cache:**
- Session storage (JWT tokens, user preferences)
- Processing job status (TTL: 24 hours)
- Rate limiting counters
- Frequently accessed study guides (LRU eviction)

**S3/Blob Storage:**
- Raw uploaded documents (retention: 30 days)
- Generated study guides (retention: indefinite)
- Exported files (pre-signed URLs, TTL: 7 days)
- Bucket structure: `/{user_id}/{document_id}/{files}`

---

### 5. AI/ML Layer

**LLM Inference:**
- Primary: Claude Sonnet 4 (via Anthropic API)
- Fallback: GPT-4 (via OpenAI API)
- Context management: Sliding window for long documents
- Token optimization: Compression prompts for large inputs

**Vector Store:**
- Stores document embeddings for semantic search
- Technology: Pinecone or Weaviate
- Dimensions: 1536 (OpenAI ada-002) or 768 (sentence-transformers)
- Use case: Finding similar content across user's documents

**Embedding Models:**
- Sentence transformers (all-MiniLM-L6-v2) for lightweight tasks
- OpenAI ada-002 for high-quality semantic search
- Batch processing: 100 chunks at a time

---

## Agentic Coding Workflow

The system uses an **agentic orchestration pattern** where each module operates semi-autonomously:

### Agent Types

1. **Ingestion Agent**
   - Detects file type and selects appropriate parser
   - Self-healing: Retries with alternative parsers on failure
   - Outputs normalized data structure

2. **Analysis Agent**
   - Receives normalized content
   - Runs parallel analysis tasks (chunking, classification, extraction)
   - Builds unified knowledge representation

3. **Generation Agent**
   - Receives knowledge representation and user preferences
   - Dynamically selects generation strategies based on content type
   - Self-evaluates output quality and retries if below threshold

4. **Quality Assurance Agent**
   - Reviews all generated content
   - Checks: Factual consistency, readability, completeness
   - Flags for human review if confidence < 80%

### Communication Protocol

Agents communicate via **message queue** (RabbitMQ or AWS SQS):
```
{
  "job_id": "uuid",
  "stage": "analysis",
  "status": "completed",
  "data": {...},
  "metadata": {
    "duration_ms": 1250,
    "tokens_used": 3500,
    "confidence": 0.92
  },
  "next_stage": "generation"
}
```

### Error Handling Strategy

- **Transient Errors**: Exponential backoff retry (3 attempts)
- **Permanent Errors**: Fall back to degraded mode (simpler processing)
- **Critical Errors**: Alert human operators, pause processing
- **Recovery**: Checkpoint system saves progress at each stage

---

## Deployment Architecture

### Development Environment
- Docker Compose with all services
- Local LLM runner (Ollama) for testing without API costs
- Hot reload for rapid iteration

### Production Environment
- Kubernetes cluster (AWS EKS or GCP GKE)
- Horizontal pod autoscaling based on queue depth
- Blue-green deployment for zero-downtime updates
- CDN (CloudFlare) for static assets and exported files

### Monitoring Stack
- Prometheus + Grafana for metrics
- ELK Stack (Elasticsearch, Logstash, Kibana) for logs
- Sentry for error tracking
- Custom dashboards: Processing time, success rate, token usage

---

## Security Considerations

- **Data Encryption**: At rest (AES-256) and in transit (TLS 1.3)
- **Access Control**: Role-based permissions (RBAC)
- **API Security**: Rate limiting, input validation, SQL injection prevention
- **Privacy**: User documents deleted after 30 days unless saved
- **Compliance**: GDPR and FERPA compliant data handling

---

**Architecture Version:** 1.0  
**Last Updated:** November 2025  
**Maintained By:** Infrastructure Team