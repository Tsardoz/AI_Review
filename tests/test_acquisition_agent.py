"""
Tests for the AcquisitionAgent and PDF matching logic.
"""

import pytest
from pathlib import Path
from datetime import datetime, UTC

from src.agents.acquisition_agent import AcquisitionAgent
from src.core.models import Paper, PaperStatus, PaperSource
from src.core.database import DatabaseManager


@pytest.fixture
def test_db(tmp_path):
    """Create a temporary test database."""
    db_path = tmp_path / "test.db"
    return DatabaseManager(str(db_path))


@pytest.fixture
def acquisition_agent(tmp_path):
    """Create AcquisitionAgent with temporary directories."""
    agent = AcquisitionAgent()
    # Override paths to use temp directory
    agent.pdf_dir = tmp_path / "pdfs"
    agent.pdf_dir.mkdir(parents=True, exist_ok=True)
    return agent


@pytest.fixture
def sample_paper():
    """Create a sample paper for testing."""
    return Paper(
        id="test_paper_1",
        title="Machine Learning for Agriculture: A Review",
        authors=["Smith, John", "Wang, Li", "Garcia, Maria"],
        abstract="This paper reviews machine learning techniques for precision agriculture.",
        doi="10.1234/j.example.2023.001",
        url="https://example.com/papers/ml-agriculture",
        year=2023,
        journal="Agricultural Technology Review",
        status=PaperStatus.AWAITING_PDF,
        sources=[PaperSource.SEMANTIC_SCHOLAR],
        source_ids={"semantic_scholar": "ss_12345"}
    )


class TestFilenameGeneration:
    """Test PDF filename generation logic."""
    
    def test_generate_filename_with_doi(self, acquisition_agent, sample_paper):
        """Test filename generation for paper with DOI."""
        filename = acquisition_agent._generate_filename(sample_paper)
        assert filename == "10.1234_j.example.2023.001.pdf"
    
    def test_generate_filename_without_doi(self, acquisition_agent):
        """Test filename generation for paper without DOI."""
        paper = Paper(
            id="no_doi_paper",
            title="Test Paper",
            year=2023,
            status=PaperStatus.AWAITING_PDF
        )
        filename = acquisition_agent._generate_filename(paper)
        assert filename == "paper_no_doi_paper.pdf"
    
    def test_filename_handles_special_chars(self, acquisition_agent):
        """Test that DOIs with special characters are normalized."""
        paper = Paper(
            id="special_paper",
            title="Test Paper",
            doi="10.1234/j.ex\\ample/2023",
            year=2023,
            status=PaperStatus.AWAITING_PDF
        )
        filename = acquisition_agent._generate_filename(paper)
        # Both / and \ should be replaced with _
        assert "/" not in filename
        assert "\\" not in filename
        assert filename == "10.1234_j.ex_ample_2023.pdf"


class TestPDFMatching:
    """Test PDF filename matching strategies."""
    
    def test_match_doi_based_filename(self, acquisition_agent, test_db, sample_paper):
        """Test matching PDF with DOI-based filename."""
        # Save paper to database
        test_db.save_paper(sample_paper)
        acquisition_agent.db = test_db
        
        # Create mock PDF file with DOI-based name
        pdf_path = acquisition_agent.pdf_dir / "10.1234_j.example.2023.001.pdf"
        pdf_path.touch()
        
        result = acquisition_agent._match_pdf_to_paper(pdf_path)
        
        assert result is not None
        paper_id, match_type = result
        assert paper_id == "test_paper_1"
        assert match_type == "DOI"
    
    def test_match_paper_id_filename(self, acquisition_agent, test_db, sample_paper):
        """Test matching PDF with paper_<id> filename."""
        test_db.save_paper(sample_paper)
        acquisition_agent.db = test_db
        
        # Create mock PDF with paper_ID format
        pdf_path = acquisition_agent.pdf_dir / "paper_test_paper_1.pdf"
        pdf_path.touch()
        
        result = acquisition_agent._match_pdf_to_paper(pdf_path)
        
        assert result is not None
        paper_id, match_type = result
        assert paper_id == "test_paper_1"
        assert match_type == "ID"
    
    def test_match_exact_id_filename(self, acquisition_agent, test_db, sample_paper):
        """Test matching PDF with exact ID as filename."""
        test_db.save_paper(sample_paper)
        acquisition_agent.db = test_db
        
        # Create mock PDF with exact ID
        pdf_path = acquisition_agent.pdf_dir / "test_paper_1.pdf"
        pdf_path.touch()
        
        result = acquisition_agent._match_pdf_to_paper(pdf_path)
        
        assert result is not None
        paper_id, match_type = result
        assert paper_id == "test_paper_1"
        assert match_type == "exact_ID"
    
    def test_no_match_random_filename(self, acquisition_agent, test_db, sample_paper):
        """Test that random filenames don't match."""
        test_db.save_paper(sample_paper)
        acquisition_agent.db = test_db
        
        pdf_path = acquisition_agent.pdf_dir / "random_paper.pdf"
        pdf_path.touch()
        
        result = acquisition_agent._match_pdf_to_paper(pdf_path)
        
        assert result is None


