# Search Architecture

## Overview

The search system is designed to **retrieve academic papers from multiple sources** in a unified way. It's currently in **Stage 2 of development** and planned but not yet implemented.

---

## How Search Will Work

### Stage 1: Query Formulation (Not Yet Implemented)

**Input**: Research topic from config  
**Process**: LLM generates multiple diverse search queries  
**Output**: 5-10 search queries covering different angles

```
Research Topic: "AI Literature Review Methodologies"
↓
LLM generates queries:
1. "automated literature review using large language models"
2. "LLM-based systematic review"
3. "AI systematic review automation"
4. "natural language processing literature synthesis"
5. "machine learning bibliography generation"
```

### Stage 2: Multi-Source Query Execution (To Be Implemented)

**Input**: 5-10 search queries  
**Process**: Execute queries against multiple APIs in parallel  
**Output**: Papers from all sources combined

```
Query: "automated literature review LLM"
    ├─→ Semantic Scholar API  → 45 papers
    ├─→ CrossRef API          → 32 papers
    └─→ arXiv API             → 18 papers
    
Total: 95 papers (before deduplication)
```

### Stage 3: Deduplication (To Be Implemented)

**Input**: 95 papers from all sources  
**Process**: Identify duplicates (same paper from multiple sources)  
**Output**: 60-70 unique papers

```
Same paper from multiple sources:
"Machine Learning for Citation Analysis"
  - Found in: Semantic Scholar + CrossRef + arXiv
  - Keep 1 copy, note all sources
```

### Stage 4: Filtering (To Be Implemented)

**Input**: 60-70 unique papers  
**Process**: Apply quality filters  
**Output**: 30-40 papers that pass filters

```
Filters applied:
✓ Year range: 2015-2025
✓ Language: English only
✓ Peer-reviewed: Yes
✓ Min citations: 5
✓ NOT predatory journals
↓
Result: 35 papers that passed all filters
```

---

## API Sources (Currently Stubbed)

### 1. Semantic Scholar

**What it is**: AI-powered academic search engine  
**Coverage**: 200M+ papers across all fields  
**Speed**: Fast responses  
**Cost**: Free

**Integration file**: `src/integrations/semantic_scholar.py` (not yet implemented)

```python
# Planned API:
semantic_scholar = SemanticScholarAPI()

results = semantic_scholar.search(
    query="automated literature review",
    limit=50,
    year_min=2015,
    year_max=2025
)
# Returns: List[Paper] with metadata
```

### 2. CrossRef

**What it is**: Metadata registry for scholarly publications  
**Coverage**: 150M+ DOI records  
**Speed**: Moderate (more comprehensive metadata)  
**Cost**: Free

**Integration file**: `src/integrations/crossref.py` (not yet implemented)

```python
# Planned API:
crossref = CrossRefAPI()

results = crossref.search(
    query="LLM systematic review",
    limit=50,
    filters={"published": {"date-parts": [[2015]]}}
)
# Returns: List[Paper] with DOI, publisher info
```

### 3. arXiv

**What it is**: Preprint archive for CS, Physics, Math, etc.  
**Coverage**: 2M+ preprints  
**Speed**: Very fast  
**Cost**: Free

**Integration file**: `src/integrations/arxiv.py` (not yet implemented)

```python
# Planned API:
arxiv = ArXivAPI()

results = arxiv.search(
    query="artificial intelligence literature review",
    limit=50,
    categories=["cs.AI", "cs.CL"]  # Computer Science categories
)
# Returns: List[Paper] with preprint metadata
```

---

## Data Flow Diagram

```
Research Topic (from config)
    ↓
[Query Formulation Agent - LLM]
    ↓ Generates 5-10 diverse queries
    ↓
[Multi-Source Search Engine]
    ├─→ [Semantic Scholar API]  → Results
    ├─→ [CrossRef API]           → Results
    └─→ [arXiv API]              → Results
    ↓ Merge results
[Deduplication Engine]
    ↓ Match papers by DOI/URL
[Filtered Results Cache]
    ↓
[Quality Filtering Agent]
    ├─→ Apply year filters
    ├─→ Apply language filters
    ├─→ Apply peer-review filters
    ├─→ Apply citation count filters
    └─→ Apply predatory journal filters
    ↓
[Filtered Papers] → Stored in SQLite Database
```

