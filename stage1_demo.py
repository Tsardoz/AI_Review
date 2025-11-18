"""
Stage 1 Demo - Foundation + LLM Abstraction Layer

This demo showcases the core foundation components that are now fully functional:
- Configuration management with YAML files
- LLM provider abstraction (ready for any provider)
- Logging system with structured output
- Base agent framework with error handling
- Comprehensive testing framework

Run this script to verify Stage 1 is working correctly.
"""

import os
import sys
from pathlib import Path

# Add src to path for imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__)))
sys.path.insert(0, project_root)

from src.core.config import get_config, reload_config
from src.utils.logger import get_logger, setup_logging
from src.core.base_agent import BaseAgent, SequentialAgent, TaskResult
from src.core.llm_interface import get_llm_manager, LLMMessage, MessageRole


def demo_configuration():
    """Demonstrate configuration management."""
    print("🔧 Configuration Management Demo")
    print("=" * 50)
    
    config = get_config()
    
    # Show project configuration
    print(f"📚 Research Topic: {config.get('project.topic')}")
    print(f"📅 Year Range: {config.get('search.year_min')} - {config.get('search.year_max')}")
    print(f"🔍 Sources: {', '.join(config.get('search.sources'))}")
    print(f"📊 Max Papers: {config.get('search.max_total_papers')}")
    
    # Research domain (now configurable)
    print("\n🌐 Research Domain Configuration:")
    rd_name = config.get('research_domain.name', 'N/A')
    rd_subject = config.get('research_domain.subject_type', 'N/A')
    rd_keywords = config.get('research_domain.keywords', []) or []
    rd_journals = config.get('research_domain.target_journals', []) or []
    print(f"  Name: {rd_name}")
    print(f"  Subject Type: {rd_subject}")
    if rd_keywords:
        print(f"  Keywords: {', '.join(rd_keywords)}")
    if rd_journals:
        print(f"  Target Journals: {', '.join(rd_journals[:3])}")
    
    # Show LLM assignments
    print("\n🤖 LLM Task Assignments:")
    for task in ['query_formulation', 'relevance_scoring', 'summarization', 'citation_validation']:
        model = config.get_model_for_task(task)
        print(f"  {task}: {model}")
    
    # Validate configuration
    validation = config.validate_config()
    print(f"\n✅ Configuration Valid: {validation['valid']}")
    if validation['warnings']:
        print(f"⚠️  Warnings: {len(validation['warnings'])}")
        for warning in validation['warnings']:
            print(f"    - {warning}")
    
    print()


def demo_logging():
    """Demonstrate logging capabilities."""
    print("📝 Logging System Demo")
    print("=" * 50)
    
    logger = get_logger("demo")
    
    # Basic logging
    logger.info("System initialized")
    logger.warning("This is a warning message")
    logger.error("This is an error message")
    
    # Structured logging
    logger.log_llm_call(
        provider="anthropic",
        model="claude-3-haiku-20240307",
        tokens_used=1500,
        cost=0.000375,
        task="query_formulation"
    )
    
    logger.log_search_query(
        source="semantic_scholar",
        query="AI irrigation scheduling orchards",
        results_count=42
    )
    
    # Task-specific logging
    task_logger = logger.create_task_logger("task_123", "Process Paper #1")
    task_logger.info("Starting paper processing")
    task_logger.update_progress(1, 10, "Extracting metadata")
    task_logger.info("Paper processed successfully")
    
    print("✅ Logged messages to console and file")
    print("📄 Check './data/system.log' for structured JSON logs")
    print()


def demo_llm_interface():
    """Demonstrate LLM interface (without actual API calls)."""
    print("🤖 LLM Interface Demo")
    print("=" * 50)
    
    llm_manager = get_llm_manager()
    
    # Show usage statistics
    stats = llm_manager.get_usage_statistics()
    print(f"💰 Total Cost: ${stats['total_cost']:.6f}")
    print(f"🔢 Total Tokens: {stats['total_tokens']}")
    print(f"🔌 Available Providers: {len(stats['available_providers'])}")
    
    # Show provider configuration
    config = get_config()
    providers = config.list_available_providers()
    
    print("\n📋 Configured Providers:")
    for name, provider in providers.items():
        print(f"  {name}:")
        print(f"    Base URL: {provider.base_url}")
        print(f"    Models: {list(provider.models.keys())}")
        print(f"    Pricing: {provider.pricing}")
    
    # Create test messages
    messages = [
        LLMMessage(MessageRole.SYSTEM, "You are a helpful research assistant."),
        LLMMessage(MessageRole.USER, "Generate search queries for AI in orchard irrigation.")
    ]
    
    print(f"\n📨 Created {len(messages)} test messages")
    print("  System message: Configure AI assistant role")
    print("  User message: Task specification")
    
    # Note: Actual generation would require API keys
    print("\n🔒 API Key Configuration:")
    print("  Set environment variables for actual usage:")
    print("    export OPENAI_API_KEY='your-key'")
    print("    export ANTHROPIC_API_KEY='your-key'")
    print("    export GOOGLE_API_KEY='your-key'")
    
    print()


