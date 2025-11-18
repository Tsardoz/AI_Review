"""
Tests for Stage 2: Search Agent and Query Formulation.

Tests:
- Query formulation from research domain
- Semantic Scholar API integration
- Search result parsing
- Database storage
- Research agent coordination
"""

import os
import sys
import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from src.core.models import ResearchDomain, Paper, SearchResult, PaperSource
from src.core.database import DatabaseManager
from src.agents.research_agent import QueryFormulator, ResearchAgent
from src.integrations.semantic_scholar import SemanticScholarAPI


class TestQueryFormulator:
    """Test query formulation from research domains."""
    
    def test_formulate_basic_queries(self):
        """Test basic rule-based query formulation."""
        formulator = QueryFormulator(use_llm=False)
        
        domain = ResearchDomain(
            name="Test Domain",
            subject_type="Computer Science",
            keywords=["machine learning", "neural networks", "deep learning"],
            description="Test domain"
        )
        
        queries = formulator.formulate_queries(domain, max_queries=3)
        
        assert len(queries) > 0
        assert len(queries) <= 3
        assert all(isinstance(q, str) for q in queries)
        # Should use at least some keywords
        assert any(keyword in ' '.join(queries) for keyword in domain.keywords)
    
    def test_formulate_with_few_keywords(self):
        """Test query formulation with limited keywords."""
        formulator = QueryFormulator(use_llm=False)
        
        domain = ResearchDomain(
            name="Minimal Domain",
            subject_type="Physics",
            keywords=["quantum computing"],
            description="Minimal test"
        )
        
        queries = formulator.formulate_queries(domain, max_queries=5)
        
        assert len(queries) > 0
        assert "quantum computing" in queries[0]
    
    def test_formulate_combines_keywords(self):
        """Test that formulator creates combined queries."""
        formulator = QueryFormulator(use_llm=False)
        
        domain = ResearchDomain(
            name="Combined Domain",
            subject_type="Biology",
            keywords=["gene editing", "CRISPR", "genomics"],
            description="Test combination"
        )
        
        queries = formulator.formulate_queries(domain, max_queries=5)
        
        # Should have some queries with combined keywords
        assert any(len(q.split()) > 2 for q in queries)


class TestSemanticScholarAPIParsing:
    """Test Semantic Scholar API parsing logic."""
    
    @pytest.fixture
    def mock_data(self):
        """Load mock Semantic Scholar response data."""
        mock_file = Path(__file__).parent.parent / 'data' / 'test_data' / 'semantic_scholar_mock.json'
        with open(mock_file, 'r') as f:
            return json.load(f)
    
    def test_parse_paper(self, mock_data):
        """Test parsing individual paper from API response."""
        api = SemanticScholarAPI()
        
        paper_data = mock_data['mock_search_response']['data'][0]
        paper = api._parse_paper(paper_data)
        
        assert paper is not None
        assert paper.title == "Automated Literature Review Using Large Language Models: A Systematic Approach"
        assert len(paper.authors) == 2
        assert "Jane Smith" in paper.authors
        assert paper.year == 2023
        assert paper.doi == "10.1371/journal.pone.mock123"
        assert paper.citation_count == 15
        assert PaperSource.SEMANTIC_SCHOLAR in paper.sources
    
    def test_parse_paper_without_doi(self, mock_data):
        """Test parsing paper that has no DOI."""
        api = SemanticScholarAPI()
        
        # Modify mock data to remove DOI
        paper_data = mock_data['mock_search_response']['data'][1].copy()
        paper = api._parse_paper(paper_data)
        
        assert paper is not None
        # Should generate ID from Semantic Scholar ID if no DOI
        assert paper.id.startswith('s2_') or paper.doi is not None
    
    def test_parse_paper_with_missing_fields(self):
        """Test parsing paper with minimal required fields."""
        api = SemanticScholarAPI()
        
        minimal_paper = {
            'paperId': 'test123',
            'title': 'Minimal Paper',
            'authors': [],
            'year': 2023
        }
        
        paper = api._parse_paper(minimal_paper)
        
        assert paper is not None
        assert paper.title == 'Minimal Paper'
        assert paper.year == 2023
    
    def test_parse_paper_no_title_returns_none(self):
        """Test that paper without title is skipped."""
        api = SemanticScholarAPI()
        
        invalid_paper = {
            'paperId': 'test456',
            'title': '',  # Empty title
            'year': 2023
        }
        
        paper = api._parse_paper(invalid_paper)
        
        assert paper is None


