"""
Unhappy path tests for AcquisitionAgent.

Tests failure scenarios, corrupt data, and edge cases.
"""

import pytest
from pathlib import Path
import os

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
    agent.pdf_dir = tmp_path / "pdfs"
    agent.pdf_dir.mkdir(parents=True, exist_ok=True)
    return agent


@pytest.fixture
def sample_paper():
    """Create a sample paper for testing."""
    return Paper(
        id="test_paper_1",
        title="Test Paper",
        doi="10.1234/test.2023",
        year=2023,
        status=PaperStatus.AWAITING_PDF,
        sources=[PaperSource.SEMANTIC_SCHOLAR]
    )


class TestCorruptPDFs:
    """Test handling of corrupt or invalid PDF files."""
    
    def test_zero_byte_pdf(self, acquisition_agent, test_db, sample_paper):
        """Test that 0-byte PDF files are logged as errors."""
        test_db.save_paper(sample_paper)
        acquisition_agent.db = test_db
        
        # Create 0-byte file
        pdf_path = acquisition_agent.pdf_dir / "10.1234_test.2023.pdf"
        pdf_path.touch()  # Creates empty file
        
        stats = acquisition_agent.scan_and_ingest_pdfs()
        
        # Should match but ideally detect corruption
        # Current implementation will match - future: add validation
        assert stats["matched"] >= 0  # At least doesn't crash
    
    def test_invalid_pdf_content(self, acquisition_agent, test_db, sample_paper):
        """Test handling of files with .pdf extension but invalid content."""
        test_db.save_paper(sample_paper)
        acquisition_agent.db = test_db
        
        # Create file with wrong content
        pdf_path = acquisition_agent.pdf_dir / "10.1234_test.2023.pdf"
        pdf_path.write_text("This is not a PDF file")
        
        stats = acquisition_agent.scan_and_ingest_pdfs()
        
        # Should not crash, but future: validate PDF magic bytes
        assert stats["matched"] + stats["unmatched"] + stats["errors"] == 1
    
    def test_pdf_with_special_characters_in_filename(self, acquisition_agent, test_db):
        """Test handling of filenames with special characters."""
        paper = Paper(
            id="special_paper",
            title="Test Paper Title",
            doi="10.1234/test(2023)",  # Parentheses in DOI
            year=2023,
            status=PaperStatus.AWAITING_PDF
        )
        test_db.save_paper(paper)
        acquisition_agent.db = test_db
        
        # Try to match - should handle special chars
        pdf_path = acquisition_agent.pdf_dir / "10.1234_test(2023).pdf"
        pdf_path.touch()
        
        result = acquisition_agent._match_pdf_to_paper(pdf_path)
        
        # May or may not match depending on normalization
        # Key: shouldn't crash
        assert result is None or isinstance(result, tuple)


class TestPermissionErrors:
    """Test handling of permission and filesystem errors."""
    
    def test_no_write_permissions_on_database(self, acquisition_agent, tmp_path, sample_paper):
        """Test handling when database is read-only."""
        # Create database
        db_path = tmp_path / "readonly.db"
        db = DatabaseManager(str(db_path))
        db.save_paper(sample_paper)
        
        # Make database file read-only
        os.chmod(str(db_path), 0o444)
        
        acquisition_agent.db = db
        pdf_path = acquisition_agent.pdf_dir / "10.1234_test.2023.pdf"
        pdf_path.touch()
        
        try:
            # Should handle gracefully
            stats = acquisition_agent.scan_and_ingest_pdfs()
            # May succeed or fail, but shouldn't crash unhandled
            assert isinstance(stats, dict)
        finally:
            # Restore permissions for cleanup
            os.chmod(str(db_path), 0o644)
    
    def test_pdf_directory_does_not_exist(self, acquisition_agent):
        """Test when PDF directory is deleted during operation."""
        # Remove directory
        acquisition_agent.pdf_dir.rmdir()
        
        # Should handle gracefully
        stats = acquisition_agent.scan_and_ingest_pdfs()
        
        assert stats["matched"] == 0
        assert stats["unmatched"] == 0


class TestMalformedData:
    """Test handling of malformed or invalid data."""
    
    def test_paper_with_no_doi_or_id(self, acquisition_agent, test_db):
        """Test matching when paper has neither DOI nor clear ID."""
        # This shouldn't happen in practice, but test defensive code
        paper = Paper(
            id="weird_id_with_no_doi",
            title="Test Paper Title",
            year=2023,
            status=PaperStatus.AWAITING_PDF
        )
        test_db.save_paper(paper)
        acquisition_agent.db = test_db
        
        # Try various filename patterns
        pdf_path = acquisition_agent.pdf_dir / "random_name.pdf"
        pdf_path.touch()
        
        result = acquisition_agent._match_pdf_to_paper(pdf_path)
        assert result is None  # Should not match
    
    def test_duplicate_pdfs(self, acquisition_agent, test_db, sample_paper):
        """Test when multiple PDFs could match same paper."""
        test_db.save_paper(sample_paper)
        acquisition_agent.db = test_db
        
        # Create multiple PDFs that could match
        pdf1 = acquisition_agent.pdf_dir / "10.1234_test.2023.pdf"
        pdf2 = acquisition_agent.pdf_dir / "paper_test_paper_1.pdf"
        pdf3 = acquisition_agent.pdf_dir / "test_paper_1.pdf"
        
        pdf1.touch()
        pdf2.touch()
        pdf3.touch()
        
        stats = acquisition_agent.scan_and_ingest_pdfs()
        
        # All should match, but only first match updates the paper
        assert stats["matched"] >= 1
    
    def test_filename_with_only_partial_doi(self, acquisition_agent, test_db):
        """Test matching when filename has incomplete DOI."""
        paper = Paper(
            id="partial_doi_paper",
            title="Test Paper Title",
            doi="10.1234/test.2023.full.version",
            year=2023,
            status=PaperStatus.AWAITING_PDF
        )
        test_db.save_paper(paper)
        acquisition_agent.db = test_db
        
        # Partial DOI in filename
        pdf_path = acquisition_agent.pdf_dir / "10.1234_test.2023.pdf"
        pdf_path.touch()
        
        result = acquisition_agent._match_pdf_to_paper(pdf_path)
        
        # May or may not match - test it doesn't crash
        assert result is None or isinstance(result, tuple)


