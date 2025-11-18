# AI-Driven Literature Review System

A modular, production-ready system for automated PhD literature review with pluggable LLM providers.

## 🏗️ Project Structure

```
literature_review_system/
├── config/
│   ├── config.yaml           # Main configuration
│   └── llm_providers.yaml    # LLM provider settings
├── src/
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py         # Configuration management
│   │   ├── llm_interface.py  # LLM abstraction layer
│   │   ├── base_agent.py     # Base agent class
│   │   ├── models.py         # Pydantic data models
│   │   └── database.py       # SQLite persistence layer
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── research_agent.py # Query formulation
│   │   ├── quality_agent.py  # Filtering & validation
│   │   ├── acquisition_agent.py # PDF download
│   │   ├── summarizer_agent.py # LLM summarization
│   │   └── citation_agent.py # Bibliography generation
│   ├── integrations/
│   │   ├── __init__.py
│   │   ├── semantic_scholar.py
│   │   ├── crossref.py
│   │   └── arxiv.py
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── logger.py         # Logging system
│   │   ├── exceptions.py     # Custom exceptions
│   │   └── validators.py     # Data validation
│   └── main.py               # Entry point
├── tests/
│   ├── test_config.py
│   ├── test_llm_interface.py
│   └── test_connectivity.py
├── data/
│   ├── test_data/            # Mock data for testing
│   └── output/               # Generated outputs
├── requirements.txt
└── setup.py
```

## 🚀 Quick Start

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Configure your LLM providers:
```yaml
# config/llm_providers.yaml
providers:
  openai:
    api_key: "your-api-key"
    models:
      fast: "gpt-3.5-turbo"
      quality: "gpt-4"
  anthropic:
    api_key: "your-api-key"
    models:
      fast: "claude-3-haiku-20240307"
      quality: "claude-3-sonnet-20240229"
  local:
    base_url: "http://localhost:11434"
    models:
      fast: "llama3-8b"
      quality: "llama3-70b"
```

3. Run a test:
```bash
python -m tests.test_connectivity
```

## 🔧 LLM Provider Flexibility

The system supports multiple LLM providers that you can assign to different tasks:

- **OpenAI**: GPT-3.5, GPT-4, GPT-4-turbo
- **Anthropic**: Claude 3 Haiku, Sonnet, Opus
- **Google**: Gemini Pro, Gemini Ultra
- **Local Models**: Via Ollama or custom endpoints
- **Custom**: Any OpenAI-compatible API

## 🎯 Publication Strategy

**Paper 1 (This project - 6-8 months)**
- Focus: **Automated literature review methodology using LLMs**
- Subject: The framework itself with quality controls, cost optimization, human oversight
- Venues: PLOS ONE, Patterns, Scientific Data
- Demonstrates: Framework is production-ready, generalizable, reproducible

**Paper 2 (Future PhD work)**
- Focus: Application of the framework to irrigation scheduling
- Subject: AI-driven literature review for precision agriculture
- Venues: Agricultural journals
- Demonstrates: Framework works effectively in agriculture domain

## 📊 Stage-by-Stage Testing

Each stage is independently testable:

```bash
# Stage 1: Foundation + LLM Abstraction Layer
python -m tests.test_connectivity
python -m tests.test_config

# Stage 1.5: Data Models & Persistence
# (new in plan; validates models and DB init)
python -m tests.test_models
python -m tests.test_database

# Stage 2: Single Source Search (Semantic Scholar)
python -m tests.test_search_agent

# Stage 2.5: Minimal E2E Workflow (Search → Filter → Acquire → Summarize)
python -m tests.test_e2e_minimal

# Stage 3: Multi-Source Integration
python -m tests.test_multi_source_search
python -m tests.test_deduplication

# Stage 4: Quality Validation & Adaptive LLM Selection
python -m tests.test_quality_validation

# Stage 5: Full Text Summarization
python -m tests.test_summarization

# Stage 6: Citation & Formatting
python -m tests.test_citation_generation

# Stage 7: Output Generation
python -m tests.test_output_formats

# Stage 8: Production Scaling & Optimization
python -m tests.test_parallel_execution
python -m tests.test_end_to_end
```

## 🎯 Key Features

- **Pluggable LLM Architecture**: Use different models for different tasks (async-ready)
- **Data Persistence**: SQLite database with Pydantic models for Papers, Summaries, Citations
- **Input Validation**: Pydantic validators for API responses and internal data
- **Resilient API Calls**: Exponential backoff for transient failures
- **Multi-Source Search**: Semantic Scholar, CrossRef, arXiv (after minimal E2E validation)
- **Quality Control**: Deduplication, relevance scoring, output quality validation
- **Cost Optimization**: Dynamic model selection based on output quality
- **Minimal E2E First**: Validate single-paper workflow before scaling
- **Checkpoint System**: Resume from last successful stage
- **Academic Compliance**: Proper citation formatting, DOI validation, style enforcement

## 📈 Performance & Cost

Designed for budget-conscious researchers:

| Task | Recommended Model | Cost/1K tokens | Speed | Quality |
|------|-------------------|----------------|-------|---------|
| Query Formulation | Claude Haiku | $0.00025 | ⚡⚡⚡ | ⭐⭐⭐⭐ |
| Relevance Scoring | GPT-3.5 | $0.0005 | ⚡⚡ | ⭐⭐⭐ |
| Summarization | Claude Sonnet | $0.003 | ⚡ | ⭐⭐⭐⭐⭐ |
| Citation Validation | Local Model | Free | ⚡ | ⭐⭐⭐ |

## 🛡️ Quality Controls

- **Source Validation**: DOI verification, journal ranking, predatory journal filtering
- **Hallucination Prevention**: Low temperature, source grounding, self-critique
- **Citation Accuracy**: Multi-level verification, format validation, manual spot-checking
- **Human Review**: Configurable checkpoints for manual validation

## 📝 System Design

This system is the **automated literature review methodology itself**:

- **Core Focus**: 8-stage pipeline for automated literature review using LLMs
- **Quality Controls**: DOI validation, citation accuracy, hallucination detection, cost tracking
- **Configurable**: Users can adapt to any research domain by changing `research_domain` config
- **Production-Ready**: SQLite persistence, retry logic, structured logging, error handling
- **Open Source**: Published on GitHub for reproducibility and community use

**Paper 1** validates this framework works. **Paper 2** applies it to irrigation.

---

Built with academic rigor and production reliability in mind. Start testing each stage immediately!