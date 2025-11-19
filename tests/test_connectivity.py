"""
Connectivity and basic functionality tests (pytest style with mocks).

Tests core components independently to ensure they work before
building more complex functionality.

REFACTORED: Converted from unittest to pytest, added LLM mocks.
"""

import pytest
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock

from src.core.config import get_config, ConfigManager
from src.utils.logger import get_logger
from src.core.llm_interface import get_llm_manager, LLMMessage, MessageRole
from src.core.base_agent import BaseAgent, TaskResult
from src.core.models import Paper, PaperStatus, PaperSource
from src.utils.retry import retry, async_retry, RetryConfig
from tests.mocks.mock_llm import MockLLMProvider, MockLLMManager


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def config():
    """Get configuration instance."""
    return get_config()


@pytest.fixture
def logger():
    """Get logger instance."""
    return get_logger("test")


@pytest.fixture
def mock_llm_provider():
    """Get mock LLM provider."""
    return MockLLMProvider()


@pytest.fixture
def mock_llm_manager():
    """Get mock LLM manager."""
    return MockLLMManager()


# ============================================================================
# CONFIGURATION TESTS
# ============================================================================

class TestConfiguration:
    """Test configuration management."""
    
    def test_config_loading(self, config):
        """Test that configuration files load correctly."""
        assert config is not None
        assert isinstance(config, ConfigManager)
    
    def test_project_config(self, config):
        """Test project-specific configuration."""
        topic = config.get('project.topic')
        # Project now focuses on AI literature review methodology
        assert 'literature review' in topic.lower()
        
        output_dir = config.get('project.output_dir')
        assert output_dir is not None
    
    def test_research_domain_config(self, config):
        """Test new research_domain configuration is present and populated."""
        subject_type = config.get('research_domain.subject_type')
        assert isinstance(subject_type, str)
        assert len(subject_type) > 0
        
        keywords = config.get('research_domain.keywords')
        assert isinstance(keywords, list)
        
        # Test has keyword for AI literature review (or irrigation from case_study)
        all_keywords = keywords + config.get('research_domain.case_study.keywords', [])
        assert any(k in all_keywords for k in ['automated literature review', 'irrigation']), \
            "Must have literature review or irrigation keywords"
    
    def test_search_config(self, config):
        """Test search configuration."""
        year_min = config.get('search.year_min')
        assert year_min == 2015
        
        year_max = config.get('search.year_max')
        assert year_max == 2025
        
        sources = config.get('search.sources')
        assert 'semantic_scholar' in sources
        assert 'crossref' in sources
        assert 'arxiv' in sources
    
    def test_llm_assignments(self, config):
        """Test LLM task assignments."""
        query_model = config.get_model_for_task('query_formulation')
        assert query_model is not None
        
        summary_model = config.get_model_for_task('summarization')
        assert summary_model is not None
        
        citation_model = config.get_model_for_task('citation_validation')
        assert citation_model is not None
    
    def test_llm_providers(self, config):
        """Test LLM provider configuration."""
        providers = config.list_available_providers()
        assert len(providers) > 0
        
        # Test that at least one provider is configured
        provider_names = list(providers.keys())
        assert len(provider_names) > 0
        
        # Test provider structure
        for name, provider in providers.items():
            assert provider.name is not None
            assert provider.base_url is not None
            assert 'models' in provider.__dict__
            assert 'pricing' in provider.__dict__
    
    def test_config_validation(self, config):
        """Test configuration validation."""
        validation_result = config.validate_config()
        assert isinstance(validation_result, dict)
        assert 'valid' in validation_result
        assert 'issues' in validation_result
        assert 'warnings' in validation_result


# ============================================================================
# LOGGING TESTS
# ============================================================================

class TestLogging:
    """Test logging system."""
    
    def test_logger_creation(self, logger):
        """Test logger creation."""
        assert logger is not None
        logger.info("Test log message")
    
    def test_task_logger(self, logger):
        """Test task-specific logging."""
        task_logger = logger.create_task_logger("test_task_123", "Test Task")
        assert task_logger is not None
        task_logger.info("Task-specific log message")
    
    def test_log_levels(self, logger):
        """Test different log levels."""
        logger.debug("Debug message")
        logger.info("Info message")
        logger.warning("Warning message")
        logger.error("Error message")
        logger.critical("Critical message")
    
    def test_structured_logging(self, logger):
        """Test structured logging with extra fields."""
        logger.info(
            "LLM test call",
            provider="test_provider",
            model="test_model",
            tokens_used=100,
            cost=0.01
        )
        
        logger.log_search_query(
            source="test_source",
            query="test query",
            results_count=5
        )
        
        logger.log_paper_processed(
            paper_id="test_123",
            title="Test Paper Title",
            status="processed"
        )


