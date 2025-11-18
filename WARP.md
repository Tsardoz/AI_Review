# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Development Setup

### Virtual Environment
**CRITICAL**: Always activate the virtual environment before running Python code:
```bash
source venv/bin/activate
```

### Install Dependencies
```bash
pip install -r requirements.txt
```

### API Keys Configuration
API keys are loaded from environment variables via `python-dotenv`. See `API_KEYS_SETUP.md` for details.

Required environment variables:
- `OPENAI_API_KEY` (optional - for OpenAI models)
- `ANTHROPIC_API_KEY` (optional - for Claude models)
- `GOOGLE_API_KEY` (optional - for Gemini models)

Configuration files:
- `config/config.yaml` - Main system configuration
- `config/llm_providers.yaml` - LLM provider settings (uses `${ENV_VAR}` syntax)

## Testing

### Run All Tests
```bash
python -m pytest tests/ -v
```

### Run Specific Test File
```bash
python -m pytest tests/test_search_agent.py -v
python -m pytest tests/test_connectivity.py -v
```

### Run Tests with Coverage
```bash
python -m pytest tests/ --cov=src --cov-report=html
```

### Run Stage Demo Scripts
```bash
python stage1_demo.py  # LLM connectivity and config validation
python stage2_demo.py  # Semantic Scholar search integration
```

## Code Quality

### Linting
```bash
flake8 src/ tests/
```

### Formatting
```bash
black src/ tests/
```

## Architecture Overview

### Project Structure
This is an **8-stage modular pipeline** for automated academic literature review:

1. **Foundation + LLM Abstraction** (Stage 1) - Complete
2. **Single Source Search** (Stage 2) - Complete (Semantic Scholar)
3. **Multi-Source Integration** (Stage 3) - Planned (CrossRef, arXiv)
4. **Quality Validation** (Stage 4) - Planned
5. **Full Text Summarization** (Stage 5) - Planned
6. **Citation & Formatting** (Stage 6) - Planned
7. **Output Generation** (Stage 7) - Planned
8. **Production Scaling** (Stage 8) - Planned

### Core Abstractions

#### 1. Configuration System (`src/core/config.py`)
- Centralized configuration via YAML files
- `ResearchDomain` model makes the system **domain-agnostic**
- Change research topic by editing `config/config.yaml` without code changes

#### 2. LLM Provider Abstraction (`src/core/llm_interface.py`)
- Unified interface for OpenAI, Anthropic, Google, and local models
- **Two-tier model selection**: `fast` (cost-effective) and `quality` (high accuracy)
- Automatic rate limiting, retry logic, and cost tracking
- Task-to-model mapping in config (e.g., summarization uses "quality", filtering uses "fast")

#### 3. Data Models (`src/core/models.py`)
All entities use **Pydantic models** with validation:
- `Paper` - Core paper entity with metadata, processing status, quality scores
- `SearchResult` - API search results with caching info
- `Summary` - LLM-generated summaries with quality metrics
- `Citation` - Formatted citations (BibTeX, APA, etc.)
- `ProcessingCheckpoint` - For resumable workflows

#### 4. Database Persistence (`src/core/database.py`)
- SQLite database with context manager pattern
- CRUD operations for Papers, Summaries, Citations
- Caching layer for API responses
- Checkpoint system for workflow resumption

#### 5. Agent Architecture (`src/core/base_agent.py`)
All agents inherit from `BaseAgent` which provides:
- Configuration access via `self.config`
- Structured logging via `self.logger`
- Progress tracking and status management
- Task execution with error handling (`execute_with_error_handling()`)

Current agents:
- `ResearchAgent` (`src/agents/research_agent.py`) - Query formulation and paper search

#### 6. API Integrations (`src/integrations/`)
- `semantic_scholar.py` - **Complete** (rate limiting, retry logic, metadata parsing)
- `crossref.py` - Stub (Stage 3)
- `arxiv.py` - Stub (Stage 3)

#### 7. Utilities (`src/utils/`)
- `logger.py` - Structured JSON logging with task tracking
- `retry.py` - Exponential backoff decorator for API calls
- `exceptions.py` - Custom exception hierarchy

## Important Patterns

### Error Handling
- Use custom exceptions from `src/utils/exceptions.py`
- All API calls wrapped with `@retry` decorator
- Agents use `execute_with_error_handling()` for comprehensive error tracking

### Database Interactions
Always use context manager for database connections:
```python
from src.core.database import DatabaseManager

db = DatabaseManager()
with db.get_connection() as conn:
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM papers")
    results = cursor.fetchall()
```

### LLM Calls
Use the abstraction layer, not direct API calls:
```python
from src.core.config import get_config
from src.core.llm_interface import get_llm_provider, LLMMessage, MessageRole

config = get_config()
provider = get_llm_provider("fast")  # or "quality"

messages = [
    LLMMessage(role=MessageRole.SYSTEM, content="You are a research assistant"),
    LLMMessage(role=MessageRole.USER, content="Summarize this paper...")
]

response = await provider.generate_response(messages, task_name="summarization")
print(response.content, response.cost)
```

