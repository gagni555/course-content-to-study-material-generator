# Rules for Agentic AI System
## Course-Content-to-Study-Guide Generator

This document defines the operational rules, behavioral constraints, and decision-making protocols for the AI agents within the Course-Content-to-Study-Guide Generator system. These rules ensure safe, consistent, and reliable autonomous operation.

---

## 1. Core Principles

### 1.1 Fundamental Directives

**P1.1.1 Educational Value First**
- All generated content must prioritize educational accuracy and learning outcomes
- Never sacrifice factual correctness for brevity or simplification
- When uncertain, flag content for human review rather than hallucinating

**P1.1.2 User Safety and Privacy**
- Never store or log personally identifiable information (PII) beyond what's necessary for service delivery
- Treat all uploaded documents as confidential
- Never use user data to train models without explicit consent

**P1.1.3 Graceful Degradation**
- When full functionality is unavailable, provide partial results with clear limitations
- Never fail silently—always communicate processing status and issues
- Prefer "good enough" output with disclaimers over complete failure

**P1.1.4 Deterministic Behavior**
- Given identical inputs and settings, produce consistent outputs
- Use seeded randomness for reproducibility in testing
- Version all prompts and model parameters for auditability

---

## 2. Agent Role Definitions

### 2.1 Ingestion Agent

**Role**: Parse and normalize uploaded documents into structured format

**Authority**: 
- Decide which parser to use based on file type and quality
- Reject files that cannot be processed (malformed, corrupted, too large)
- Apply fallback parsing strategies automatically

**Constraints**:
- Must preserve all textual content from source (no summarization at this stage)
- Must maintain document structure hierarchy
- Cannot modify or interpret content semantics

**Decision Protocol**:
```
IF file_type == "pdf" AND is_text_based(file):
    USE PyMuPDF_parser
ELIF file_type == "pdf" AND is_scanned(file):
    USE OCR_pipeline
ELIF file_type == "docx":
    USE python_docx_parser
ELIF file_type == "image":
    USE OCR_pipeline
ELSE:
    TRY Pandoc_converter
    IF failed:
        REJECT with error message
```

**Error Handling**:
- Retry failed parsing with alternative methods (max 3 attempts)
- If OCR confidence < 70%, warn user and request confirmation
- Log all parsing errors with file metadata for debugging

---

### 2.2 Analysis Agent

**Role**: Extract concepts, identify relationships, and build knowledge representation

**Authority**:
- Determine concept importance scores
- Infer implicit relationships between concepts
- Classify content types (definition, example, theory, etc.)

**Constraints**:
- Cannot add concepts not present in source material
- Must base all relationships on textual evidence
- Cannot make subjective judgments about content quality

**Decision Protocol for Concept Extraction**:
```
FOR each content_chunk:
    concepts = extract_named_entities(chunk)
    concepts += extract_domain_terms(chunk)
    
    FOR each concept:
        importance_score = calculate_importance(
            term_frequency,
            position_in_document,
            emphasis_markers,
            relationship_density
        )
        
        IF importance_score > threshold:
            ADD to knowledge_graph
        ELSE:
            DISCARD
```

**Relationship Detection Rules**:
- "X is defined as Y" → IS_A relationship
- "X causes Y" → CAUSES relationship
- "X consists of Y and Z" → PART_OF relationship
- "X contrasts with Y" → CONTRASTS_WITH relationship
- Spatial proximity < 50 words → RELATED_TO (weak)

**Quality Assurance**:
- Minimum 10 concepts per 1000 words
- Maximum 50 concepts per 1000 words (prevents over-extraction)
- Flag for review if concept extraction rate outside this range

---

### 2.3 Generation Agent

**Role**: Create study materials (summaries, questions, concept maps) from analyzed content

**Authority**:
- Select appropriate generation strategies based on content type
- Adjust output detail level based on user preferences
- Rephrase and restructure content for clarity

**Constraints**:
- Cannot introduce factual information not in source
- Must cite page numbers for all generated content
- Cannot generate copyrighted content (e.g., textbook questions verbatim)

**Prompt Engineering Rules**:

**For Summaries**:
```python
SYSTEM_PROMPT = """
You are an expert educational content summarizer.
Your goal: Create clear, accurate summaries that help students learn.

RULES:
1. Preserve all key facts and definitions
2. Use hierarchical structure (main points → supporting details)
3. Include specific examples when provided in source
4. Cite page numbers in [p.X] format
5. Use active voice and present tense
6. Never add information not in the source

OUTPUT FORMAT:
# Topic Name
## Key Concepts
- Concept 1: Definition [p.X]
- Concept 2: Definition [p.Y]

## Detailed Explanation
[2-3 paragraphs covering main ideas]

## Important Examples
- Example 1 [p.Z]
- Example 2 [p.W]
"""
```

**For Question Generation**:
```python
QUESTION_GENERATION_RULES = {
    "remember": {
        "types": ["multiple_choice", "fill_blank", "true_false"],
        "verbs": ["identify", "define", "recall", "list"],
        "example": "What is the definition of X? [p.Y]"
    },
    "understand": {
        "types": ["short_answer", "matching"],
        "verbs": ["explain", "summarize", "compare", "classify"],
        "example": "Explain the difference between X and Y. [p.Z]"
    },
    "apply": {
        "types": ["problem_solving", "case_study"],
        "verbs": ["calculate", "demonstrate", "apply", "solve"],
        "example": "Given X scenario, apply Y principle to solve for Z."
    },
    "analyze": {
        "types": ["short_essay", "diagram_labeling"],
        "verbs": ["analyze", "differentiate", "investigate"],
        "example": "Analyze the relationship between X and Y."
    }
}
```

**Question Quality Criteria**:
- **Clarity**: Question must be unambiguous
- **Answerability**: Answer must be derivable from source material
- **Appropriate Difficulty**: Matches selected difficulty level
- **Distractor Plausibility** (MCQs): Wrong answers should be plausible but clearly incorrect

**Self-Evaluation Protocol**:
```
FOR each generated_question:
    IF contains_information_not_in_source:
        REJECT and REGENERATE
    IF ambiguous OR unanswerable:
        REJECT and REGENERATE
    IF difficulty_mismatch:
        ADJUST and RETRY
    
    IF regeneration_attempts > 3:
        FLAG for human review
```

---

### 2.4 Quality Assurance Agent

**Role**: Validate all generated content for accuracy, completeness, and quality

**Authority**:
- Accept, reject, or request revision of generated content
- Escalate to human review when confidence < 80%
- Modify content formatting and presentation

**Constraints**:
- Cannot change factual content, only presentation
- Must explain all rejections with specific reasons
- Cannot override user-specified preferences (e.g., detail level)

**Validation Checklist**:

**For Summaries**:
- [ ] All key concepts from source are included
- [ ] No hallucinated facts or unsupported claims
- [ ] Appropriate length (within 20% of target)
- [ ] Clear hierarchical structure
- [ ] All citations present and accurate
- [ ] Reading level appropriate for target audience
- [ ] No grammatical errors

**For Questions**:
- [ ] Each question tests a specific concept
- [ ] Questions span multiple Bloom's levels
- [ ] Correct answers are unambiguous
- [ ] MCQ distractors are plausible
- [ ] Question distribution matches content importance
- [ ] No duplicate or near-duplicate questions
- [ ] Answer key is accurate and complete

**For Concept Maps**:
- [ ] All major concepts included
- [ ] Relationships are accurate and directional
- [ ] Visual layout is readable (no overlap)
- [ ] Color coding is consistent
- [ ] Legend explains all symbols

**Confidence Scoring**:
```python
def calculate_confidence(content, source):
    score = 1.0
    
    # Factual consistency check
    if contains_unsupported_claims(content, source):
        score -= 0.3
    
    # Completeness check
    if missing_key_concepts(content, source):
        score -= 0.2
    
    # Quality check
    if has_formatting_issues(content):
        score -= 0.1
    
    if has_citation_errors(content):
        score -= 0.1
    
    return max(0, score)
```

**Escalation Thresholds**:
- Confidence < 0.8: Flag for human review
- Confidence < 0.6: Reject and regenerate
- Confidence ≥ 0.8: Accept and deliver

---

## 3. Data Handling and Safety Rules

### 3.1 Input Validation

**D3.1.1 File Type Restrictions**
```python
ALLOWED_FILE_TYPES = [
    ".pdf", ".docx", ".doc", ".pptx", ".ppt",
    ".jpg", ".jpeg", ".png", ".txt", ".md"
]

BLOCKED_FILE_TYPES = [
    ".exe", ".dll", ".sh", ".bat", ".zip",
    ".rar", ".7z", ".dmg", ".pkg"
]

MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
MIN_FILE_SIZE = 1024  # 1KB
```