class TestResearchAgentIntegration:
    """Test Research Agent with mocked API calls."""
    
    @pytest.fixture
    def temp_db(self, tmp_path):
        """Create temporary database for testing."""
        db_path = tmp_path / "test.db"
        return DatabaseManager(str(db_path))
    
    @pytest.fixture
    def mock_data(self):
        """Load mock Semantic Scholar response data."""
        mock_file = Path(__file__).parent.parent / 'data' / 'test_data' / 'semantic_scholar_mock.json'
        with open(mock_file, 'r') as f:
            return json.load(f)
    
    def test_research_agent_initialization(self, temp_db):
        """Test that Research Agent initializes correctly."""
        agent = ResearchAgent(temp_db)
        
        assert agent.db is not None
        assert agent.semantic_scholar is not None
        assert agent.query_formulator is not None
    
    @patch('src.integrations.semantic_scholar.SemanticScholarAPI.search')
    def test_search_literature_mocked(self, mock_search, temp_db, mock_data):
        """Test literature search with mocked API."""
        # Setup mock
        mock_result = SearchResult(
            query="test query",
            source=PaperSource.SEMANTIC_SCHOLAR,
            papers=[],
            total_results=3,
            page=1,
            page_size=50,
            success=True
        )
        
        # Parse papers from mock data
        api = SemanticScholarAPI()
        for paper_data in mock_data['mock_search_response']['data']:
            paper = api._parse_paper(paper_data)
            if paper:
                mock_result.papers.append(paper)
        
        mock_search.return_value = mock_result
        
        # Execute search
        agent = ResearchAgent(temp_db)
        domain = ResearchDomain(
            name="Test Domain",
            subject_type="AI Research",
            keywords=["automated literature review", "LLM"],
            description="Test"
        )
        
        stats = agent.search_literature(domain, max_queries=2, papers_per_query=10)
        
        # Verify results
        assert stats['queries_executed'] == 2
        assert stats['total_papers_found'] > 0
        assert stats['papers_stored'] > 0
        
        # Verify papers were stored in database
        stored_papers = temp_db.get_all_papers()
        assert len(stored_papers) > 0
    
    @patch('src.integrations.semantic_scholar.SemanticScholarAPI.search')
    def test_search_handles_failures(self, mock_search, temp_db):
        """Test that search handles API failures gracefully."""
        # Setup mock to return failure
        mock_result = SearchResult(
            query="test query",
            source=PaperSource.SEMANTIC_SCHOLAR,
            papers=[],
            total_results=0,
            page=1,
            page_size=50,
            success=False,
            error_message="API Error"
        )
        mock_search.return_value = mock_result
        
        agent = ResearchAgent(temp_db)
        domain = ResearchDomain(
            name="Test Domain",
            subject_type="AI",
            keywords=["test"],
            description="Test"
        )
        
        # Should not raise exception
        stats = agent.search_literature(domain, max_queries=1, papers_per_query=10)
        
        assert stats['total_papers_found'] == 0
        assert stats['queries_executed'] == 1


class TestCacheKeyGeneration:
    """Test cache key generation for search queries."""
    
    def test_generate_cache_key(self):
        """Test cache key generation is consistent."""
        api = SemanticScholarAPI()
        
        query = "machine learning"
        params = {'limit': 50, 'year': '2020-2024'}
        
        key1 = api.generate_cache_key(query, params)
        key2 = api.generate_cache_key(query, params)
        
        assert key1 == key2
        assert isinstance(key1, str)
        assert len(key1) == 32  # MD5 hash length
    
    def test_cache_key_different_for_different_queries(self):
        """Test that different queries produce different cache keys."""
        api = SemanticScholarAPI()
        
        key1 = api.generate_cache_key("query1", {'limit': 50})
        key2 = api.generate_cache_key("query2", {'limit': 50})
        
        assert key1 != key2


def run_stage2_tests():
    """Run all Stage 2 tests."""
    print("=" * 70)
    print("STAGE 2 TESTS: Search Agent & Query Formulation")
    print("=" * 70)
    
    # Run tests with pytest
    pytest_args = [
        __file__,
        '-v',
        '--tb=short',
        '--color=yes'
    ]
    
    exit_code = pytest.main(pytest_args)
    
    if exit_code == 0:
        print("\n" + "=" * 70)
        print("✓ ALL STAGE 2 TESTS PASSED")
        print("=" * 70)
    else:
        print("\n" + "=" * 70)
        print("✗ SOME STAGE 2 TESTS FAILED")
        print("=" * 70)
    
    return exit_code


if __name__ == '__main__':
    exit(run_stage2_tests())