class TestPDFIngestion:
    """Test full PDF ingestion workflow."""
    
    def test_scan_empty_directory(self, acquisition_agent):
        """Test scanning when no PDFs present."""
        stats = acquisition_agent.scan_and_ingest_pdfs()
        
        assert stats["matched"] == 0
        assert stats["unmatched"] == 0
        assert stats["errors"] == 0
    
    def test_ingest_single_pdf(self, acquisition_agent, test_db, sample_paper):
        """Test ingesting a single matched PDF."""
        # Setup
        test_db.save_paper(sample_paper)
        acquisition_agent.db = test_db
        
        pdf_path = acquisition_agent.pdf_dir / "10.1234_j.example.2023.001.pdf"
        pdf_path.touch()
        
        # Run ingestion
        stats = acquisition_agent.scan_and_ingest_pdfs()
        
        assert stats["matched"] == 1
        assert stats["unmatched"] == 0
        assert stats["errors"] == 0
        
        # Verify database updated
        updated_paper = test_db.get_paper("test_paper_1")
        assert updated_paper.status == PaperStatus.PDF_ACQUIRED
        assert updated_paper.pdf_path == str(pdf_path.absolute())
    
    def test_ingest_with_unmatched_files(self, acquisition_agent, test_db, sample_paper):
        """Test ingestion when some files don't match."""
        test_db.save_paper(sample_paper)
        acquisition_agent.db = test_db
        
        # Create matched and unmatched PDFs
        matched_pdf = acquisition_agent.pdf_dir / "10.1234_j.example.2023.001.pdf"
        matched_pdf.touch()
        
        unmatched_pdf = acquisition_agent.pdf_dir / "random_file.pdf"
        unmatched_pdf.touch()
        
        stats = acquisition_agent.scan_and_ingest_pdfs()
        
        assert stats["matched"] == 1
        assert stats["unmatched"] == 1
        assert stats["errors"] == 0


class TestAcquisitionList:
    """Test acquisition list generation."""
    
    def test_generate_empty_list(self, acquisition_agent, test_db, tmp_path):
        """Test generating list when no papers await PDF."""
        acquisition_agent.db = test_db
        output_path = tmp_path / "TO_ACQUIRE.csv"
        
        count = acquisition_agent.generate_acquisition_list(str(output_path))
        
        assert count == 0
        assert not output_path.exists()
    
    def test_generate_acquisition_list(self, acquisition_agent, test_db, tmp_path, sample_paper):
        """Test generating acquisition list with papers."""
        test_db.save_paper(sample_paper)
        acquisition_agent.db = test_db
        
        output_path = tmp_path / "TO_ACQUIRE.csv"
        count = acquisition_agent.generate_acquisition_list(str(output_path))
        
        assert count == 1
        assert output_path.exists()
        
        # Verify CSV contents
        with open(output_path, 'r') as f:
            lines = f.readlines()
            assert len(lines) == 2  # Header + 1 data row
            assert "paper_id" in lines[0]
            assert "test_paper_1" in lines[1]
            assert "10.1234/j.example.2023.001" in lines[1]


class TestStatusTransitions:
    """Test paper status transitions during acquisition."""
    
    def test_status_update_on_pdf_match(self, acquisition_agent, test_db, sample_paper):
        """Test that status changes from AWAITING_PDF to PDF_ACQUIRED."""
        test_db.save_paper(sample_paper)
        acquisition_agent.db = test_db
        
        pdf_path = acquisition_agent.pdf_dir / "10.1234_j.example.2023.001.pdf"
        pdf_path.touch()
        
        # Initial status
        paper = test_db.get_paper("test_paper_1")
        assert paper.status == PaperStatus.AWAITING_PDF
        
        # Update
        success = acquisition_agent._update_paper_with_pdf("test_paper_1", pdf_path)
        assert success
        
        # Verify status changed
        updated_paper = test_db.get_paper("test_paper_1")
        assert updated_paper.status == PaperStatus.PDF_ACQUIRED
        assert updated_paper.pdf_path is not None


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def test_doi_with_underscore_already(self, acquisition_agent):
        """Test DOI that already contains underscores."""
        paper = Paper(
            id="edge_case",
            title="Test Paper Title",
            doi="10.1234_already_has_underscore",
            year=2023,
            status=PaperStatus.AWAITING_PDF
        )
        filename = acquisition_agent._generate_filename(paper)
        # Should not double-process
        assert filename == "10.1234_already_has_underscore.pdf"
    
    def test_paper_without_abstract(self, acquisition_agent):
        """Test handling papers without abstracts (should still work)."""
        paper = Paper(
            id="no_abstract",
            title="Paper Without Abstract",
            year=2023,
            doi="10.9999/test.2023",
            status=PaperStatus.AWAITING_PDF
        )
        filename = acquisition_agent._generate_filename(paper)
        assert filename == "10.9999_test.2023.pdf"
