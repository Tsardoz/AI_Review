"""
Core data models for the literature review system.

Defines Pydantic models for Papers, SearchResults, Summaries, and Citations
with built-in validation and serialization.
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class ResearchDomain(BaseModel):
    """Configuration for the research domain/subject area."""
    name: str = Field(..., description="Name of the research domain (e.g., 'Irrigation Scheduling')")
    subject_type: str = Field(..., description="Academic field (e.g., 'Agricultural Technology', 'Computer Science')")
    keywords: List[str] = Field(default_factory=list, description="Domain-specific keywords")
    description: str = Field("", description="Brief description of the research focus")
    target_journals: List[str] = Field(default_factory=list, description="Target journals/venues")

    class Config:
        use_enum_values = False


class PaperSource(str, Enum):
    """Source of a paper."""
    SEMANTIC_SCHOLAR = "semantic_scholar"
    CROSSREF = "crossref"
    ARXIV = "arxiv"
    DOI = "doi"
    MANUAL = "manual"


class PaperStatus(str, Enum):
    """Status of paper processing."""
    DISCOVERED = "discovered"           # Found in search
    FILTERED = "filtered"                # Passed quality filters
    ACQUIRED = "acquired"                # PDF obtained
    PROCESSED = "processed"              # Text extracted
    SUMMARIZED = "summarized"            # Summary generated
    VALIDATED = "validated"              # Quality check passed
    ARCHIVED = "archived"                # Final storage
    REJECTED = "rejected"                # Failed quality check


class Paper(BaseModel):
    """Core paper entity."""
    id: str = Field(..., description="Unique identifier (DOI or generated)")
    title: str = Field(..., min_length=5, description="Paper title")
    authors: List[str] = Field(default_factory=list, description="Author names")
    abstract: Optional[str] = Field(None, description="Paper abstract")
    doi: Optional[str] = Field(None, description="Digital Object Identifier")
    url: Optional[str] = Field(None, description="Paper URL")
    pdf_url: Optional[str] = Field(None, description="Direct PDF URL")
    
    # Publication metadata
    year: int = Field(..., ge=1900, le=2100, description="Publication year")
    journal: Optional[str] = Field(None, description="Journal name")
    conference: Optional[str] = Field(None, description="Conference name")
    volume: Optional[str] = Field(None)
    issue: Optional[str] = Field(None)
    pages: Optional[str] = Field(None)
    
    # Sourcing
    sources: List[PaperSource] = Field(default_factory=list, description="Sources where paper was found")
    source_ids: Dict[str, str] = Field(default_factory=dict, description="IDs from each source (e.g., {'semantic_scholar': 'ss_id'})")
    
    # Processing
    status: PaperStatus = Field(default=PaperStatus.DISCOVERED)
    discovered_at: datetime = Field(default_factory=datetime.utcnow)
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    
    # Quality metrics
    citation_count: int = Field(default=0, ge=0)
    relevance_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="Relevance to research topic (0-1)")
    quality_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="Overall quality score (0-1)")
    
    # Content
    pdf_path: Optional[str] = Field(None, description="Local path to stored PDF")
    full_text: Optional[str] = Field(None, description="Extracted full text from PDF")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    
    class Config:
        use_enum_values = False
    
    @validator('doi')
    def validate_doi(cls, v):
        """Validate DOI format."""
        if v and not v.startswith('10.'):
            raise ValueError('DOI must start with "10."')
        return v
    
    @validator('url', 'pdf_url')
    def validate_urls(cls, v):
        """Validate URL format."""
        if v and not (v.startswith('http://') or v.startswith('https://')):
            raise ValueError('URL must start with http:// or https://')
        return v


class SearchResult(BaseModel):
    """Result from a search query."""
    query: str = Field(..., description="Search query executed")
    source: PaperSource = Field(..., description="Source API")
    papers: List[Paper] = Field(default_factory=list)
    total_results: int = Field(0, ge=0, description="Total results found (may exceed papers list)")
    page: int = Field(1, ge=1)
    page_size: int = Field(50, ge=1, le=200)
    
    executed_at: datetime = Field(default_factory=datetime.utcnow)
    execution_time_seconds: float = Field(0.0, ge=0.0)
    success: bool = Field(True)
    error_message: Optional[str] = Field(None)
    
    # Caching info
    cached: bool = Field(False, description="Whether result was served from cache")
    
    class Config:
        use_enum_values = False


class Summary(BaseModel):
    """LLM-generated summary of a paper."""
    paper_id: str = Field(..., description="Reference to Paper.id")
    
    # Summary content
    abstract: str = Field(..., min_length=50, description="Generated abstract-like summary")
    key_contributions: List[str] = Field(default_factory=list, description="Main contributions")
    methodology: Optional[str] = Field(None, description="Research methodology summary")
    findings: Optional[str] = Field(None, description="Key findings summary")
    limitations: Optional[str] = Field(None, description="Acknowledged limitations")
    future_work: Optional[str] = Field(None, description="Suggested future directions")
    
    # Quality metrics
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    llm_provider: str = Field(..., description="Which LLM generated this")
    llm_model: str = Field(..., description="Specific model used")
    tokens_used: int = Field(0, ge=0)
    cost_usd: float = Field(0.0, ge=0.0)
    
    # Quality assessment
    quality_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="Quality of summary (0-1)")
    hallucination_risk: Optional[float] = Field(None, ge=0.0, le=1.0, description="Risk of hallucinated content (0-1)")
    
    # Validation
    manually_reviewed: bool = Field(False)
    reviewer_notes: Optional[str] = Field(None)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        use_enum_values = False


class Citation(BaseModel):
    """Formatted citation for a paper."""
    paper_id: str = Field(..., description="Reference to Paper.id")
    
    # Citation formats
    bibtex: Optional[str] = Field(None, description="BibTeX format")
    chicago_author_date: Optional[str] = Field(None, description="Chicago author-date style")
    mla: Optional[str] = Field(None, description="MLA format")
    apa: Optional[str] = Field(None, description="APA format")
    
    # Citation validation
    validated: bool = Field(False)
    doi_validated: bool = Field(False, description="DOI link verified")
    url_validated: bool = Field(False, description="URL accessible")
    validation_errors: List[str] = Field(default_factory=list)
    
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        use_enum_values = False


class ProcessingCheckpoint(BaseModel):
    """Checkpoint for resumable workflows."""
    stage: str = Field(..., description="Stage name (e.g., 'search', 'summarize')")
    status: str = Field(..., description="'running', 'completed', 'failed'")
    papers_processed: int = Field(0, ge=0)
    papers_total: int = Field(0, ge=0)
    
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = Field(None)
    
    error_message: Optional[str] = Field(None)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class CacheEntry(BaseModel):
    """Cache entry for API responses."""
    cache_key: str = Field(..., description="Unique cache key (hash of query+params)")
    source: PaperSource = Field(...)
    data: Dict[str, Any] = Field(..., description="Cached response data")
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime = Field(..., description="Cache expiration time")
    hits: int = Field(0, ge=0, description="Number of times cache was hit")