def demo_agent_framework():
    """Demonstrate agent framework."""
    print("🎭 Agent Framework Demo")
    print("=" * 50)
    
    # Create a simple test agent
    class DemoAgent(BaseAgent):
        def run(self, test_data: str) -> TaskResult:
            def process_data():
                # Simulate processing
                return {"processed": test_data.upper(), "status": "completed"}
            
            return self.execute_with_error_handling(
                "demo_processing",
                process_data
            )
    
    agent = DemoAgent("demo_agent", "Demonstration agent")
    
    print(f"📋 Agent Name: {agent.name}")
    print(f"📝 Description: {agent.description}")
    print(f"🆔 Agent ID: {agent.agent_id}")
    print(f"📊 Status: {agent.status.state}")
    
    # Execute agent
    print("\n🚀 Executing agent...")
    result = agent.run("test input data")
    
    print(f"✅ Success: {result.success}")
    print(f"📄 Result: {result.data}")
    print(f"⏱️  Execution Time: {result.execution_time:.4f}s")
    
    # Show status summary
    summary = agent.get_status_summary()
    print(f"\n📊 Performance Summary:")
    print(f"  Tasks Completed: {summary['performance']['total_tasks_completed']}")
    print(f"  Total Errors: {summary['performance']['total_errors']}")
    print(f"  Success Rate: {summary['performance']['success_rate']:.1%}")
    print()


def demo_sequential_agent():
    """Demonstrate sequential agent execution."""
    print("🔄 Sequential Agent Demo")
    print("=" * 50)
    
    # Create sequential agent
    agent = SequentialAgent("demo_sequential", "Multi-step demonstration")
    
    # Define processing steps
    def step1_fetch_data():
        return {"papers": ["paper1", "paper2", "paper3"]}
    
    def step2_filter_papers():
        return {"filtered": ["paper1", "paper3"]}
    
    def step3_process_papers():
        return {"processed": ["processed_paper1", "processed_paper3"]}
    
    # Add tasks to sequence
    agent.add_task("fetch_data", step1_fetch_data)
    agent.add_task("filter_papers", step2_filter_papers)
    agent.add_task("process_papers", step3_process_papers)
    
    print(f"📋 Created sequence with {len(agent.task_sequence)} tasks")
    for i, task in enumerate(agent.task_sequence, 1):
        print(f"  {i}. {task['name']}")
    
    # Execute sequence
    print("\n🚀 Executing sequence...")
    result = agent.run()
    
    print(f"✅ Sequence Success: {result.success}")
    if result.success:
        for task_name, task_result in result.data.items():
            print(f"  {task_name}: {task_result.data}")
    
    print()


def demo_output_directories():
    """Show the created directory structure."""
    print("📁 Project Structure Demo")
    print("=" * 50)
    
    directories = [
        "config",
        "src/core",
        "src/agents", 
        "src/integrations",
        "src/utils",
        "tests",
        "data/test_data",
        "data/output"
    ]
    
    print("📂 Created Directories:")
    for directory in directories:
        path = Path(directory)
        if path.exists():
            file_count = len([f for f in path.rglob("*") if f.is_file()])
            print(f"  ✅ {directory}/ ({file_count} files)")
        else:
            print(f"  ❌ {directory}/ (missing)")
    
    # Show key files
    key_files = [
        "config/config.yaml",
        "config/llm_providers.yaml", 
        "requirements.txt",
        "README.md",
        "tests/test_connectivity.py"
    ]
    
    print("\n📄 Key Files Created:")
    for file_path in key_files:
        path = Path(file_path)
        if path.exists():
            size = path.stat().st_size
            print(f"  ✅ {file_path} ({size:,} bytes)")
        else:
            print(f"  ❌ {file_path} (missing)")
    
    print()


def main():
    """Run all Stage 1 demonstrations."""
    print("🎯 Stage 1: Foundation + LLM Abstraction Layer")
    print("🚀 AI-Driven Literature Review System")
    print("=" * 60)
    print()
    
    try:
        demo_configuration()
        demo_logging()
        demo_llm_interface()
        demo_agent_framework()
        demo_sequential_agent()
        demo_output_directories()
        
        print("🎉 Stage 1 Demo Completed Successfully!")
        print("=" * 60)
        print()
        print("📋 What's Working in Stage 1:")
        print("  ✅ Configuration management with YAML")
        print("  ✅ Environment variable substitution")
        print("  ✅ Structured logging with file output")
        print("  ✅ Task-specific logging contexts")
        print("  ✅ LLM provider abstraction layer")
        print("  ✅ Base agent framework with error handling")
        print("  ✅ Sequential agent execution")
        print("  ✅ Comprehensive testing framework")
        print("  ✅ Project structure and documentation")
        print()
        print("🔧 Ready for Stage 2: Single Source Search")
        print("   - Semantic Scholar API integration")
        print("   - Query formulation system")
        print("   - Result storage and validation")
        print()
        print("💡 Next Steps:")
        print("   1. Install LLM provider libraries for actual API usage")
        print("   2. Set API keys as environment variables")
        print("   3. Run individual tests: python tests/test_connectivity.py")
        print("   4. Check logs: tail -f data/system.log")
        
    except Exception as e:
        print(f"❌ Demo failed: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()