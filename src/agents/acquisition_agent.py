"""
Acquisition Agent for the two-pass workflow.

Phase 1: Generate TO_ACQUIRE.csv for human download
Phase 2: Match PDFs from data/pdfs/ to database entries
"""

import csv
import re
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from datetime import datetime, UTC

from ..core.base_agent import BaseAgent
from ..core.models import Paper, PaperStatus
from ..core.database import DatabaseManager
from ..utils.logger import get_logger


class AcquisitionAgent(BaseAgent):
    """Manages PDF acquisition through human-in-the-loop workflow."""
    
    def __init__(self, config_path: str = "./config/config.yaml"):
        """Initialize acquisition agent."""
        super().__init__(name="acquisition_agent", description="PDF acquisition and matching")
        self.db = DatabaseManager()
        self.logger = get_logger("acquisition_agent")
        self.pdf_dir = Path("./data/pdfs")
        self.pdf_dir.mkdir(parents=True, exist_ok=True)
    
    def run(self, *args, **kwargs):
        """Main execution method - runs full acquisition workflow."""
        from ..core.base_agent import TaskResult
        
        # Generate acquisition list
        count = self.generate_acquisition_list()
        
        if count > 0:
            print("\n⏸️  Workflow paused for manual PDF download.")
            print("After downloading PDFs, run: python stage2.5_demo.py --ingest")
            
            return TaskResult(
                success=True,
                data={"acquisition_list_generated": count},
                metadata={"awaiting_manual_download": True}
            )
        else:
            # No papers awaiting PDF, try ingestion
            stats = self.scan_and_ingest_pdfs()
            
            return TaskResult(
                success=True,
                data=stats,
                metadata={"ingestion_complete": True}
            )
    
    def generate_acquisition_list(self, output_path: str = "./data/TO_ACQUIRE.csv") -> int:
        """
        Generate CSV of papers needing PDF acquisition.
        
        Selects papers with status AWAITING_PDF and exports metadata
        for manual download via institutional access.
        
        Args:
            output_path: Path to save CSV file
            
        Returns:
            Number of papers exported
        """
        self.logger.info("Generating acquisition list")
        
        papers = self.db.get_papers_by_status(PaperStatus.AWAITING_PDF.value)
        
        if not papers:
            self.logger.info("No papers awaiting PDF acquisition")
            return 0
        
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                'paper_id',
                'title',
                'authors',
                'year',
                'journal',
                'doi',
                'doi_url',
                'publisher_url',
                'suggested_filename'
            ])
            
            for paper in papers:
                doi_url = f"https://doi.org/{paper.doi}" if paper.doi else ""
                # Suggest filename based on normalized DOI or ID
                suggested_filename = self._generate_filename(paper)
                
                writer.writerow([
                    paper.id,
                    paper.title,
                    "; ".join(paper.authors[:3]),  # First 3 authors
                    paper.year,
                    paper.journal or "",
                    paper.doi or "",
                    doi_url,
                    paper.url or "",
                    suggested_filename
                ])
        
        self.logger.info(f"Exported {len(papers)} papers to {output_file}")
        print(f"\n{'='*80}")
        print(f"📋 ACQUISITION LIST GENERATED")
        print(f"{'='*80}")
        print(f"Papers needing PDF: {len(papers)}")
        print(f"Export location: {output_file}")
        print(f"\nNext steps:")
        print(f"1. Use your institutional access to download PDFs")
        print(f"2. Save PDFs to: {self.pdf_dir.absolute()}")
        print(f"3. Use suggested filenames from the CSV for easy matching")
        print(f"4. Run: python main.py --ingest-pdfs")
        print(f"{'='*80}\n")
        
        return len(papers)
    
    def _generate_filename(self, paper: Paper) -> str:
        """
        Generate standardized filename for PDF matching.
        
        Prioritizes DOI-based naming, falls back to paper ID.
        
        Args:
            paper: Paper object
            
        Returns:
            Suggested filename (e.g., "10.1234_j.example.2023.pdf")
        """
        if paper.doi:
            # Normalize DOI: replace / with _ for filesystem safety
            safe_doi = paper.doi.replace('/', '_').replace('\\', '_')
            return f"{safe_doi}.pdf"
        else:
            # Use internal ID
            return f"paper_{paper.id}.pdf"
    
    def scan_and_ingest_pdfs(self) -> Dict[str, int]:
        """
        Scan data/pdfs/ for PDFs and match them to database entries.
        
        Matching strategy:
        1. Try to extract DOI from filename (e.g., "10.1234_j.example.2023.pdf")
        2. Fall back to paper ID pattern (e.g., "paper_abc123.pdf")
        3. Log unmatched files for manual review
        
        Returns:
            Statistics dict with counts of matched, unmatched, errors
        """
        self.logger.info("Scanning for PDFs to ingest")
        
        pdf_files = list(self.pdf_dir.glob("*.pdf"))
        
        if not pdf_files:
            self.logger.warning(f"No PDF files found in {self.pdf_dir}")
            print(f"⚠️  No PDF files found in {self.pdf_dir}")
            return {"matched": 0, "unmatched": 0, "errors": 0}
        
        stats = {
            "matched": 0,
            "unmatched": 0,
            "errors": 0
        }
        
        unmatched_files = []
        
        for pdf_file in pdf_files:
            try:
                match_result = self._match_pdf_to_paper(pdf_file)
                
                if match_result:
                    paper_id, match_type = match_result
                    success = self._update_paper_with_pdf(paper_id, pdf_file)
                    
                    if success:
                        stats["matched"] += 1
                        self.logger.info(f"Matched {pdf_file.name} to {paper_id} via {match_type}")
                    else:
                        stats["errors"] += 1
                else:
                    stats["unmatched"] += 1
                    unmatched_files.append(pdf_file.name)
                    
            except Exception as e:
                self.logger.error(f"Error processing {pdf_file.name}: {str(e)}")
                stats["errors"] += 1
        
        # Report results
        print(f"\n{'='*80}")
        print(f"📥 PDF INGESTION COMPLETE")
        print(f"{'='*80}")
        print(f"Total PDFs scanned: {len(pdf_files)}")
        print(f"✅ Successfully matched: {stats['matched']}")
        print(f"❌ Unmatched: {stats['unmatched']}")
        print(f"⚠️  Errors: {stats['errors']}")
        
        if unmatched_files:
            print(f"\nUnmatched files:")
            for filename in unmatched_files:
                print(f"  - {filename}")
            print(f"\nTip: Rename files to match DOI or paper ID from TO_ACQUIRE.csv")
        
        print(f"{'='*80}\n")
        
        self.logger.info(f"Ingestion complete: {stats}")
        return stats
    
    def _match_pdf_to_paper(self, pdf_file: Path) -> Optional[Tuple[str, str]]:
        """
        Attempt to match PDF filename to a paper in database.
        
        Args:
            pdf_file: Path to PDF file
            
        Returns:
            (paper_id, match_type) tuple if matched, None otherwise
        """
        filename = pdf_file.stem  # Remove .pdf extension
        
        # Strategy 1: DOI-based matching (e.g., "10.1234_j.example.2023")
        doi_match = re.match(r'(10\.\d+[._].+)', filename)
        if doi_match:
            # Reconstruct DOI (replace _ back to /)
            doi_candidate = doi_match.group(1).replace('_', '/')
            
            paper = self.db.get_paper_by_doi(doi_candidate)
            if paper:
                return (paper.id, "DOI")
        
        # Strategy 2: Paper ID pattern (e.g., "paper_abc123")
        id_match = re.match(r'paper[_-](.+)', filename, re.IGNORECASE)
        if id_match:
            paper_id_candidate = id_match.group(1)
            
            paper = self.db.get_paper(paper_id_candidate)
            if paper:
                return (paper.id, "ID")
        
        # Strategy 3: Exact ID match (user may have used raw ID as filename)
        paper = self.db.get_paper(filename)
        if paper:
            return (paper.id, "exact_ID")
        
        self.logger.warning(f"Could not match PDF: {pdf_file.name}")
        return None
    
    def _update_paper_with_pdf(self, paper_id: str, pdf_file: Path) -> bool:
        """
        Update paper record with PDF path and status.
        
        Args:
            paper_id: Paper ID to update
            pdf_file: Path to PDF file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            paper = self.db.get_paper(paper_id)
            if not paper:
                self.logger.error(f"Paper {paper_id} not found in database")
                return False
            
            # Update paper with PDF path and new status
            paper.pdf_path = str(pdf_file.absolute())
            paper.status = PaperStatus.PDF_ACQUIRED
            paper.last_updated = datetime.now(UTC)
            
            success = self.db.save_paper(paper)
            
            if success:
                self.logger.info(f"Updated paper {paper_id}: PDF acquired")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Failed to update paper {paper_id}: {str(e)}")
            return False
    
    def get_acquisition_statistics(self) -> Dict[str, int]:
        """
        Get statistics on PDF acquisition status.
        
        Returns:
            Dict with counts by status
        """
        stats = {
            "awaiting_pdf": len(self.db.get_papers_by_status(PaperStatus.AWAITING_PDF.value)),
            "pdf_acquired": len(self.db.get_papers_by_status(PaperStatus.PDF_ACQUIRED.value)),
            "text_extracted": len(self.db.get_papers_by_status(PaperStatus.TEXT_EXTRACTED.value)),
        }
        
        return stats
