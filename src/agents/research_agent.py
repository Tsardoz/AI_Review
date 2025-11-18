"""
Research Agent for query formulation and search coordination.

Responsible for:
- Formulating effective search queries from research domain keywords
- Coordinating searches across API sources
- Storing results in database
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, UTC

from ..core.models import ResearchDomain, SearchResult, Paper, PaperSource
from ..core.config import get_config
from ..core.database import DatabaseManager
from ..integrations.semantic_scholar import SemanticScholarAPI
from ..utils.logger import get_logger

logger = get_logger("research_agent")


class QueryFormulator:
    """
    Formulates effective search queries from research domain keywords.
    
    Can use LLM for sophisticated query generation or rule-based approach
    for simpler scenarios.
    """
    
    def __init__(self, use_llm: bool = False):
        """
        Initialize query formulator.
        
        Args:
            use_llm: Whether to use LLM for query generation (Stage 2: False, later: True)
        """
        self.use_llm = use_llm
        self.config = get_config()
    
    def formulate_queries(
        self,
        research_domain: ResearchDomain,
        max_queries: int = 5
    ) -> List[str]:
        """
        Generate search queries from research domain.
        
        Args:
            research_domain: Research domain configuration
            max_queries: Maximum number of queries to generate
            
        Returns:
            List of search query strings
        """
        if self.use_llm:
            return self._formulate_with_llm(research_domain, max_queries)
        else:
            return self._formulate_rule_based(research_domain, max_queries)
    
    def _formulate_rule_based(
        self,
        research_domain: ResearchDomain,
        max_queries: int
    ) -> List[str]:
        """
        Generate queries using rule-based approach.
        
        For Stage 2, we use simple combinations of keywords.
        Later stages will use LLM for more sophisticated query generation.
        """
        queries = []
        
        # Strategy 1: Use keywords directly
        for keyword in research_domain.keywords[:max_queries]:
            queries.append(keyword)
        
        # Strategy 2: Combine keywords with domain
        if len(queries) < max_queries and len(research_domain.keywords) >= 2:
            # Combine first two keywords
            combined = f"{research_domain.keywords[0]} {research_domain.keywords[1]}"
            if combined not in queries:
                queries.append(combined)
        
        # Strategy 3: Add domain context to first keyword
        if len(queries) < max_queries and research_domain.keywords:
            contextualized = f"{research_domain.keywords[0]} {research_domain.subject_type}"
            if contextualized not in queries:
                queries.append(contextualized)
        
        logger.info(
            "Formulated queries (rule-based)",
            domain=research_domain.name,
            num_queries=len(queries),
            queries=queries
        )
        
        return queries[:max_queries]
    
    def _formulate_with_llm(
        self,
        research_domain: ResearchDomain,
        max_queries: int
    ) -> List[str]:
        """
        Generate queries using LLM.
        
        This will be implemented in later stages when we integrate LLM
        for query generation.
        """
        # TODO: Implement LLM-based query generation in later stage
        logger.info("LLM-based query generation not yet implemented, falling back to rule-based")
        return self._formulate_rule_based(research_domain, max_queries)


class ResearchAgent:
    """
    Coordinates literature search operations.
    
    Responsibilities:
    - Query formulation from research domain
    - Executing searches via API integrations
    - Storing results in database
    - Deduplication (Stage 3)
    """
    
    def __init__(
        self,
        database: DatabaseManager,
        semantic_scholar_api_key: Optional[str] = None
    ):
        """
        Initialize Research Agent.
        
        Args:
            database: DatabaseManager instance for persistence
            semantic_scholar_api_key: Optional API key for Semantic Scholar
        """
        self.db = database
        self.config = get_config()
        self.query_formulator = QueryFormulator(use_llm=False)
        
        # Initialize API clients
        self.semantic_scholar = SemanticScholarAPI(api_key=semantic_scholar_api_key)
        
        logger.info("Research Agent initialized")
    
    def search_literature(
        self,
        research_domain: ResearchDomain,
        max_queries: int = 3,
        papers_per_query: int = 20
    ) -> Dict[str, Any]:
        """
        Execute literature search for a research domain.
        
        Args:
            research_domain: Research domain to search for
            max_queries: Maximum number of queries to generate
            papers_per_query: Papers to retrieve per query
            
        Returns:
            Dictionary with search results and statistics
        """
        logger.info(
            "Starting literature search",
            domain=research_domain.name,
            max_queries=max_queries
        )
        
        # Generate search queries
        queries = self.query_formulator.formulate_queries(
            research_domain,
            max_queries=max_queries
        )
        
        # Execute searches
        all_papers = []
        search_results = []
        
        # Get year filters from config
        year_min = self.config.get('search.year_min')
        year_max = self.config.get('search.year_max')
        
        for query in queries:
            logger.info(f"Executing search query: {query}")
            
            try:
                result = self.semantic_scholar.search(
                    query=query,
                    limit=papers_per_query,
                    year_min=year_min,
                    year_max=year_max
                )
                
                search_results.append(result)
                
                if result.success:
                    all_papers.extend(result.papers)
                    logger.info(
                        f"Query completed",
                        query=query,
                        papers_found=len(result.papers)
                    )
                else:
                    logger.warning(
                        f"Query failed",
                        query=query,
                        error=result.error_message
                    )
            
            except Exception as e:
                logger.error(f"Search query failed", query=query, error=str(e))
        
        # Store papers in database
        papers_stored = 0
        for paper in all_papers:
            try:
                if self.db.save_paper(paper):
                    papers_stored += 1
            except Exception as e:
                logger.error(
                    "Failed to store paper",
                    paper_id=paper.id,
                    error=str(e)
                )
        
        # Compile statistics
        stats = {
            'domain': research_domain.name,
            'queries_executed': len(queries),
            'queries': queries,
            'total_papers_found': len(all_papers),
            'papers_stored': papers_stored,
            'unique_papers': len(set(p.id for p in all_papers)),
            'search_results': search_results,
            'timestamp': datetime.now(UTC).isoformat()
        }
        
        logger.info(
            "Literature search completed",
            domain=research_domain.name,
            total_papers=stats['total_papers_found'],
            unique_papers=stats['unique_papers'],
            stored=papers_stored
        )
        
        return stats
    
    def get_paper_details(self, paper_id: str, source: PaperSource) -> Optional[Paper]:
        """
        Retrieve detailed information for a specific paper.
        
        Args:
            paper_id: Paper identifier
            source: Source to retrieve from
            
        Returns:
            Paper object or None if not found
        """
        if source == PaperSource.SEMANTIC_SCHOLAR:
            return self.semantic_scholar.get_paper_by_id(paper_id)
        else:
            logger.warning(f"Source {source} not yet supported for paper retrieval")
            return None
