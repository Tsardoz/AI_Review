# Stage 2.5: Two-Pass PDF Acquisition Workflow

## Overview

This stage implements a **PRISMA-compliant two-pass screening workflow** that ensures:
1. **Equality**: All papers judged on abstracts only (no Open Access bias)
2. **Copyright compliance**: Manual download via institutional access
3. **Operational efficiency**: Only acquire PDFs for shortlisted papers (50-150)

## Architecture: Three Phases

### Phase 1: Abstract-Based Screening (Automated)
**Input**: 500-1000 papers from search APIs (Semantic Scholar, CrossRef, arXiv)  
**Data Used**: Title + Abstract + Metadata only  
**Agent**: `QualityAgent` (future) or manual filtering  
**Output**: Shortlist of 50-150 papers marked as `AWAITING_PDF`  

**Key Principle**: Every paper is evaluated equally based on abstract content, eliminating bias toward Open Access papers.

---

### Phase 2: PDF Acquisition (Human-Assisted)

#### Step 2.1: Generate Acquisition List
```bash
python main.py --generate-acquisition-list
```

**What it does**:
- Queries database for papers with status `AWAITING_PDF`
- Exports `data/TO_ACQUIRE.csv` with:
  - Paper ID
  - Title
  - Authors
  - DOI and DOI URL (https://doi.org/...)
  - Publisher URL
  - **Suggested filename** for easy matching

**Example CSV row**:
```csv
paper_id,title,authors,year,journal,doi,doi_url,publisher_url,suggested_filename
abc123,"Deep Learning for Crops",Smith J; Wang L,2023,Nature,10.1038/s41586-023-12345,https://doi.org/10.1038/s41586-023-12345,https://nature.com/articles/...,10.1038_s41586-023-12345.pdf
```

#### Step 2.2: Manual Download via Institutional Access
1. Open `data/TO_ACQUIRE.csv` in Excel/LibreOffice
2. Use DOI URL to access papers through your university library proxy
3. Download PDFs and save them to `data/pdfs/`
4. **Critical**: Use the suggested filename from the CSV (e.g., `10.1038_s41586-023-12345.pdf`)
   - This enables automatic matching in Step 2.3

**Tips**:
- Most university libraries have browser extensions (e.g., LibKey) that auto-redirect DOI links
- Batch download 10-20 papers at a time to avoid triggering publisher rate limits
- If a paper is unavailable, document it and skip—the system will log unmatched files

#### Step 2.3: Ingest PDFs into System
```bash
python main.py --ingest-pdfs
```

**What it does**:
- Scans `data/pdfs/` for PDF files
- Matches filenames to database entries using three strategies:
  1. **DOI-based**: `10.1234_j.example.2023.pdf` → DOI `10.1234/j.example.2023`
  2. **Paper ID**: `paper_abc123.pdf` → Paper ID `abc123`
  3. **Exact ID**: `abc123.pdf` → Paper ID `abc123`
- Updates matched papers:
  - Sets `pdf_path` to absolute file path
  - Changes status from `AWAITING_PDF` → `PDF_ACQUIRED`
- Logs unmatched files for manual review

**Example Output**:
```
================================================================================
📥 PDF INGESTION COMPLETE
================================================================================
Total PDFs scanned: 147
✅ Successfully matched: 145
❌ Unmatched: 2
⚠️  Errors: 0

Unmatched files:
  - random_paper.pdf
  - backup_copy.pdf

Tip: Rename files to match DOI or paper ID from TO_ACQUIRE.csv
================================================================================
```

---

### Phase 3: Full-Text Synthesis (Automated)
**Input**: Papers with status `PDF_ACQUIRED`  
**Agent**: `SummarizerAgent` (Stage 5)  
**Process**:
1. Extract text from PDF (OCR if needed)
2. Use long-context LLM (Claude Opus, GPT-4 Turbo) to analyze full text
3. Generate structured summary with:
   - Key contributions
   - Methodology
   - Findings
   - Limitations
4. Update status: `PDF_ACQUIRED` → `TEXT_EXTRACTED` → `SYNTHESIZED`

---

## File Naming Best Practices

### Recommended: DOI-Based Naming
**Format**: Replace `/` in DOI with `_`  
**Example**:
- DOI: `10.1038/s41586-023-12345`
- Filename: `10.1038_s41586-023-12345.pdf`

**Advantages**:
- Unique identifier (DOIs are globally unique)
- Automatic matching by the system
- Easy to verify correctness

### Alternative: Paper ID-Based Naming
**Format**: `paper_<ID>.pdf`  
**Example**:
- Paper ID from CSV: `abc123`
- Filename: `paper_abc123.pdf`

**Use when**: DOI is missing or contains characters that break your filesystem

### What NOT to do:
- ❌ `Science_Paper_v2.pdf` (no identifier)
- ❌ `10.1234/j.example.2023.pdf` (forward slash breaks Windows paths)
- ❌ `paper-from-smith-2023.pdf` (ambiguous, won't match)

---

## Database Status Flow

```
DISCOVERED (API search result)
    ↓
[Abstract Screening by QualityAgent]
    ↓
SCREENED_IN (Passed relevance filter)
    ↓
[Mark for acquisition]
    ↓
AWAITING_PDF (In TO_ACQUIRE.csv)
    ↓
[Human downloads via institutional access]
    ↓
[python main.py --ingest-pdfs]
    ↓
PDF_ACQUIRED (Matched to database)
    ↓
[Extract text from PDF]
    ↓
TEXT_EXTRACTED
    ↓
[LLM full-text analysis]
    ↓
SYNTHESIZED (Summary generated)
    ↓
VALIDATED (Quality check)
    ↓
ARCHIVED (Final storage)
```

---

## Code Reference

### Key Classes
- **`AcquisitionAgent`**: `src/agents/acquisition_agent.py`
  - `generate_acquisition_list()`: Creates TO_ACQUIRE.csv
  - `scan_and_ingest_pdfs()`: Matches PDFs to database
  - `_match_pdf_to_paper()`: Filename → Paper ID matching logic

- **`PaperStatus`**: `src/core/models.py`
  - Enum defining workflow stages

- **`DatabaseManager`**: `src/core/database.py`
  - `get_papers_by_status()`: Query papers by status
  - `get_paper_by_doi()`: Lookup paper by DOI
  - `save_paper()`: Update paper metadata

---

## Troubleshooting

### "No papers awaiting PDF acquisition"
**Cause**: No papers in database with status `AWAITING_PDF`  
**Solution**: 
1. Run abstract screening first (Stage 4 QualityAgent)
2. Manually update paper status:
   ```python
   from src.core.database import DatabaseManager
   from src.core.models import PaperStatus
   
   db = DatabaseManager()
   papers = db.get_papers_by_status(PaperStatus.SCREENED_IN.value)
   for paper in papers[:150]:  # Select top 150
       paper.status = PaperStatus.AWAITING_PDF
       db.save_paper(paper)
   ```

### "PDF matched but file not found"
**Cause**: PDF was moved/deleted after matching  
**Solution**: Re-run `--ingest-pdfs` or manually update `pdf_path` in database

### "Unmatched PDFs"
**Cause**: Filename doesn't match DOI or Paper ID  
**Solution**:
1. Check TO_ACQUIRE.csv for correct filename
2. Rename PDF to suggested filename
3. Re-run `--ingest-pdfs`

### "DOI mismatch"
**Cause**: CSV has DOI `10.1234/j.example` but PDF named `10.1234-j.example.pdf`  
**Solution**: Use underscore `_` not hyphen `-` (system expects `10.1234_j.example.pdf`)

---

## Why This Approach?

### Scientific Rigor (For Paper 1)
- **PRISMA Compliance**: Mirrors standard systematic review methodology (Identification → Screening → Eligibility → Included)
- **No Open Access Bias**: All papers evaluated equally on abstracts, not influenced by PDF availability
- **Reproducibility**: Clear documentation of acquisition process for reviewers

### Copyright Compliance
- **No automated paywall scraping**: Avoids legal/ethical issues that could tank publication
- **Human-verified access**: Uses institutional credentials, respecting publisher agreements
- **Audit trail**: Database records which papers were manually acquired

### Operational Efficiency
- **Targeted downloads**: Only 50-150 PDFs, not 500-1000
- **LLM cost optimization**: Use cheap models (Haiku/Flash) for abstract screening, expensive models (Opus/GPT-4) only for final shortlist
- **Time savings**: 2-3 hours of manual work vs. weeks debugging paywall scrapers

---

## Future Enhancements (Stage 8: Production)

Potential automations (if staying within copyright bounds):
1. **Unpaywall API integration**: Auto-download legally available Open Access PDFs before generating TO_ACQUIRE.csv
2. **arXiv auto-fetch**: Many papers have arXiv versions (legal to download)
3. **PubMed Central**: Open access subset can be auto-downloaded
4. **Browser automation**: Selenium script to auto-download via institutional proxy (if permitted by university IT)

**Critical**: These must be explicitly allowed by your institution's terms of service.

---

## Integration with Stage 2 (Search)

The acquisition workflow assumes papers are already in the database with abstracts. Typical flow:

1. **Stage 2**: `ResearchAgent.search()` → 500-1000 papers with status `DISCOVERED`
2. **Stage 4**: `QualityAgent.screen()` → Filter to 50-150 papers, mark as `SCREENED_IN`
3. **Stage 2.5**: Bulk update `SCREENED_IN` → `AWAITING_PDF`
4. **Stage 2.5**: Follow this guide to acquire PDFs
5. **Stage 5**: `SummarizerAgent.synthesize()` → Full-text analysis

---

## Testing the Workflow

See `tests/test_acquisition_agent.py` for:
- Mock PDF ingestion
- Filename matching edge cases
- Status transition validation
- Database integrity checks

Run tests:
```bash
source venv/bin/activate
python -m pytest tests/test_acquisition_agent.py -v
```

---

## Questions?

For issues with this workflow:
1. Check `data/system.log` for detailed error messages
2. Verify database status: `python -c "from src.core.database import DatabaseManager; print(DatabaseManager().count_papers())"`
3. Manually inspect `data/TO_ACQUIRE.csv` and `data/pdfs/` contents
4. See `WARP.md` for general debugging guidance