# ============================================================================
# LLM INTERFACE TESTS (WITH MOCKS - NO API KEYS NEEDED)
# ============================================================================

class TestLLMInterface:
    """Test LLM interface and manager."""
    
    def test_llm_manager_creation(self):
        """Test LLM manager initialization."""
        llm_manager = get_llm_manager()
        assert llm_manager is not None
        
        stats = llm_manager.get_usage_statistics()
        assert isinstance(stats, dict)
        assert 'total_cost' in stats
        assert 'total_tokens' in stats
        assert 'available_providers' in stats
    
    def test_provider_availability(self):
        """Test that LLM providers are available."""
        llm_manager = get_llm_manager()
        stats = llm_manager.get_usage_statistics()
        available_providers = stats['available_providers']
        
        # Note: This test may fail if no LLM providers are configured
        # The system is designed to work without installed LLM libraries initially
        if len(available_providers) == 0:
            pytest.skip("No LLM providers configured (libraries not installed)")
        
        # Test getting a provider
        provider = llm_manager.get_provider()
        assert provider is not None
    
    def test_message_creation(self):
        """Test LLM message creation."""
        message = LLMMessage(MessageRole.USER, "Test message")
        assert message.role == MessageRole.USER
        assert message.content == "Test message"
        
        system_message = LLMMessage(MessageRole.SYSTEM, "You are a helpful assistant")
        assert system_message.role == MessageRole.SYSTEM
    
    @pytest.mark.asyncio
    async def test_mock_llm_generation(self, mock_llm_provider):
        """Test LLM generation pipeline using mock (NO API keys needed)."""
        # Configure mock response
        mock_llm_provider.set_response_for_task("test_task", "Mock LLM response")
        
        # Create messages
        messages = [
            {"role": "user", "content": "Test prompt"}
        ]
        
        # Generate response
        response = await mock_llm_provider.generate_response(
            messages, 
            task_name="test_task"
        )
        
        # Assertions
        assert response.content == "Mock LLM response"
        assert response.tokens_used > 0
        assert response.cost > 0
        assert mock_llm_provider.get_call_count() == 1
    
    @pytest.mark.asyncio
    async def test_mock_llm_failure_simulation(self, mock_llm_provider):
        """Test LLM error handling using mock failures."""
        # Configure mock to fail
        mock_llm_provider.configure_failure(
            should_fail=True, 
            message="Rate limit exceeded"
        )
        
        messages = [{"role": "user", "content": "Test"}]
        
        # Should raise exception
        with pytest.raises(Exception, match="Rate limit exceeded"):
            await mock_llm_provider.generate_response(messages, "test")
    
    @pytest.mark.asyncio
    async def test_mock_llm_manager_tiers(self, mock_llm_manager):
        """Test LLM manager tier selection with mocks."""
        # Test fast tier
        response_fast = await mock_llm_manager.generate_response(
            messages=[{"role": "user", "content": "Quick task"}],
            task_name="filtering",
            tier="fast"
        )
        
        # Test quality tier
        response_quality = await mock_llm_manager.generate_response(
            messages=[{"role": "user", "content": "Important task"}],
            task_name="summarization",
            tier="quality"
        )
        
        # Verify calls were tracked
        stats = mock_llm_manager.get_usage_statistics()
        assert stats['calls_by_provider']['fast'] == 1
        assert stats['calls_by_provider']['quality'] == 1
        assert stats['total_tokens'] > 0
        assert stats['total_cost'] > 0
    
    @pytest.mark.asyncio
    async def test_llm_call_history_tracking(self, mock_llm_provider):
        """Test that mock provider tracks call history."""
        messages = [{"role": "user", "content": "First prompt"}]
        await mock_llm_provider.generate_response(messages, "task1")
        
        messages = [{"role": "user", "content": "Second prompt"}]
        await mock_llm_provider.generate_response(messages, "task2")
        
        # Verify history
        assert mock_llm_provider.get_call_count() == 2
        assert len(mock_llm_provider.calls_history) == 2
        assert mock_llm_provider.calls_history[0]['task_name'] == "task1"
        assert mock_llm_provider.calls_history[1]['task_name'] == "task2"


# ============================================================================
# BASE AGENT TESTS
# ============================================================================