**D3.1.2 Content Filtering**
- Reject documents containing malicious code or scripts
- Reject documents with excessive encryption or DRM
- Reject documents that are primarily images without text (< 100 words)
- Flag documents with concerning content (violence, explicit material) for review

### 3.2 Data Retention

**D3.2.1 Temporary Storage**
- Raw uploaded files: Delete after 30 days (or when user deletes account)
- Processing artifacts: Delete immediately after job completion
- Generated study guides: Persist indefinitely (user-owned)
- Error logs: Retain for 90 days, then archive

**D3.2.2 User Data Deletion**
- Honor deletion requests within 48 hours
- Permanently delete all user documents and metadata
- Retain anonymized usage statistics only
- Comply with GDPR "right to be forgotten"

### 3.3 API Key and Secret Management

**D3.3.1 Secure Storage**
- Never log API keys, tokens, or passwords
- Store secrets in AWS Secrets Manager or HashiCorp Vault
- Rotate API keys every 90 days
- Use environment variables, never hardcode secrets

**D3.3.2 Access Control**
- Principle of least privilege: Each service gets only necessary permissions
- API keys are scoped to specific operations (read-only where possible)
- Audit all secret access attempts

---

## 4. Interaction Rules with External APIs

### 4.1 LLM API Usage

**A4.1.1 Rate Limiting**
- Respect API provider rate limits (90% of max to account for burst)
- Implement exponential backoff for rate limit errors (2^n seconds, max 32s)
- Queue requests when near rate limit, never discard

**A4.1.2 Token Optimization**
```python
def optimize_llm_request(content, max_tokens=4000):
    # Truncation strategy
    if token_count(content) > max_tokens:
        # Priority: Concepts > Examples > Filler
        content = prioritized_truncation(content, max_tokens)
    
    # Compression strategy for very long documents
    if token_count(content) > 8000:
        content = semantic_compression(content, target_tokens=7000)
    
    return content
```

**A4.1.3 Cost Control**
- Set per-user daily token limits (free: 50K, premium: 500K)
- Monitor token usage per request and per user
- Alert if daily spend exceeds budget ($100/day default)
- Cache LLM responses for identical inputs (TTL: 24 hours)

**A4.1.4 Fallback Strategy**
```python
def generate_with_fallback(prompt, primary="claude", fallback="gpt4"):
    try:
        return call_llm(primary, prompt)
    except (RateLimitError, APIError) as e:
        log_error(e)
        try:
            return call_llm(fallback, prompt)
        except Exception as e2:
            log_critical(e2)
            return degraded_mode_response(prompt)
```

### 4.2 Vector Database Interactions

**A4.2.1 Embedding Generation**
- Batch embed documents (chunks of 100) to reduce API calls
- Cache embeddings for unchanged documents
- Use lower-cost embedding models for non-critical searches

**A4.2.2 Semantic Search**
- Set max results = 10 for initial search
- Re-rank results using LLM for better relevance
- Filter by similarity threshold (cosine > 0.7)

---

## 5. Coding Style and Conventions

### 5.1 Python Style

**S5.1.1 Naming Conventions**
```python
# Classes: PascalCase
class DocumentProcessor:
    pass

# Functions and variables: snake_case
def process_document(file_path: str) -> Dict:
    user_id = get_user_id()
    return result

# Constants: UPPER_SNAKE_CASE
MAX_FILE_SIZE = 50 * 1024 * 1024
DEFAULT_TIMEOUT = 30

# Private methods: Leading underscore
def _internal_helper(self):
    pass
```

**S5.1.2 Type Hints**
- Always use type hints for function parameters and return values
- Use `Optional[T]` for nullable types
- Use `Union[T1, T2]` for multiple types
- Use `List[T]`, `Dict[K, V]`, `Tuple[T1, T2]` for collections

```python
from typing import List, Dict, Optional, Union

def extract_concepts(
    content: str,
    min_score: float = 0.5,
    max_concepts: Optional[int] = None
) -> List[Dict[str, Union[str, float]]]:
    """Extract key concepts from content.
    
    Args:
        content: Input text to analyze
        min_score: Minimum importance score (0-1)
        max_concepts: Maximum concepts to return (None = unlimited)
    
    Returns:
        List of concept dictionaries with 'term' and 'score' keys
    """
    pass
```

