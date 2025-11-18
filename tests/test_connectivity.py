"""
Connectivity and basic functionality tests for the literature review system.

Tests core components independently to ensure they work before
building more complex functionality.
"""

import os
import sys
import asyncio
import unittest
from pathlib import Path

# Add src to path for imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from src.core.config import get_config, reload_config, ConfigManager
from src.utils.logger import get_logger, setup_logging
from src.core.llm_interface import get_llm_manager, LLMMessage, MessageRole
from src.core.base_agent import BaseAgent, TaskResult, SequentialAgent
from src.core.models import Paper, PaperStatus, PaperSource, Summary, Citation, SearchResult
from src.core.database import get_db
from src.utils.retry import retry, async_retry, RetryConfig


class TestConfiguration(unittest.TestCase):
    """Test configuration management."""
    
    def setUp(self):
        self.config = get_config()
    
    def test_config_loading(self):
        """Test that configuration files load correctly."""
        self.assertIsNotNone(self.config)
        self.assertIsInstance(self.config, ConfigManager)
    
    def test_project_config(self):
        """Test project-specific configuration."""
        topic = self.config.get('project.topic')
        # Project now focuses on AI literature review methodology
        self.assertIn('literature review', topic.lower())
        
        output_dir = self.config.get('project.output_dir')
        self.assertIsNotNone(output_dir)
    
    def test_research_domain_config(self):
        """Test new research_domain configuration is present and populated."""
        subject_type = self.config.get('research_domain.subject_type')
        self.assertIsInstance(subject_type, str)
        self.assertGreater(len(subject_type), 0)
        
        keywords = self.config.get('research_domain.keywords')
        self.assertIsInstance(keywords, list)
        # Test has keyword for AI literature review (or irrigation from case_study)
        all_keywords = keywords + self.config.get('research_domain.case_study.keywords', [])
        self.assertTrue(
            any(k in all_keywords for k in ['automated literature review', 'irrigation']),
            "Must have literature review or irrigation keywords"
        )
    
    def test_search_config(self):
        """Test search configuration."""
        year_min = self.config.get('search.year_min')
        self.assertEqual(year_min, 2015)
        
        year_max = self.config.get('search.year_max')
        self.assertEqual(year_max, 2025)
        
        sources = self.config.get('search.sources')
        self.assertIn('semantic_scholar', sources)
        self.assertIn('crossref', sources)
        self.assertIn('arxiv', sources)
    
    def test_llm_assignments(self):
        """Test LLM task assignments."""
        query_model = self.config.get_model_for_task('query_formulation')
        self.assertIsNotNone(query_model)
        
        summary_model = self.config.get_model_for_task('summarization')
        self.assertIsNotNone(summary_model)
        
        citation_model = self.config.get_model_for_task('citation_validation')
        self.assertIsNotNone(citation_model)
    
    def test_llm_providers(self):
        """Test LLM provider configuration."""
        providers = self.config.list_available_providers()
        self.assertGreater(len(providers), 0)
        
        # Test that at least one provider is configured
        provider_names = list(providers.keys())
        self.assertGreater(len(provider_names), 0)
        
        # Test provider structure
        for name, provider in providers.items():
            self.assertIsNotNone(provider.name)
            self.assertIsNotNone(provider.base_url)
            self.assertIn('models', provider.__dict__)
            self.assertIn('pricing', provider.__dict__)
    
    def test_config_validation(self):
        """Test configuration validation."""
        validation_result = self.config.validate_config()
        self.assertIsInstance(validation_result, dict)
        self.assertIn('valid', validation_result)
        self.assertIn('issues', validation_result)
        self.assertIn('warnings', validation_result)


class TestLogging(unittest.TestCase):
    """Test logging system."""
    
    def setUp(self):
        self.logger = get_logger("test")
    
    def test_logger_creation(self):
        """Test logger creation."""
        self.assertIsNotNone(self.logger)
        self.logger.info("Test log message")
    
    def test_task_logger(self):
        """Test task-specific logging."""
        task_logger = self.logger.create_task_logger("test_task_123", "Test Task")
        self.assertIsNotNone(task_logger)
        task_logger.info("Task-specific log message")
    
    def test_log_levels(self):
        """Test different log levels."""
        self.logger.debug("Debug message")
        self.logger.info("Info message")
        self.logger.warning("Warning message")
        self.logger.error("Error message")
        self.logger.critical("Critical message")
    
    def test_structured_logging(self):
        """Test structured logging with extra fields."""
        self.logger.info(
            "LLM test call",
            provider="test_provider",
            model="test_model",
            tokens_used=100,
            cost=0.01
        )
        
        self.logger.log_search_query(
            source="test_source",
            query="test query",
            results_count=5
        )
        
        self.logger.log_paper_processed(
            paper_id="test_123",
            title="Test Paper Title",
            status="processed"
        )