### Adding New Agents
1. Inherit from `BaseAgent`
2. Implement required abstract methods
3. Use `self.logger` for logging
4. Use `self.config` for configuration access
5. Register in `src/agents/__init__.py`

## Research Domain Configuration

The system is **domain-agnostic**. To adapt to a new research field:

1. Edit `config/config.yaml`:
```yaml
research_domain:
  name: "Your Research Domain"
  subject_type: "Academic Field"
  keywords:
    - "keyword1"
    - "keyword2"
  target_journals:
    - "Target Journal 1"
```

2. No code changes required - the entire pipeline adapts automatically

Current configuration focuses on **AI Literature Review Methodologies** (for Paper 1: the methodology itself).

## Current Project Status

**Stage 1**: ✅ Complete (LLM abstraction, config, database, models)
**Stage 2**: ✅ Complete (Semantic Scholar integration, query formulation)
**Stage 2.5**: 🔄 Next (Minimal end-to-end: search → filter → acquire → summarize for 1-5 papers)

See `PROJECT_STATUS.md`, `STAGE2_COMPLETION.md`, and `SEARCH_ARCHITECTURE.md` for detailed progress.

## Key Design Decisions

### Why SQLite?
- Portability and simplicity
- No external database server required
- Sufficient for research-scale data (thousands of papers)
- Easy to version control schema

### Why Pydantic Models?
- Built-in validation prevents corrupt data
- Automatic serialization/deserialization
- Clear data contracts between components
- IDE autocomplete support

### Why Multi-Provider LLM Support?
- Cost optimization (use cheaper models for simple tasks)
- Flexibility (researchers may not have access to all providers)
- Resilience (fallback if one provider is unavailable)
- Benchmarking (compare quality across providers)

### Why Stage-by-Stage Testing?
- Validate each component before building on it
- Catch issues early in development
- Enable incremental paper writing
- Demonstrate reproducibility to reviewers

## Common Tasks

### Add a New API Integration
1. Create file in `src/integrations/` (e.g., `new_api.py`)
2. Implement API client with rate limiting and retry logic
3. Return `List[Paper]` from search methods
4. Add tests in `tests/test_new_api.py`
5. Update `ResearchAgent` to use new source

### Add a New Test
Tests use pytest with fixtures. See `tests/test_search_agent.py` for examples:
```python
import pytest
from src.core.models import Paper

def test_paper_validation():
    paper = Paper(
        id="test_id",
        title="Test Paper",
        year=2023
    )
    assert paper.id == "test_id"
```

### Debug LLM Calls
Enable verbose logging:
1. Edit `config/config.yaml`:
```yaml
logging:
  level: "DEBUG"
```
2. Check logs in `data/system.log`
3. Look for `llm.*` logger entries showing token usage and costs

### Resume from Checkpoint
The system automatically saves checkpoints. To resume:
```python
from src.core.database import DatabaseManager

db = DatabaseManager()
checkpoint = db.get_latest_checkpoint("summarization")
if checkpoint and checkpoint.status != "completed":
    # Resume from checkpoint
    papers = db.get_papers_by_status("acquired")
```

## Publication Context

This codebase is designed for **academic publication**. Key considerations:

- **Paper 1**: The methodology framework itself (AI literature review automation)
- **Paper 2**: Application to irrigation scheduling (future work)
- Target venues: PLOS ONE, Patterns, Scientific Data
- Emphasis on reproducibility, configurability, and quality control

When making changes, consider:
- Will this be clear to academic reviewers?
- Is this reproducible by other researchers?
- Does this maintain scientific rigor?

See `PAPER_PUBLISHING_GUIDE.md` for detailed publication strategy.

## Codebase Conventions

- Python 3.10+ required
- Use type hints for all function signatures
- Docstrings for all public methods (Google style)
- Max line length: 100 characters (for Black formatter)
- Test files mirror source structure (`src/core/foo.py` → `tests/test_foo.py`)
- Database migrations: Handled by `_initialize_db()` in `database.py`

## File Naming

- Configuration: `*.yaml` (not `*.yml`)
- Test data: `data/test_data/*.json`
- Logs: `data/*.log`
- Databases: `data/*.db` (gitignored)
- Demo scripts: `stage{N}_demo.py`

## Troubleshooting

### "ModuleNotFoundError"
Ensure virtual environment is activated: `source venv/bin/activate`

### "Database is locked"
SQLite has one writer at a time. Check for:
- Long-running transactions
- Unclosed connections
- Multiple processes accessing the database

### "Rate limit exceeded"
API integrations have built-in rate limiting. If errors persist:
- Check `config/llm_providers.yaml` rate limits
- Verify API key has sufficient quota
- Use exponential backoff (already implemented in `@retry`)

### Tests failing with "KeyError"
Likely missing environment variable. Check:
1. `.env` file exists
2. Required API keys are set
3. `config/llm_providers.yaml` references correct env vars

## Git Workflow

Ignored files (see `.gitignore`):
- `*.db`, `*.sqlite` - Database files
- `venv/` - Virtual environment
- `.env` - API keys and secrets
- `*.log` - Log files
- `__pycache__/`, `*.pyc` - Python cache
- `data/cache/`, `data/processed/` - Generated data

Commit meaningful, atomic changes with descriptive messages following the existing pattern.