**S5.1.3 Error Handling**
```python
# Specific exceptions over generic Exception
try:
    result = risky_operation()
except FileNotFoundError as e:
    logger.error(f"File not found: {e}")
    raise
except PermissionError as e:
    logger.error(f"Permission denied: {e}")
    return None
except Exception as e:
    logger.critical(f"Unexpected error: {e}")
    sentry.capture_exception(e)
    raise

# Use context managers for resources
with open(file_path, 'r') as f:
    content = f.read()
```

### 5.2 Async/Await Patterns

**S5.2.1 Async Best Practices**
```python
# Use async for I/O-bound operations
async def fetch_embeddings(texts: List[str]) -> List[np.ndarray]:
    async with aiohttp.ClientSession() as session:
        tasks = [embed_text(session, text) for text in texts]
        return await asyncio.gather(*tasks)

# Use sync for CPU-bound operations
def analyze_content(text: str) -> Dict:
    # Blocking NLP operations
    doc = nlp(text)
    return extract_features(doc)
```

**S5.2.2 Concurrent Execution**
```python
# Process documents concurrently (limit parallelism)
semaphore = asyncio.Semaphore(5)  # Max 5 concurrent

async def process_with_limit(doc_id: str):
    async with semaphore:
        return await process_document(doc_id)

results = await asyncio.gather(
    *[process_with_limit(id) for id in document_ids]
)
```

### 5.3 Logging Standards

**S5.3.1 Log Levels**
```python
# DEBUG: Detailed diagnostic info
logger.debug(f"Processing chunk {i}/{total}, size={len(chunk)}")

# INFO: General operational events
logger.info(f"User {user_id} uploaded document {doc_id}")

# WARNING: Unexpected but recoverable situations
logger.warning(f"OCR confidence low ({conf:.2f}), flagging for review")

# ERROR: Serious problems requiring attention
logger.error(f"Failed to parse document {doc_id}: {error}")

# CRITICAL: System failures requiring immediate action
logger.critical(f"Database connection lost, unable to save results")
```

**S5.3.2 Structured Logging**
```python
# Use structured logging for better searchability
logger.info(
    "Document processed successfully",
    extra={
        "user_id": user_id,
        "document_id": doc_id,
        "processing_time_ms": elapsed_ms,
        "page_count": pages,
        "token_count": tokens
    }
)
```

---

## 6. Self-Debugging and Recovery Protocols

### 6.1 Automated Debugging

**R6.1.1 Error Classification**
```python
class ErrorSeverity(Enum):
    TRANSIENT = 1    # Retry immediately (network blips)
    RECOVERABLE = 2  # Retry with backoff (rate limits)
    PERMANENT = 3    # Don't retry (invalid input)
    CRITICAL = 4     # Escalate immediately (data corruption)

def classify_error(exception: Exception) -> ErrorSeverity:
    if isinstance(exception, (TimeoutError, ConnectionError)):
        return ErrorSeverity.TRANSIENT
    elif isinstance(exception, RateLimitError):
        return ErrorSeverity.RECOVERABLE
    elif isinstance(exception, ValidationError):
        return ErrorSeverity.PERMANENT
    elif isinstance(exception, DatabaseError):
        return ErrorSeverity.CRITICAL
    else:
        return ErrorSeverity.RECOVERABLE  # Default to recoverable
```

**R6.1.2 Self-Healing Actions**
```python
async def self_healing_execution(func, *args, max_retries=3, **kwargs):
    for attempt in range(max_retries):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            severity = classify_error(e)
            
            if severity == ErrorSeverity.TRANSIENT:
                await asyncio.sleep(1)  # Brief pause
                continue
            
            elif severity == ErrorSeverity.RECOVERABLE:
                backoff = 2 ** attempt
                logger.warning(f"Retry {attempt+1}/{max_retries} after {backoff}s")
                await asyncio.sleep(backoff)
                continue
            
            elif severity == ErrorSeverity.PERMANENT:
                logger.error(f"Permanent error, aborting: {e}")
                raise
            
            elif severity == ErrorSeverity.CRITICAL:
                logger.critical(f"Critical error: {e}")
                alert_ops_team(e)
                raise
    
    raise MaxRetriesExceeded(f"Failed after {max_retries} attempts")
```

### 6.2 Checkpoint and Recovery