class TestLLMInterface(unittest.TestCase):
    """Test LLM interface and manager."""
    
    def setUp(self):
        self.llm_manager = get_llm_manager()
    
    def test_llm_manager_creation(self):
        """Test LLM manager initialization."""
        self.assertIsNotNone(self.llm_manager)
        
        stats = self.llm_manager.get_usage_statistics()
        self.assertIsInstance(stats, dict)
        self.assertIn('total_cost', stats)
        self.assertIn('total_tokens', stats)
        self.assertIn('available_providers', stats)
    
    def test_provider_availability(self):
        """Test that LLM providers are available."""
        stats = self.llm_manager.get_usage_statistics()
        available_providers = stats['available_providers']
        
        # Note: This test may fail if no LLM providers are configured
        # The system is designed to work without installed LLM libraries initially
        if len(available_providers) == 0:
            self.skipTest("No LLM providers configured (libraries not installed)")
        
        # Test getting a provider
        provider = self.llm_manager.get_provider()
        self.assertIsNotNone(provider)
    
    def test_message_creation(self):
        """Test LLM message creation."""
        message = LLMMessage(MessageRole.USER, "Test message")
        self.assertEqual(message.role, MessageRole.USER)
        self.assertEqual(message.content, "Test message")
        
        system_message = LLMMessage(MessageRole.SYSTEM, "You are a helpful assistant")
        self.assertEqual(system_message.role, MessageRole.SYSTEM)
    
    @unittest.skip("Requires actual API keys")
    def test_provider_test(self):
        """Test provider connectivity (requires API keys)."""
        stats = self.llm_manager.get_usage_statistics()
        providers = stats['available_providers']
        
        for provider_name in providers:
            result = self.llm_manager.test_provider(provider_name)
            self.assertIsInstance(result, dict)
            self.assertIn('provider', result)
            self.assertIn('status', result)
            
            print(f"Provider {provider_name}: {result['status']}")
    
    @unittest.skip("Requires actual API keys")
    def test_simple_generation(self):
        """Test simple text generation (requires API keys)."""
        messages = [
            LLMMessage(MessageRole.USER, "Say 'Hello, World!'")
        ]
        
        async def test_generate():
            try:
                response = await self.llm_manager.generate_response(
                    messages,
                    task_type="query_formulation"
                )
                
                self.assertIsNotNone(response)
                self.assertIsInstance(response.content, str)
                self.assertGreater(len(response.content), 0)
                
                print(f"Generated response: {response.content}")
                print(f"Cost: ${response.cost:.6f}")
                print(f"Tokens: {response.tokens_used}")
                print(f"Time: {response.response_time:.2f}s")
                
            except Exception as e:
                print(f"Generation test failed: {str(e)}")
                raise
        
        # Run the async test
        asyncio.run(test_generate())


class TestBaseAgent(unittest.TestCase):
    """Test base agent functionality."""
    
    def setUp(self):
        class TestAgent(BaseAgent):
            def run(self, *args, **kwargs) -> TaskResult:
                def test_task():
                    return {"test": "data"}
                
                return self.execute_with_error_handling(
                    "test_task",
                    test_task
                )
        
        self.agent = TestAgent("test_agent", "A test agent")
    
    def test_agent_creation(self):
        """Test agent creation."""
        self.assertIsNotNone(self.agent)
        self.assertEqual(self.agent.name, "test_agent")
        self.assertEqual(self.agent.description, "A test agent")
        self.assertEqual(self.agent.status.state, 'idle')
    
    def test_task_creation(self):
        """Test task creation."""
        task_id = self.agent.create_task("test_task")
        self.assertIsNotNone(task_id)
        self.assertIsNotNone(self.agent.task_logger)
        self.assertEqual(self.agent.current_task_id, task_id)
    
    def test_progress_tracking(self):
        """Test progress tracking."""
        self.agent.update_progress(5, 10, "Processing items")
        self.assertEqual(self.agent.status.processed_items, 5)
        self.assertEqual(self.agent.status.total_items, 10)
        self.assertEqual(self.agent.status.progress, 0.5)
    
    def test_status_management(self):
        """Test status management."""
        self.agent.set_status('running', 'Test operation')
        self.assertEqual(self.agent.status.state, 'running')
        self.assertEqual(self.agent.status.current_task, 'Test operation')
        
        self.agent.set_status('completed')
        self.assertEqual(self.agent.status.state, 'completed')
    
    def test_execution(self):
        """Test agent execution."""
        result = self.agent.run()
        self.assertIsInstance(result, TaskResult)
        self.assertTrue(result.success)
        self.assertIsNotNone(result.data)
        self.assertGreater(result.execution_time, 0)
    
    def test_status_summary(self):
        """Test status summary generation."""
        summary = self.agent.get_status_summary()
        self.assertIsInstance(summary, dict)
        self.assertIn('agent_id', summary)
        self.assertIn('name', summary)
        self.assertIn('status', summary)
        self.assertIn('performance', summary)


