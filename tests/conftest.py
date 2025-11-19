"""
Pytest configuration and shared fixtures.

This file:
1. Handles path imports so tests can find src/ modules
2. Provides shared fixtures for all tests
3. Configures pytest behavior
"""

import sys
import pytest
from pathlib import Path

# Add src to path for all tests
# This makes `from src.core.models import ...` work correctly
project_root = Path(__file__).parent.parent
src_path = project_root / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path.parent))


# ============================================================================
# PYTEST CONFIGURATION
# ============================================================================

def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "asyncio: mark test as async"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as integration test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )


# ============================================================================
# SHARED FIXTURES
# ============================================================================

@pytest.fixture
def project_root():
    """Get project root directory."""
    return Path(__file__).parent.parent


@pytest.fixture
def data_dir():
    """Get test data directory."""
    return Path(__file__).parent.parent / "data" / "test_data"


@pytest.fixture(scope="session")
def test_config():
    """Get test configuration."""
    return {
        "test_db_name": "test_literature_review.db",
        "temp_dir": "test_temp",
    }


# ============================================================================
# CLEANUP HOOKS
# ============================================================================

@pytest.fixture(autouse=True)
def reset_logging():
    """Reset logging between tests to avoid interference."""
    import logging
    # Clear all handlers from root logger
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
    yield
    # Cleanup after test
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
