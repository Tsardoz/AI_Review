"""
Custom exceptions for the literature review system.

Provides specific exception types for different error scenarios
to enable better error handling and debugging.
"""

from typing import Optional, Dict, Any


class LiteratureReviewError(Exception):
    """Base exception for all literature review system errors."""
    
    def __init__(self, message: str, error_code: Optional[str] = None, context: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.error_code = error_code
        self.context = context or {}
    
    def __str__(self):
        base_msg = super().__str__()
        if self.error_code:
            base_msg = f"[{self.error_code}] {base_msg}"
        if self.context:
            context_str = ", ".join(f"{k}={v}" for k, v in self.context.items())
            base_msg = f"{base_msg} (Context: {context_str})"
        return base_msg


class ConfigurationError(LiteratureReviewError):
    """Raised when there are configuration issues."""
    pass


class LLMProviderError(LiteratureReviewError):
    """Raised when there are issues with LLM providers."""
    pass


class APIError(LiteratureReviewError):
    """Raised when API calls fail."""
    
    def __init__(self, message: str, provider: Optional[str] = None, status_code: Optional[int] = None, **kwargs):
        super().__init__(message, **kwargs)
        self.provider = provider
        self.status_code = status_code


class SearchError(LiteratureReviewError):
    """Raised when search operations fail."""
    
    def __init__(self, message: str, source: Optional[str] = None, query: Optional[str] = None, **kwargs):
        super().__init__(message, **kwargs)
        self.source = source
        self.query = query


class PDFProcessingError(LiteratureReviewError):
    """Raised when PDF processing fails."""
    
    def __init__(self, message: str, pdf_url: Optional[str] = None, paper_id: Optional[str] = None, **kwargs):
        super().__init__(message, **kwargs)
        self.pdf_url = pdf_url
        self.paper_id = paper_id


class TextExtractionError(PDFProcessingError):
    """Raised when text extraction from PDF fails."""
    pass


class SummarizationError(LiteratureReviewError):
    """Raised when LLM summarization fails."""
    
    def __init__(self, message: str, paper_id: Optional[str] = None, provider: Optional[str] = None, **kwargs):
        super().__init__(message, **kwargs)
        self.paper_id = paper_id
        self.provider = provider


class CitationError(LiteratureReviewError):
    """Raised when citation processing fails."""
    
    def __init__(self, message: str, doi: Optional[str] = None, paper_id: Optional[str] = None, **kwargs):
        super().__init__(message, **kwargs)
        self.doi = doi
        self.paper_id = paper_id


class ValidationError(LiteratureReviewError):
    """Raised when data validation fails."""
    
    def __init__(self, message: str, field: Optional[str] = None, value: Optional[Any] = None, **kwargs):
        super().__init__(message, **kwargs)
        self.field = field
        self.value = value


class RateLimitError(APIError):
    """Raised when API rate limits are exceeded."""
    
    def __init__(self, message: str, retry_after: Optional[int] = None, **kwargs):
        super().__init__(message, **kwargs)
        self.retry_after = retry_after


class AuthenticationError(APIError):
    """Raised when API authentication fails."""
    pass


class NetworkError(LiteratureReviewError):
    """Raised when network operations fail."""
    
    def __init__(self, message: str, url: Optional[str] = None, timeout: Optional[float] = None, **kwargs):
        super().__init__(message, **kwargs)
        self.url = url
        self.timeout = timeout


class DataFormatError(LiteratureReviewError):
    """Raised when data format is unexpected or invalid."""
    
    def __init__(self, message: str, expected_format: Optional[str] = None, received_data: Optional[Any] = None, **kwargs):
        super().__init__(message, **kwargs)
        self.expected_format = expected_format
        self.received_data = received_data


class QualityControlError(LiteratureReviewError):
    """Raised when quality control checks fail."""
    
    def __init__(self, message: str, check_type: Optional[str] = None, threshold: Optional[float] = None, **kwargs):
        super().__init__(message, **kwargs)
        self.check_type = check_type
        self.threshold = threshold


# Exception handling utilities
def handle_api_error(func):
    """Decorator for handling API errors gracefully."""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            # Convert common exceptions to our custom types
            if "rate limit" in str(e).lower():
                raise RateLimitError(f"API rate limit exceeded: {str(e)}")
            elif "auth" in str(e).lower() or "unauthorized" in str(e).lower():
                raise AuthenticationError(f"API authentication failed: {str(e)}")
            elif "timeout" in str(e).lower():
                raise NetworkError(f"API request timeout: {str(e)}")
            else:
                raise APIError(f"API call failed: {str(e)}")
    return wrapper


def create_error_context(error: Exception, **additional_context) -> Dict[str, Any]:
    """
    Create standardized error context for logging.
    
    Args:
        error: The exception that occurred
        **additional_context: Additional context information
        
    Returns:
        Dictionary with error context
    """
    context = {
        'error_type': type(error).__name__,
        'error_message': str(error),
        'error_module': getattr(error, '__module__', 'unknown')
    }
    
    # Add exception-specific context
    if hasattr(error, 'context'):
        context.update(error.context)
    
    # Add additional context
    context.update(additional_context)
    
    return context