class TestSequentialAgent(unittest.TestCase):
    """Test sequential agent functionality."""
    
    def setUp(self):
        self.agent = SequentialAgent("test_sequential", "Test sequential agent")
    
    def test_sequential_creation(self):
        """Test sequential agent creation."""
        self.assertIsNotNone(self.agent)
        self.assertEqual(len(self.agent.task_sequence), 0)
    
    def test_task_addition(self):
        """Test adding tasks to sequence."""
        def task1():
            return {"task1": "result1"}
        
        def task2():
            return {"task2": "result2"}
        
        self.agent.add_task("task1", task1)
        self.agent.add_task("task2", task2)
        
        self.assertEqual(len(self.agent.task_sequence), 2)
    
    def test_sequential_execution(self):
        """Test sequential task execution."""
        def task1():
            return {"task1": "result1"}
        
        def task2():
            return {"task2": "result2"}
        
        self.agent.add_task("task1", task1)
        self.agent.add_task("task2", task2)
        
        result = self.agent.run()
        self.assertTrue(result.success)
        self.assertIsNotNone(result.data)
        
        # Check individual task results
        task1_result = self.agent.get_task_result("task1")
        self.assertIsNotNone(task1_result)
        self.assertTrue(task1_result.success)
        
        task2_result = self.agent.get_task_result("task2")
        self.assertIsNotNone(task2_result)
        self.assertTrue(task2_result.success)


class TestModels(unittest.TestCase):
    """Test Pydantic data models."""
    
    def test_paper_creation(self):
        """Test Paper model creation and validation."""
        paper = Paper(
            id="test_paper_1",
            title="AI for Irrigation Scheduling",
            authors=["John Doe", "Jane Smith"],
            year=2023,
            doi="10.1234/test.2023",
            url="https://example.com/paper"
        )
        
        self.assertEqual(paper.id, "test_paper_1")
        self.assertEqual(paper.title, "AI for Irrigation Scheduling")
        self.assertEqual(len(paper.authors), 2)
        self.assertEqual(paper.status, PaperStatus.DISCOVERED)
    
    def test_paper_validation(self):
        """Test Paper model validation."""
        # DOI validation
        with self.assertRaises(ValueError):
            Paper(
                id="test",
                title="Test",
                year=2023,
                doi="invalid_doi"  # Should fail - must start with 10.
            )
        
        # URL validation
        with self.assertRaises(ValueError):
            Paper(
                id="test",
                title="Test",
                year=2023,
                url="invalid_url"  # Should fail - must start with http(s)
            )
    
    def test_summary_creation(self):
        """Test Summary model creation."""
        summary = Summary(
            paper_id="test_paper_1",
            abstract="This paper explores AI techniques for optimizing irrigation scheduling in orchards.",
            key_contributions=["Novel ML model", "Real-world validation"],
            llm_provider="anthropic",
            llm_model="claude-3-haiku",
            tokens_used=1500,
            cost_usd=0.000375
        )
        
        self.assertEqual(summary.paper_id, "test_paper_1")
        self.assertEqual(len(summary.key_contributions), 2)
        self.assertFalse(summary.manually_reviewed)
    
    def test_citation_creation(self):
        """Test Citation model creation."""
        citation = Citation(
            paper_id="test_paper_1",
            bibtex="@article{test2023, ...}",
            chicago_author_date="Doe, J., 2023"
        )
        
        self.assertEqual(citation.paper_id, "test_paper_1")
        self.assertFalse(citation.validated)