class TestBaseAgent:
    """Test base agent functionality."""
    
    @pytest.fixture
    def test_agent(self):
        """Create a test agent."""
        class TestAgent(BaseAgent):
            def run(self, *args, **kwargs) -> TaskResult:
                def test_task():
                    return {"test": "data"}
                
                return self.execute_with_error_handling(
                    "test_task",
                    test_task
                )
        
        return TestAgent("test_agent", "A test agent")
    
    def test_agent_creation(self, test_agent):
        """Test agent creation."""
        assert test_agent is not None
        assert test_agent.name == "test_agent"
        assert test_agent.description == "A test agent"
        assert test_agent.status.state == 'idle'
    
    def test_task_creation(self, test_agent):
        """Test task creation."""
        task_id = test_agent.create_task("test_task")
        assert task_id is not None
        assert test_agent.task_logger is not None
        assert test_agent.current_task_id == task_id
    
    def test_progress_tracking(self, test_agent):
        """Test progress tracking."""
        test_agent.update_progress(5, 10, "Processing items")
        assert test_agent.status.processed_items == 5
        assert test_agent.status.total_items == 10
        assert test_agent.status.progress == 0.5
    
    def test_status_management(self, test_agent):
        """Test status management."""
        test_agent.set_status('running', 'Test operation')
        assert test_agent.status.state == 'running'
        assert test_agent.status.current_task == 'Test operation'
        
        test_agent.set_status('completed')
        assert test_agent.status.state == 'completed'
    
    def test_execution(self, test_agent):
        """Test agent execution."""
        result = test_agent.run()
        assert isinstance(result, TaskResult)
        assert result.success
        assert result.data is not None
        assert result.execution_time > 0
    
    def test_status_summary(self, test_agent):
        """Test status summary generation."""
        summary = test_agent.get_status_summary()
        assert isinstance(summary, dict)
        assert 'agent_id' in summary
        assert 'name' in summary
        assert 'status' in summary
        assert 'performance' in summary


# ============================================================================
# RETRY LOGIC TESTS
# ============================================================================

class TestRetry:
    """Test retry decorator functionality."""
    
    def test_retry_success(self):
        """Test retry on successful operation."""
        call_count = 0
        
        @retry(max_retries=3)
        def successful_operation():
            nonlocal call_count
            call_count += 1
            return "success"
        
        result = successful_operation()
        assert result == "success"
        assert call_count == 1
    
    def test_retry_eventual_success(self):
        """Test retry on operation that eventually succeeds."""
        call_count = 0
        
        @retry(max_retries=3, initial_delay=0.1)
        def eventually_successful():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Not yet")
            return "success"
        
        result = eventually_successful()
        assert result == "success"
        assert call_count == 3
    
    def test_retry_exhaustion(self):
        """Test retry when max attempts exhausted."""
        call_count = 0
        
        @retry(max_retries=3, initial_delay=0.1)
        def always_fails():
            nonlocal call_count
            call_count += 1
            raise ValueError("Always fails")
        
        with pytest.raises(ValueError):
            always_fails()
        
        assert call_count == 4  # Initial + 3 retries
    
    @pytest.mark.asyncio
    async def test_async_retry_success(self):
        """Test async retry on successful operation."""
        call_count = 0
        
        @async_retry(max_retries=3)
        async def successful_async_operation():
            nonlocal call_count
            call_count += 1
            return "success"
        
        result = await successful_async_operation()
        assert result == "success"
        assert call_count == 1
    
    @pytest.mark.asyncio
    async def test_async_retry_eventual_success(self):
        """Test async retry on operation that eventually succeeds."""
        call_count = 0
        
        @async_retry(max_retries=3, initial_delay=0.1)
        async def eventually_successful_async():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Not yet")
            return "success"
        
        result = await eventually_successful_async()
        assert result == "success"
        assert call_count == 3


# ============================================================================
# DATA MODEL TESTS
# ============================================================================

class TestDataModels:
    """Test Pydantic data models."""
    
    def test_paper_creation(self):
        """Test Paper model creation and validation."""
        paper = Paper(
            id="test_123",
            title="Test Paper",
            year=2023,
            doi="10.1234/test.2023",
            status=PaperStatus.DISCOVERED,
            sources=[PaperSource.SEMANTIC_SCHOLAR]
        )
        
        assert paper.id == "test_123"
        assert paper.title == "Test Paper"
        assert paper.year == 2023
        assert paper.status == PaperStatus.DISCOVERED
    
    def test_paper_doi_validation(self):
        """Test DOI validation."""
        # Valid DOI
        paper = Paper(
            id="test_123",
            title="Test Paper Title",
            year=2023,
            doi="10.1234/test.2023"
        )
        assert paper.doi == "10.1234/test.2023"
        
        # Invalid DOI should raise error
        with pytest.raises(ValueError, match='DOI must start with "10."'):
            Paper(
                id="test_456",
                title="Test",
                year=2023,
                doi="invalid_doi"
            )
    
    def test_paper_url_validation(self):
        """Test URL validation."""
        # Valid URLs
        paper = Paper(
            id="test_123",
            title="Test Paper Title",
            year=2023,
            url="https://example.com",
            pdf_url="https://example.com/paper.pdf"
        )
        assert paper.url == "https://example.com"
        
        # Invalid URL should raise error
        with pytest.raises(ValueError, match="URL must start with http"):
            Paper(
                id="test_456",
                title="Test",
                year=2023,
                url="ftp://invalid.com"
            )