---

## Key Classes (Currently Stubbed)

### SearchResult Model

```python
class SearchResult(BaseModel):
    query: str                          # Search query used
    source: PaperSource                 # Which API (semantic_scholar, crossref, arxiv)
    papers: List[Paper]                 # Papers found
    total_results: int                  # Total matches on server
    page: int                           # Current page
    page_size: int                      # Results per page
    executed_at: datetime               # When search was done
    execution_time_seconds: float       # How long it took
    success: bool                       # Did search succeed?
    error_message: Optional[str]        # Error if failed
    cached: bool                        # Was this from cache?
```

### Paper Model (Key Fields for Search)

```python
class Paper(BaseModel):
    id: str                             # Unique ID (DOI or generated)
    title: str                          # Paper title
    authors: List[str]                  # Author names
    abstract: Optional[str]             # Paper abstract
    doi: Optional[str]                  # Digital Object Identifier
    url: Optional[str]                  # Paper URL
    pdf_url: Optional[str]              # Direct PDF link (if available)
    year: int                           # Publication year
    journal: Optional[str]              # Journal name
    sources: List[PaperSource]          # Which APIs found this paper
    source_ids: Dict[str, str]          # IDs from each source
    citation_count: int                 # Citation count (if available)
    status: PaperStatus                 # Current processing status
```

---

## Search Workflow Example

### Input Configuration

```yaml
research_domain:
  name: "AI Literature Review Methodologies"
  keywords:
    - "automated literature review"
    - "large language models"
    - "systematic review"
    - "LLM hallucination"

search:
  year_min: 2015
  year_max: 2025
  max_papers_per_source: 50
  max_total_papers: 150
```

### Step 1: Query Formulation

```
Input: "AI Literature Review Methodologies"
       Keywords: [automated, LLM, systematic review, hallucination]

LLM generates 5 queries:
1. "automated literature review using large language models"
2. "LLM-based systematic review"
3. "hallucination prevention in AI literature synthesis"
4. "machine learning for bibliography generation"
5. "neural network literature summarization"
```

### Step 2: Parallel Search (Each runs independently)

**Query 1 on Semantic Scholar**:
```
URL: https://api.semanticscholar.org/graph/v1/paper/search
Parameters:
  query: "automated literature review using large language models"
  limit: 50
  year: 2015-2025

Response: 50 papers (max per query)
```

**Query 2 on CrossRef**:
```
URL: https://api.crossref.org/works
Parameters:
  query: "LLM-based systematic review"
  sort: date
  rows: 50

Response: 45 papers (fewer matches)
```

**Query 3 on arXiv**:
```
URL: http://arxiv.org/api/query
Parameters:
  search_query: "cat:cs.AI AND all:hallucination AND all:literature"
  max_results: 50

Response: 28 papers (limited to arXiv preprints)
```

### Step 3: Combine & Deduplicate

```
Semantic Scholar results: 50 papers
  + CrossRef results: 45 papers
  + arXiv results: 28 papers
  = 123 total papers

Deduplication (match by DOI or URL):
  - "Machine Learning for Citation Analysis" found in all 3
  - "LLM Bias in Literature Review" found in Semantic Scholar + CrossRef
  - 43 other unique papers
  
Result: ~95 unique papers
```

### Step 4: Filter

```
Starting with: 95 papers

Apply filters:
✓ Year 2015-2025: 89 papers remain
✓ English only: 87 papers remain
✓ Peer-reviewed: 71 papers remain
✓ Min 5 citations: 64 papers remain
✓ Not predatory: 62 papers remain

Final: 62 papers
(Stopped at max_total_papers: 150, so all kept)
```

### Step 5: Store in Database