class TestDatabase(unittest.TestCase):
    """Test database operations."""
    
    def setUp(self):
        """Set up test database."""
        import tempfile
        self.temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.db = get_db()
        self.db.db_path = Path(self.temp_db.name)
        self.db._initialize_db()
    
    def tearDown(self):
        """Clean up test database."""
        import os
        os.unlink(self.temp_db.name)
    
    def test_database_initialization(self):
        """Test database is initialized correctly."""
        self.assertTrue(self.db.db_path.exists())
    
    def test_save_and_retrieve_paper(self):
        """Test saving and retrieving a paper."""
        paper = Paper(
            id="test_paper_db",
            title="Database Test Paper",
            authors=["Test Author"],
            year=2023
        )
        
        # Save paper
        result = self.db.save_paper(paper)
        self.assertTrue(result)
        
        # Retrieve paper
        retrieved = self.db.get_paper("test_paper_db")
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.title, "Database Test Paper")
        self.assertEqual(len(retrieved.authors), 1)
    
    def test_paper_count(self):
        """Test counting papers."""
        # Create and save test papers
        for i in range(5):
            paper = Paper(
                id=f"paper_{i}",
                title=f"Test Paper {i}",
                year=2023
            )
            self.db.save_paper(paper)
        
        count = self.db.count_papers()
        self.assertEqual(count, 5)
    
    def test_save_and_retrieve_summary(self):
        """Test saving and retrieving summaries."""
        # First save a paper
        paper = Paper(id="paper_with_summary", title="Test Paper", year=2023)
        self.db.save_paper(paper)
        
        # Save summary
        summary = Summary(
            paper_id="paper_with_summary",
            abstract="This is a test summary with more than fifty characters to pass validation.",
            llm_provider="test",
            llm_model="test-model"
        )
        result = self.db.save_summary(summary)
        self.assertTrue(result)
        
        # Retrieve summary
        retrieved = self.db.get_summary("paper_with_summary")
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.llm_provider, "test")


class TestRetry(unittest.TestCase):
    """Test retry logic."""
    
    def test_retry_config(self):
        """Test retry configuration."""
        config = RetryConfig(max_retries=5, initial_delay=0.1, backoff_factor=2.0)
        
        self.assertEqual(config.max_retries, 5)
        self.assertEqual(config.initial_delay, 0.1)
        
        # Test delay calculation
        delay_0 = config.get_delay(0)
        delay_1 = config.get_delay(1)
        self.assertGreater(delay_1, delay_0)
    
    def test_retry_decorator_success(self):
        """Test retry decorator with successful function."""
        call_count = [0]
        
        @retry(max_retries=3, initial_delay=0.1)
        def succeeds_immediately():
            call_count[0] += 1
            return "success"
        
        result = succeeds_immediately()
        self.assertEqual(result, "success")
        self.assertEqual(call_count[0], 1)
    
    def test_retry_decorator_eventual_success(self):
        """Test retry decorator with eventual success."""
        call_count = [0]
        
        @retry(max_retries=3, initial_delay=0.1)
        def fails_twice():
            call_count[0] += 1
            if call_count[0] < 3:
                raise ValueError("Not yet")
            return "success"
        
        result = fails_twice()
        self.assertEqual(result, "success")
        self.assertEqual(call_count[0], 3)
    
    def test_retry_decorator_max_retries(self):
        """Test retry decorator exhausts retries."""
        call_count = [0]
        
        @retry(max_retries=2, initial_delay=0.1)
        def always_fails():
            call_count[0] += 1
            raise ValueError("Always fails")
        
        with self.assertRaises(ValueError):
            always_fails()
        
        self.assertEqual(call_count[0], 3)  # Initial + 2 retries


def run_connectivity_tests():
    """Run all connectivity tests."""
    print("🚀 Running Literature Review System Connectivity Tests\n")
    
    # Create test suite
    test_suite = unittest.TestSuite()
    
    # Add test classes
    test_classes = [
        TestConfiguration,
        TestLogging,
        TestLLMInterface,
        TestBaseAgent,
        TestSequentialAgent,
        TestModels,
        TestDatabase,
        TestRetry
    ]
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        test_suite.addTests(tests)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # Print summary
    print(f"\n{'='*60}")
    print(f"TEST SUMMARY")
    print(f"{'='*60}")
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%")
    
    if result.failures:
        print(f"\nFAILURES:")
        for test, traceback in result.failures:
            error_msg = traceback.split('AssertionError: ')[-1].split('\n')[0]
            print(f"  - {test}: {error_msg}")
    
    if result.errors:
        print(f"\nERRORS:")
        for test, traceback in result.errors:
            error_msg = traceback.split('\n')[-2]
            print(f"  - {test}: {error_msg}")
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_connectivity_tests()
    sys.exit(0 if success else 1)