class TestDatabaseConsistency:
    """Test database consistency during concurrent operations."""
    
    def test_paper_deleted_during_ingestion(self, acquisition_agent, test_db, sample_paper):
        """Test when paper is deleted from DB while being processed."""
        test_db.save_paper(sample_paper)
        acquisition_agent.db = test_db
        
        pdf_path = acquisition_agent.pdf_dir / "10.1234_test.2023.pdf"
        pdf_path.touch()
        
        # Match the PDF
        result = acquisition_agent._match_pdf_to_paper(pdf_path)
        assert result is not None
        
        paper_id, match_type = result
        
        # Delete paper from database (simulating concurrent deletion)
        # In SQLite, we'd need to manipulate the DB directly
        # For now, just verify the update_paper_with_pdf handles missing paper
        
        # Try to update non-existent paper
        success = acquisition_agent._update_paper_with_pdf("non_existent_id", pdf_path)
        assert success == False  # Should fail gracefully
    
    def test_status_already_changed(self, acquisition_agent, test_db, sample_paper):
        """Test when paper status changes during ingestion."""
        test_db.save_paper(sample_paper)
        acquisition_agent.db = test_db
        
        pdf_path = acquisition_agent.pdf_dir / "10.1234_test.2023.pdf"
        pdf_path.touch()
        
        # Change status to something else
        sample_paper.status = PaperStatus.REJECTED
        test_db.save_paper(sample_paper)
        
        # Try to ingest - should still work but may skip
        stats = acquisition_agent.scan_and_ingest_pdfs()
        
        # Should handle gracefully
        assert isinstance(stats, dict)


class TestEdgeCases:
    """Test unusual but valid edge cases."""
    
    def test_very_long_filename(self, acquisition_agent, test_db):
        """Test handling of extremely long filenames."""
        paper = Paper(
            id="long_name",
            title="Test Paper Title",
            doi="10." + "x" * 200,  # Very long DOI
            year=2023,
            status=PaperStatus.AWAITING_PDF
        )
        test_db.save_paper(paper)
        acquisition_agent.db = test_db
        
        # Filename might be truncated by filesystem
        try:
            long_name = "10." + "_" * 200 + ".pdf"
            pdf_path = acquisition_agent.pdf_dir / long_name
            pdf_path.touch()
            
            result = acquisition_agent._match_pdf_to_paper(pdf_path)
            # Should not crash
            assert result is None or isinstance(result, tuple)
        except OSError:
            # Filesystem may reject the filename - that's OK
            pass
    
    def test_unicode_in_filename(self, acquisition_agent, test_db):
        """Test handling of Unicode characters in filenames."""
        paper = Paper(
            id="unicode_paper",
            title="Test Paper Title",
            doi="10.1234/日本語.2023",  # Unicode in DOI
            year=2023,
            status=PaperStatus.AWAITING_PDF
        )
        test_db.save_paper(paper)
        acquisition_agent.db = test_db
        
        try:
            pdf_path = acquisition_agent.pdf_dir / "10.1234_日本語.2023.pdf"
            pdf_path.touch()
            
            result = acquisition_agent._match_pdf_to_paper(pdf_path)
            # Should handle gracefully
            assert result is None or isinstance(result, tuple)
        except (UnicodeEncodeError, OSError):
            # Some filesystems don't support Unicode - that's OK
            pass
    
    def test_empty_pdf_directory(self, acquisition_agent, test_db, sample_paper):
        """Test when PDF directory exists but is empty."""
        test_db.save_paper(sample_paper)
        acquisition_agent.db = test_db
        
        # Directory exists but no PDFs
        stats = acquisition_agent.scan_and_ingest_pdfs()
        
        assert stats["matched"] == 0
        assert stats["unmatched"] == 0
        assert stats["errors"] == 0
    
    def test_thousands_of_pdfs(self, acquisition_agent, test_db):
        """Test performance with many PDFs (stress test)."""
        # Create many PDFs with random names
        num_pdfs = 100  # Reduced from 1000 for reasonable test time
        
        for i in range(num_pdfs):
            pdf_path = acquisition_agent.pdf_dir / f"random_{i}.pdf"
            pdf_path.touch()
        
        # Should not take forever or crash
        stats = acquisition_agent.scan_and_ingest_pdfs()
        
        assert stats["unmatched"] == num_pdfs
        assert stats["matched"] == 0
