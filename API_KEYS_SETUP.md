# API Keys Setup Guide

All API keys are passed as **environment variables**, NOT hardcoded in config files.

## How It Works

The `config/llm_providers.yaml` file references environment variables using `${VARIABLE_NAME}` syntax:

```yaml
openai:
  api_key: "${OPENAI_API_KEY}"  # Reads from environment variable

anthropic:
  api_key: "${ANTHROPIC_API_KEY}"  # Reads from environment variable

google:
  api_key: "${GOOGLE_API_KEY}"  # Reads from environment variable

custom:
  api_key: "${CUSTOM_LLM_API_KEY}"  # Reads from environment variable
```

The system automatically substitutes these with environment variable values at runtime.

---

## Setting Up Environment Variables

### Option 1: Command Line (Temporary - Session Only)

```bash
export OPENAI_API_KEY="sk-..."
export ANTHROPIC_API_KEY="sk-ant-..."
export GOOGLE_API_KEY="AIzaSyD..."

# Then run your code
python tests/test_connectivity.py
```

### Option 2: .env File (Recommended for Development)

Create a `.env` file in the project root:

```bash
# .env (NEVER commit this to Git)
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_API_KEY=AIzaSyD...
CUSTOM_LLM_URL=https://api.custom-llm.com
CUSTOM_LLM_API_KEY=custom-key-...
```

Then load it before running:

```bash
set -a
source .env
set +a
python stage1_demo.py
```

Or use a tool like `python-dotenv`:

```bash
pip install python-dotenv

# In your Python code:
from dotenv import load_dotenv
load_dotenv()  # Loads from .env automatically
```

### Option 3: Add to Shell Profile (Persistent)

Add to `~/.bashrc` or `~/.zshrc`:

```bash
export OPENAI_API_KEY="sk-..."
export ANTHROPIC_API_KEY="sk-ant-..."
export GOOGLE_API_KEY="AIzaSyD..."
```

Then reload:

```bash
source ~/.bashrc
```

---

## Which Keys Do You Need?

### For Paper 1 (Methodology - No actual API calls needed yet)

You **don't need real API keys** for:
- Unit tests (mock data)
- Configuration validation
- Database tests
- Code structure validation

### When You Need Keys

- **Stage 2+**: When actually calling search APIs (Semantic Scholar, CrossRef, arXiv)
- **Stage 5**: When actually calling LLM APIs for summarization

### Providers You Can Use

**Free/Cheap Options:**
- **Claude Haiku** (Anthropic): $0.00025 per 1K tokens — Best value
- **GPT-3.5 Turbo** (OpenAI): $0.0005 per 1K tokens
- **Gemini Flash** (Google): $0.000075 per 1K tokens — Cheapest
- **Local Models** (Ollama): Free after setup

---

## Getting API Keys

### OpenAI

1. Go to https://platform.openai.com/api-keys
2. Create new secret key
3. Copy key immediately (can't retrieve later)

```bash
export OPENAI_API_KEY="sk-..."
```

### Anthropic

1. Go to https://console.anthropic.com/keys
2. Create new API key
3. Copy key immediately

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

### Google (Gemini)

1. Go to https://aistudio.google.com/app/apikey
2. Create new API key
3. Copy key

```bash
export GOOGLE_API_KEY="AIzaSyD..."
```

### Local Models (Ollama)

No API key needed. Just run locally:

```bash
# Install Ollama: https://ollama.ai
ollama serve

# In another terminal:
ollama pull llama3:8b
```

---

## Safety Best Practices

### ✅ DO:
- Store keys in environment variables
- Use `.env` file for local development (add to `.gitignore`)
- Use secret managers for production (GitHub Secrets, AWS Secrets Manager, etc.)
- Rotate keys regularly

### ❌ DON'T:
- Commit API keys to Git
- Store keys in config files that get committed
- Share API keys in code or documentation
- Use same key for development and production

### .gitignore Entry

```bash
# Add to .gitignore to prevent accidental commits
.env
.env.local
.env.*.local
```

---

## Testing Without API Keys

For **Paper 1**, you can run tests without real API keys:

```bash
# This works without any API keys set
python tests/test_connectivity.py

# Output shows which providers are available
# If no keys set, most LLM tests are skipped
# But configuration, database, and model tests all pass
```

---

## Running the Code

### With Keys Set

```bash
# Terminal 1: Set environment variables
export OPENAI_API_KEY="sk-..."
export ANTHROPIC_API_KEY="sk-ant-..."

# Terminal 2: Run code (inherits environment)
source venv/bin/activate
python stage1_demo.py
```

### In Python Code

```python
from src.core.llm_interface import get_llm_manager

# Automatically reads from environment variables
llm_manager = get_llm_manager()

# Will only work if OPENAI_API_KEY is set
response = await llm_manager.generate_response(
    "Hello, world!",
    provider_name="openai"
)
```

---

## Troubleshooting

### Error: "Provider not initialized"

**Cause**: API key not set for that provider

**Solution**:
```bash
export PROVIDER_API_KEY="your-key"
# Then try again
```

### Error: "Authentication failed"

**Cause**: Invalid or expired API key

**Solution**:
1. Check key is correct at provider's dashboard
2. Regenerate key if expired
3. Set new key as environment variable

### Error: "Rate limit exceeded"

**Cause**: Too many API calls too quickly

**Solution**: System has exponential backoff built in—it will retry automatically

---

## For Paper 1 Submission

**You don't need to include API keys in the submission.**

The paper's supplementary materials should include:
- Example config file (with `${VARIABLE_NAME}` placeholders)
- Instructions on how to set environment variables
- README with setup guide (like this file)

Reviewers will set their own keys when they test your code.

---

## Summary

✅ **All API keys are environment variables**  
✅ **Safe from accidental commits**  
✅ **Easy to switch between providers**  
✅ **Works with local models (no keys needed)**  
✅ **Paper 1 doesn't need real keys** (can use mock data)  

**For now**: Don't worry about API keys. Focus on the paper. Keys only matter when you get to Stage 2+.