```
INSERT INTO papers (id, title, authors, doi, ...) 
VALUES 
  ('paper_1', 'Automated Literature Review...', [...], ...),
  ('paper_2', 'LLM Hallucination Prevention...', [...], ...),
  ...
  ('paper_62', ...);

INSERT INTO cache (cache_key, data, expires_at)
  Key: hash("automated literature review" + source + date)
  TTL: 24 hours
```

---

## Caching Strategy

### Why Cache?

API calls are expensive (time + bandwidth). Cache prevents redundant calls for the same query.

### Cache Key

```python
cache_key = hashlib.sha256(
    f"{query}:{source}:{year_min}:{year_max}".encode()
).hexdigest()

# Example: abc123def456...
```

### Cache Duration

- **Semantic Scholar**: 24 hours (relatively stable)
- **CrossRef**: 24 hours (stable metadata)
- **arXiv**: 24 hours (new preprints daily, but search results stable)

### Cache Invalidation

```python
# Automatic cleanup
database.cleanup_expired_cache()  # Removes entries older than TTL

# Manual invalidation (if needed)
database.delete_cache("abc123def456")  # Remove specific entry
```

---

## Error Handling

### Common Errors

| Error | Cause | Recovery |
|-------|-------|----------|
| Network timeout | API slow or down | Retry with exponential backoff |
| Rate limit exceeded | Too many requests | Wait and retry |
| Invalid API key | Auth failed | Check environment variables |
| No results | Query too specific | Broaden query or try different source |
| Malformed response | API changed format | Log and continue with other sources |

### Retry Logic

```python
# Automatic retries with exponential backoff
@async_retry(max_retries=3, initial_delay=1.0, backoff_factor=2.0)
async def search_with_retry(query):
    # Attempt 1: Immediate
    # If fails...
    # Attempt 2: Wait 1 second, try again
    # If fails...
    # Attempt 3: Wait 2 seconds, try again
    # If fails...
    # Attempt 4: Wait 4 seconds, try again
    # If still fails, raise exception
```

---

## Current Status

### ✅ Ready
- SearchResult and Paper models
- Database schema for storing papers
- Cache system with TTL
- Retry logic with exponential backoff
- Configuration for search parameters

### ⏳ Not Yet Implemented (Stage 2)
- Semantic Scholar API integration
- CrossRef API integration
- arXiv API integration
- Query formulation agent
- Deduplication engine
- Filtering pipeline

### 📅 Timeline

For **Paper 1 (Methodology)**, the search implementation is NOT needed. We'll use:
- Mock/example paper data
- Demonstrate the framework's structure
- Show how it would work with real data

For **Paper 2 (Irrigation application)**, we'll implement:
- Stages 2-4 (search, deduplicate, filter)
- Real API integrations
- Actual paper discovery

---

## How to Test Search (When Implemented)

```python
from src.integrations import SemanticScholarAPI, CrossRefAPI, ArXivAPI
from src.core.config import get_config

config = get_config()
queries = [
    "automated literature review",
    "LLM systematic review",
    "AI bibliography"
]

# Search all sources
semantic_scholar = SemanticScholarAPI()
crossref = CrossRefAPI()
arxiv = ArXivAPI()

for query in queries:
    ss_results = semantic_scholar.search(query, limit=50)
    cr_results = crossref.search(query, limit=50)
    ax_results = arxiv.search(query, limit=50)
    
    print(f"Query '{query}':")
    print(f"  Semantic Scholar: {len(ss_results)} papers")
    print(f"  CrossRef: {len(cr_results)} papers")
    print(f"  arXiv: {len(ax_results)} papers")
```

---

## Summary

**Search Architecture:**
1. Formulate diverse queries from research topic
2. Execute queries in parallel against multiple APIs
3. Deduplicate results (same paper from multiple sources)
4. Filter by quality criteria (year, language, peer-review, citations)
5. Cache results to avoid redundant API calls
6. Store in database for further processing

**Current Status**: Models and infrastructure ready, API integrations pending Stage 2 implementation.

**For Paper 1**: Not needed yet—we'll demonstrate with example data.
