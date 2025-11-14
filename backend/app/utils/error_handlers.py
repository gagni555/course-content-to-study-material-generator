import asyncio
import logging
from typing import Dict, Any, Optional
from enum import Enum
from app.config import settings
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration

logger = logging.getLogger(__name__)

class ErrorSeverity(Enum):
    """
    Error severity levels for classification
    """
    TRANSIENT = 1      # Temporary issues (network blips)
    RECOVERABLE = 2    # Issues that can be recovered from (rate limits)
    PERMANENT = 3      # Issues that cannot be recovered from (invalid input)
    CRITICAL = 4       # System critical issues requiring immediate attention

class ErrorRecoveryManager:
    """
    Manages error recovery and retry logic
    """
    
    def __init__(self):
        self.max_retries = 3
        self.base_delay = 1  # seconds
        self.max_delay = 60  # seconds
        self.jitter_factor = 0.1  # 10% jitter for exponential backoff
    
    async def execute_with_retry(self, func, *args, max_retries: Optional[int] = None, **kwargs) -> Any:
        """
        Execute a function with retry logic
        """
        if max_retries is None:
            max_retries = self.max_retries
        
        last_exception = None
        
        for attempt in range(max_retries + 1):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                severity = self.classify_error(e)
                
                if severity == ErrorSeverity.TRANSIENT and attempt < max_retries:
                    delay = self._calculate_delay(attempt)
                    logger.warning(f"Transient error in {func.__name__}, retrying in {delay}s. Attempt {attempt + 1}/{max_retries}. Error: {str(e)}")
                    await asyncio.sleep(delay)
                    continue
                elif severity == ErrorSeverity.RECOVERABLE and attempt < max_retries:
                    delay = self._calculate_delay(attempt)
                    logger.warning(f"Recoverable error in {func.__name__}, retrying in {delay}s. Attempt {attempt + 1}/{max_retries}. Error: {str(e)}")
                    await asyncio.sleep(delay)
                    continue
                elif severity == ErrorSeverity.PERMANENT:
                    logger.error(f"Permanent error in {func.__name__}, not retrying. Error: {str(e)}")
                    raise
                elif severity == ErrorSeverity.CRITICAL:
                    logger.critical(f"Critical error in {func.__name__}: {str(e)}")
                    self._alert_critical_error(e, func.__name__)
                    raise
                else:
                    # Default to recoverable for unknown errors
                    if attempt < max_retries:
                        delay = self._calculate_delay(attempt)
                        logger.warning(f"Unknown error in {func.__name__}, retrying in {delay}s. Attempt {attempt + 1}/{max_retries}. Error: {str(e)}")
                        await asyncio.sleep(delay)
                        continue
                    else:
                        logger.error(f"Failed after {max_retries} attempts. Error: {str(e)}")
                        raise
        
        # If we've exhausted retries, raise the last exception
        raise last_exception
    
    def classify_error(self, exception: Exception) -> ErrorSeverity:
        """
        Classify an exception based on its type and characteristics
        """
        exception_str = str(exception).lower()
        
        # Check for common transient errors
        if any(keyword in exception_str for keyword in [
            "timeout", "connection", "network", "socket", "502", "503", "504"
        ]):
            return ErrorSeverity.TRANSIENT
        
        # Check for rate limiting errors
        if any(keyword in exception_str for keyword in [
            "rate limit", "too many requests", "429", "quota", "limit exceeded"
        ]):
            return ErrorSeverity.RECOVERABLE
        
        # Check for permanent errors (validation, etc.)
        if any(keyword in exception_str for keyword in [
            "validation", "invalid", "not found", "40", "404", "422"
        ]):
            return ErrorSeverity.PERMANENT
        
        # Check for critical errors
        if any(keyword in exception_str for keyword in [
            "database", "connection failed", "500", "internal server error"
        ]):
            return ErrorSeverity.CRITICAL
        
        # Default classification based on exception type
        if isinstance(exception, (TimeoutError, ConnectionError, OSError)):
            return ErrorSeverity.TRANSIENT
        elif isinstance(exception, (ValueError, AttributeError, KeyError)):
            return ErrorSeverity.PERMANENT
        elif isinstance(exception, RuntimeError):
            return ErrorSeverity.CRITICAL
        else:
            # Default to recoverable for most other exceptions
            return ErrorSeverity.RECOVERABLE
    
    def _calculate_delay(self, attempt: int) -> float:
        """
        Calculate delay with exponential backoff and jitter
        """
        delay = min(self.base_delay * (2 ** attempt), self.max_delay)
        # Add jitter to prevent thundering herd
        jitter = delay * self.jitter_factor
        import random
        delay += random.uniform(-jitter, jitter)
        return max(0, delay)
    
    def _alert_critical_error(self, exception: Exception, context: str):
        """
        Alert about critical errors
        """
        logger.critical(f"Critical error in {context}: {str(exception)}")
        # In a real implementation, this might send an alert to a monitoring system
        # or trigger other incident response procedures


