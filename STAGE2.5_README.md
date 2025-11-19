# Stage 2.5: PDF Acquisition - Quick Start

## What is This?

**PRISMA-compliant two-pass workflow** for acquiring PDFs:
1. Screen abstracts → Shortlist 50-150 papers
2. Manual download via institutional access
3. Auto-match PDFs to database

**Why?** Eliminates Open Access bias, ensures copyright compliance, and is operationally practical.

---

## Quick Demo

```bash
# Activate virtual environment
source venv/bin/activate

# Run the demo
python stage2.5_demo.py --full

# This creates 5 mock papers and generates TO_ACQUIRE.csv

# Create test PDFs (simulate manual download)
touch data/pdfs/10.1016_j.compag.2023.107890.pdf
touch data/pdfs/10.3390_w15081234.pdf

# Ingest the PDFs
python stage2.5_demo.py --ingest
```

---

## Real Workflow

### 1. After Abstract Screening (Stage 4)
You have 50-150 papers with status `SCREENED_IN` in your database.

### 2. Generate Acquisition List
```bash
python stage2.5_demo.py --generate
```
Creates `data/TO_ACQUIRE.csv` with:
- Paper IDs
- Titles & Authors
- DOI links (https://doi.org/...)
- Suggested filenames

### 3. Manual Download
1. Open `data/TO_ACQUIRE.csv` in Excel/LibreOffice
2. Click DOI links (your university library should intercept them)
3. Download PDFs
4. Save to `data/pdfs/` using the suggested filename from the CSV

**Example**: For DOI `10.1234/j.example.2023`, save as `10.1234_j.example.2023.pdf`

### 4. Ingest PDFs
```bash
python stage2.5_demo.py --ingest
```
Automatically matches PDFs to database and updates status to `PDF_ACQUIRED`.

---

## Key Features

### Intelligent Filename Matching
Three strategies (in order):
1. **DOI-based**: `10.1234_j.example.2023.pdf` → DOI `10.1234/j.example.2023`
2. **Paper ID**: `paper_abc123.pdf` → Paper ID `abc123`
3. **Exact ID**: `abc123.pdf` → Paper ID `abc123`

### Status Flow
```
SCREENED_IN → AWAITING_PDF → PDF_ACQUIRED → TEXT_EXTRACTED → SYNTHESIZED
```

### Error Handling
- Unmatched PDFs are logged for manual review
- System shows clear error messages if files can't be matched
- Safe to re-run ingestion multiple times

---

## Files Created

```
src/agents/acquisition_agent.py       # Main agent
tests/test_acquisition_agent.py       # Comprehensive tests
stage2.5_demo.py                      # Runnable demo script
data/pdfs/                            # PDF storage (gitignored)
STAGE2.5_ACQUISITION_GUIDE.md         # Full documentation
STAGE2.5_IMPLEMENTATION_SUMMARY.md    # Technical details
```

---

## Testing

Run tests:
```bash
python -m pytest tests/test_acquisition_agent.py -v
```

All tests should pass (filename matching, ingestion, status transitions, etc.)

---

## Documentation

- **User Guide**: `STAGE2.5_ACQUISITION_GUIDE.md` - Complete workflow documentation
- **Implementation**: `STAGE2.5_IMPLEMENTATION_SUMMARY.md` - Technical details and design decisions
- **Project Context**: See `WARP.md` for overall project structure

---

## For Your Paper

This implementation gives you:
- **PRISMA compliance** (standard systematic review methodology)
- **No Open Access bias** (all papers evaluated equally on abstracts)
- **Copyright safety** (manual download via institutional access)
- **Reproducibility** (clear documentation for reviewers)

See `STAGE2.5_IMPLEMENTATION_SUMMARY.md` section "For Your Paper" for suggested methodology text.

---

## Next Steps

1. **Integration**: Add acquisition commands to `main.py` CLI
2. **Stage 4**: Build QualityAgent for abstract screening
3. **Stage 5**: Implement PDF text extraction and full-text synthesis

---

## Troubleshooting

### "No papers awaiting PDF acquisition"
Run `python stage2.5_demo.py --create-mocks 5` to create test papers.

### "Unmatched PDFs"
Check that filenames match the suggested format in TO_ACQUIRE.csv. Use DOI with underscores: `10.1234_j.example.pdf`

### "PDF matched but file not found"
Re-run `--ingest` or check that PDF files haven't been moved/deleted.

For more details, see `STAGE2.5_ACQUISITION_GUIDE.md`.

---

**Status**: ✅ Fully implemented and tested  
**Ready for**: Integration with main workflow and real-world testing
