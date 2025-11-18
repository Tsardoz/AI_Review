"""
Semantic Scholar API integration.

Provides search and paper retrieval from Semantic Scholar Academic Graph.
"""

import time
import hashlib
import requests
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

from ..core.models import Paper, SearchResult, PaperSource, PaperStatus
from ..utils.logger import get_logger
from ..utils.retry import retry
from ..utils.exceptions import APIError, RateLimitError

logger = get_logger("semantic_scholar")


class SemanticScholarAPI:
    """
    Client for Semantic Scholar API.
    
    Provides methods for searching papers, retrieving paper details,
    and handling rate limiting and error recovery.
    """
    
    BASE_URL = "https://api.semanticscholar.org/graph/v1"
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        rate_limit_delay: float = 0.1,
        cache_ttl_hours: int = 24
    ):
        """
        Initialize Semantic Scholar API client.
        
        Args:
            api_key: Optional API key for higher rate limits
            rate_limit_delay: Delay between requests (seconds)
            cache_ttl_hours: Cache time-to-live in hours
        """
        self.api_key = api_key
        self.rate_limit_delay = rate_limit_delay
        self.cache_ttl = timedelta(hours=cache_ttl_hours)
        self.last_request_time = 0.0
        
        # Session for connection pooling
        self.session = requests.Session()
        if api_key:
            self.session.headers.update({"x-api-key": api_key})
        
        logger.info("Initialized Semantic Scholar API client", has_api_key=bool(api_key))
    
    def _wait_for_rate_limit(self):
        """Enforce rate limiting between requests."""
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        
        if time_since_last_request < self.rate_limit_delay:
            wait_time = self.rate_limit_delay - time_since_last_request
            time.sleep(wait_time)
        
        self.last_request_time = time.time()
    
    @retry(max_retries=3, initial_delay=1.0, retryable_exceptions=(requests.RequestException,))
    def _make_request(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Make an API request with retry logic.
        
        Args:
            endpoint: API endpoint (e.g., '/paper/search')
            params: Query parameters
            
        Returns:
            JSON response as dictionary
            
        Raises:
            APIError: For API errors
            RateLimitError: For rate limit exceeded
        """
        self._wait_for_rate_limit()
        
        url = f"{self.BASE_URL}{endpoint}"
        
        try:
            response = self.session.get(url, params=params, timeout=30)
            
            # Handle rate limiting
            if response.status_code == 429:
                retry_after = int(response.headers.get('Retry-After', 60))
                logger.warning(
                    "Rate limit exceeded",
                    retry_after=retry_after,
                    endpoint=endpoint
                )
                raise RateLimitError(f"Rate limit exceeded. Retry after {retry_after}s")
            
            # Handle other errors
            if response.status_code != 200:
                logger.error(
                    "API request failed",
                    status_code=response.status_code,
                    endpoint=endpoint,
                    response=response.text
                )
                raise APIError(f"API request failed with status {response.status_code}")
            
            return response.json()
        
        except requests.RequestException as e:
            logger.error("Request exception", error=str(e), endpoint=endpoint)
            raise APIError(f"Request failed: {str(e)}")
    
    def search(
        self,
        query: str,
        limit: int = 50,
        offset: int = 0,
        year_min: Optional[int] = None,
        year_max: Optional[int] = None,
        fields: Optional[List[str]] = None
    ) -> SearchResult:
        """
        Search for papers on Semantic Scholar.
        
        Args:
            query: Search query string
            limit: Maximum number of results to return (max 100)
            offset: Offset for pagination
            year_min: Minimum publication year
            year_max: Maximum publication year
            fields: Fields to retrieve (default: comprehensive set)
            
        Returns:
            SearchResult containing papers found
        """
        start_time = time.time()
        
        # Default fields to retrieve
        if fields is None:
            fields = [
                'paperId', 'title', 'abstract', 'authors', 'year',
                'citationCount', 'referenceCount', 'venue',
                'publicationTypes', 'publicationDate', 'journal',
                'externalIds', 'url', 'openAccessPdf'
            ]
        
        # Build query parameters
        params = {
            'query': query,
            'limit': min(limit, 100),  # API max is 100
            'offset': offset,
            'fields': ','.join(fields)
        }
        
        # Add year filters if provided
        if year_min is not None or year_max is not None:
            year_filter = []
            if year_min is not None:
                year_filter.append(f"{year_min}-")
            if year_max is not None:
                if year_min is None:
                    year_filter.append(f"-{year_max}")
                else:
                    year_filter[-1] = f"{year_min}-{year_max}"
            params['year'] = ''.join(year_filter)
        
        logger.info(
            "Searching Semantic Scholar",
            query=query,
            limit=limit,
            year_filter=params.get('year')
        )
        
        try:
            response = self._make_request('/paper/search', params)
            
            # Parse papers
            papers = []
            for item in response.get('data', []):
                paper = self._parse_paper(item)
                if paper:
                    papers.append(paper)
            
            execution_time = time.time() - start_time
            
            result = SearchResult(
                query=query,
                source=PaperSource.SEMANTIC_SCHOLAR,
                papers=papers,
                total_results=response.get('total', len(papers)),
                page=offset // limit + 1,
                page_size=limit,
                execution_time_seconds=execution_time,
                success=True
            )
            
            logger.info(
                "Search completed",
                query=query,
                results_found=len(papers),
                total_available=result.total_results,
                execution_time=f"{execution_time:.2f}s"
            )
            
            return result
        
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error("Search failed", query=query, error=str(e))
            
            return SearchResult(
                query=query,
                source=PaperSource.SEMANTIC_SCHOLAR,
                papers=[],
                total_results=0,
                page=offset // limit + 1,
                page_size=limit,
                execution_time_seconds=execution_time,
                success=False,
                error_message=str(e)
            )
    
    def get_paper_by_id(self, paper_id: str, fields: Optional[List[str]] = None) -> Optional[Paper]:
        """
        Retrieve a specific paper by Semantic Scholar ID.
        
        Args:
            paper_id: Semantic Scholar paper ID
            fields: Fields to retrieve
            
        Returns:
            Paper object or None if not found
        """
        if fields is None:
            fields = [
                'paperId', 'title', 'abstract', 'authors', 'year',
                'citationCount', 'referenceCount', 'venue',
                'publicationTypes', 'publicationDate', 'journal',
                'externalIds', 'url', 'openAccessPdf'
            ]
        
        params = {'fields': ','.join(fields)}
        
        try:
            response = self._make_request(f'/paper/{paper_id}', params)
            return self._parse_paper(response)
        except Exception as e:
            logger.error("Failed to retrieve paper", paper_id=paper_id, error=str(e))
            return None
    
    def _parse_paper(self, data: Dict[str, Any]) -> Optional[Paper]:
        """
        Parse API response into Paper object.
        
        Args:
            data: Raw API response data
            
        Returns:
            Paper object or None if parsing fails
        """
        try:
            # Extract basic info
            paper_id = data.get('paperId')
            title = data.get('title', '').strip()
            
            if not title:
                logger.warning("Skipping paper with no title", paper_id=paper_id)
                return None
            
            # Extract authors
            authors = []
            for author_data in data.get('authors', []):
                author_name = author_data.get('name', '').strip()
                if author_name:
                    authors.append(author_name)
            
            # Extract year
            year = data.get('year')
            if not year:
                # Try to extract from publicationDate
                pub_date = data.get('publicationDate', '')
                if pub_date:
                    try:
                        year = int(pub_date.split('-')[0])
                    except (ValueError, IndexError):
                        year = datetime.now().year
                else:
                    year = datetime.now().year
            
            # Extract external IDs (DOI, arXiv, etc.)
            external_ids = data.get('externalIds', {})
            doi = external_ids.get('DOI')
            arxiv_id = external_ids.get('ArXiv')
            
            # Extract URLs
            url = data.get('url', '')
            pdf_url = None
            open_access_pdf = data.get('openAccessPdf')
            if open_access_pdf and isinstance(open_access_pdf, dict):
                pdf_url = open_access_pdf.get('url')
            
            # Create Paper object
            paper = Paper(
                id=doi if doi else f"s2_{paper_id}",
                title=title,
                authors=authors,
                abstract=data.get('abstract', ''),
                doi=doi,
                url=url,
                pdf_url=pdf_url,
                year=year,
                journal=data.get('journal', {}).get('name') if isinstance(data.get('journal'), dict) else data.get('venue'),
                sources=[PaperSource.SEMANTIC_SCHOLAR],
                source_ids={'semantic_scholar': paper_id},
                status=PaperStatus.DISCOVERED,
                citation_count=data.get('citationCount', 0),
                metadata={
                    'reference_count': data.get('referenceCount', 0),
                    'publication_types': data.get('publicationTypes', []),
                    'venue': data.get('venue', ''),
                    'arxiv_id': arxiv_id
                }
            )
            
            return paper
        
        except Exception as e:
            logger.error("Failed to parse paper", error=str(e), data=str(data)[:200])
            return None
    
    def generate_cache_key(self, query: str, params: Dict[str, Any]) -> str:
        """
        Generate a cache key for a search query.
        
        Args:
            query: Search query
            params: Search parameters
            
        Returns:
            Cache key string
        """
        # Create a consistent string representation of query + params
        cache_string = f"{query}_{sorted(params.items())}"
        return hashlib.md5(cache_string.encode()).hexdigest()