**R6.2.1 State Checkpointing**
```python
class ProcessingCheckpoint:
    """Save processing state for recovery."""
    
    def __init__(self, job_id: str):
        self.job_id = job_id
        self.checkpoint_key = f"checkpoint:{job_id}"
    
    async def save(self, stage: str, data: Dict):
        """Save checkpoint to Redis."""
        checkpoint = {
            "stage": stage,
            "data": data,
            "timestamp": datetime.utcnow().isoformat()
        }
        await redis.setex(
            self.checkpoint_key,
            ttl=3600,  # 1 hour
            value=json.dumps(checkpoint)
        )
    
    async def recover(self) -> Optional[Dict]:
        """Recover from last checkpoint."""
        checkpoint_data = await redis.get(self.checkpoint_key)
        if checkpoint_data:
            return json.loads(checkpoint_data)
        return None
```

**R6.2.2 Recovery Strategy**
```python
async def process_with_recovery(job_id: str, document_path: str):
    checkpoint = ProcessingCheckpoint(job_id)
    
    # Try to recover previous state
    saved_state = await checkpoint.recover()
    
    if saved_state:
        logger.info(f"Recovering job {job_id} from stage {saved_state['stage']}")
        start_stage = saved_state['stage']
        intermediate_data = saved_state['data']
    else:
        start_stage = "ingestion"
        intermediate_data = None
    
    # Resume from checkpoint
    if start_stage == "ingestion":
        normalized = await ingest_document(document_path)
        await checkpoint.save("analysis", {"normalized": normalized})
    
    if start_stage in ["ingestion", "analysis"]:
        concepts = await analyze_content(intermediate_data or normalized)
        await checkpoint.save("generation", {"concepts": concepts})
    
    if start_stage in ["ingestion", "analysis", "generation"]:
        study_guide = await generate_materials(intermediate_data or concepts)
        await checkpoint.save("complete", {"study_guide": study_guide})
    
    # Clear checkpoint after successful completion
    await redis.delete(checkpoint.checkpoint_key)
    
    return study_guide
```

### 6.3 Health Checks

**R6.3.1 System Health Monitoring**
```python
async def health_check() -> Dict[str, str]:
    """Check health of all system components."""
    health = {}
    
    # Database connectivity
    try:
        await db.execute("SELECT 1")
        health["database"] = "healthy"
    except Exception:
        health["database"] = "unhealthy"
    
    # Redis connectivity
    try:
        await redis.ping()
        health["redis"] = "healthy"
    except Exception:
        health["redis"] = "unhealthy"
    
    # LLM API availability
    try:
        await test_llm_connection()
        health["llm_api"] = "healthy"
    except Exception:
        health["llm_api"] = "unhealthy"
    
    # Storage availability
    try:
        await storage.head_object("health-check.txt")
        health["storage"] = "healthy"
    except Exception:
        health["storage"] = "unhealthy"
    
    return health
```

---

## 7. Decision-Making Protocols

### 7.1 Uncertainty Handling

**When agents encounter ambiguous situations:**

1. **Quantify Uncertainty**: Assign confidence score (0-1)
2. **Apply Threshold Logic**:
   - Confidence ≥ 0.9: Proceed autonomously
   - 0.7 ≤ Confidence < 0.9: Proceed with warning flag
   - 0.5 ≤ Confidence < 0.7: Present options to user
   - Confidence < 0.5: Escalate to human review

3. **Document Decision**: Log reasoning and confidence score

### 7.2 Conflict Resolution

**When multiple valid approaches exist:**

1. **Optimize for User Preference**: Check saved settings
2. **Default to Conservative**: Choose safer, more accurate option
3. **Preserve Optionality**: Offer multiple outputs when feasible
4. **Learn from Feedback**: Adjust defaults based on user ratings

---

## 8. Prohibited Actions

Agents **MUST NEVER**:

1. ❌ Hallucinate facts not present in source material
2. ❌ Reproduce copyrighted content verbatim (beyond fair use)
3. ❌ Generate harmful, offensive, or discriminatory content
4. ❌ Bypass security restrictions or authentication
5. ❌ Modify user data without explicit user action
6. ❌ Share user data with unauthorized parties
7. ❌ Ignore error conditions or fail silently
8. ❌ Execute arbitrary code from user input
9. ❌ Overwrite existing user content without confirmation
10. ❌ Continue processing after critical error

---

**Rules Version**: 1.0  
**Effective Date**: November 2025  
**Review Cycle**: Quarterly  
**Owner**: AI Safety & Engineering Team