class DocumentProcessingErrorHandler:
    """
    Handles errors specific to document processing pipeline
    """
    
    def __init__(self):
        self.recovery_manager = ErrorRecoveryManager()
    
    async def handle_document_parsing_error(self, exception: Exception, file_path: str) -> Dict[str, Any]:
        """
        Handle errors during document parsing with fallback strategies
        """
        logger.error(f"Document parsing error for {file_path}: {str(exception)}")
        
        # Determine if we can try a fallback parsing method
        if "pdf" in file_path.lower():
            # Try alternative PDF parsing methods
            return await self._try_alternative_pdf_parsing(file_path, exception)
        elif "image" in file_path.lower():
            # Try OCR with different parameters
            return await self._try_alternative_ocr(file_path, exception)
        else:
            # For other formats, try using pandoc or other converters
            return await self._try_alternative_conversion(file_path, exception)
    
    async def _try_alternative_pdf_parsing(self, file_path: str, original_exception: Exception) -> Dict[str, Any]:
        """
        Try alternative PDF parsing methods
        """
        try:
            # Try using PyPDF2 as fallback
            import PyPDF2
            with open(file_path, 'rb') as f:
                pdf_reader = PyPDF2.PdfReader(f)
                text_content = ""
                for page in pdf_reader.pages:
                    text_content += page.extract_text() + "\n"
            
            return {
                "status": "success",
                "content": text_content,
                "method": "pypdf2_fallback",
                "warnings": ["Used fallback PDF parsing method"]
            }
        except Exception as e:
            logger.error(f"Fallback PDF parsing also failed: {str(e)}")
            return {
                "status": "failed",
                "error": f"Original: {str(original_exception)}, Fallback: {str(e)}",
                "method": "no_method_available"
            }
    
    async def _try_alternative_ocr(self, file_path: str, original_exception: Exception) -> Dict[str, Any]:
        """
        Try alternative OCR methods
        """
        try:
            from PIL import Image
            import easyocr
            
            # Try EasyOCR as fallback to Tesseract
            reader = easyocr.Reader(['en'])
            results = reader.readtext(file_path)
            
            # Combine the text results
            text_content = " ".join([result[1] for result in results if result[2] > 0.5])  # Only include high confidence results
            
            return {
                "status": "success",
                "content": text_content,
                "method": "easyocr_fallback",
                "warnings": ["Used fallback OCR method"]
            }
        except Exception as e:
            logger.error(f"Fallback OCR also failed: {str(e)}")
            return {
                "status": "failed",
                "error": f"Original: {str(original_exception)}, Fallback: {str(e)}",
                "method": "no_method_available"
            }
    
    async def _try_alternative_conversion(self, file_path: str, original_exception: Exception) -> Dict[str, Any]:
        """
        Try alternative document conversion methods
        """
        try:
            # Try using pypandoc to convert various formats to text
            import pypandoc
            text_content = pypandoc.convert_file(file_path, 'plain')
            
            return {
                "status": "success",
                "content": text_content,
                "method": "pandoc_fallback",
                "warnings": ["Used fallback conversion method"]
            }
        except Exception as e:
            logger.error(f"Fallback conversion also failed: {str(e)}")
            return {
                "status": "failed",
                "error": f"Original: {str(original_exception)}, Fallback: {str(e)}",
                "method": "no_method_available"
            }


class APIErrorHandler:
    """
    Handles API-specific errors and provides appropriate responses
    """
    
    @staticmethod
    def handle_llm_api_error(exception: Exception) -> Dict[str, Any]:
        """
        Handle errors from LLM API calls
        """
        error_msg = str(exception)
        
        # Check for specific LLM API errors
        if "rate limit" in error_msg.lower() or "429" in error_msg:
            return {
                "error_type": "rate_limit",
                "message": "Rate limit exceeded. Please try again later.",
                "retry_after": 60 # Suggest retry after 60 seconds
            }
        elif "quota" in error_msg.lower() or "credit" in error_msg.lower():
            return {
                "error_type": "quota_exceeded",
                "message": "API quota exceeded. Please upgrade your plan or try again later."
            }
        elif "authentication" in error_msg.lower() or "401" in error_msg:
            return {
                "error_type": "authentication",
                "message": "Authentication failed. Please check your API key."
            }
        elif "not found" in error_msg.lower() or "404" in error_msg:
            return {
                "error_type": "not_found",
                "message": "Requested resource not found."
            }
        else:
            return {
                "error_type": "llm_api_error",
                "message": f"LLM API error: {error_msg}"
            }


# Initialize error handlers
error_recovery_manager = ErrorRecoveryManager()
document_error_handler = DocumentProcessingErrorHandler()
api_error_handler = APIErrorHandler()

# Initialize Sentry for error tracking if configured
if hasattr(settings, 'sentry_dsn') and settings.sentry_dsn:
    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        integrations=[FastApiIntegration()],
        traces_sample_rate=1.0
    )