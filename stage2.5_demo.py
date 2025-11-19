#!/usr/bin/env python3
"""
Stage 2.5 Demo: PDF Acquisition Workflow

Demonstrates the two-pass PRISMA workflow:
1. Generate acquisition list from papers with AWAITING_PDF status
2. Simulate manual download (or prompt user)
3. Ingest PDFs and match to database

Usage:
    python stage2.5_demo.py --generate    # Generate TO_ACQUIRE.csv
    python stage2.5_demo.py --ingest      # Ingest PDFs from data/pdfs/
    python stage2.5_demo.py --full        # Run full demo with mock data
"""

import sys
import argparse
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.agents.acquisition_agent import AcquisitionAgent
from src.core.database import DatabaseManager
from src.core.models import Paper, PaperStatus, PaperSource, ExclusionReason
from src.utils.logger import get_logger
from src.utils.prisma_generator import generate_prisma_report


def create_mock_papers(db: DatabaseManager, count: int = 5) -> None:
    """Create mock papers for testing the workflow."""
    logger = get_logger("stage2.5_demo")
    
    mock_papers = [
        {
            "id": "demo_paper_1",
            "title": "Deep Learning for Crop Yield Prediction: A Systematic Review",
            "authors": ["Zhang, Wei", "Smith, John", "Garcia, Maria"],
            "abstract": "This systematic review examines the application of deep learning techniques in crop yield prediction, analyzing 150 papers published between 2018-2023.",
            "doi": "10.1016/j.compag.2023.107890",
            "url": "https://www.sciencedirect.com/science/article/pii/demo1",
            "year": 2023,
            "journal": "Computers and Electronics in Agriculture",
            "citation_count": 42,
        },
        {
            "id": "demo_paper_2",
            "title": "Machine Learning for Irrigation Scheduling: Current State and Future Directions",
            "authors": ["Kumar, Rajesh", "Liu, Yifan"],
            "abstract": "We review machine learning approaches for irrigation scheduling, covering reinforcement learning, neural networks, and ensemble methods.",
            "doi": "10.3390/w15081234",
            "url": "https://www.mdpi.com/demo2",
            "year": 2023,
            "journal": "Water",
            "citation_count": 18,
        },
        {
            "id": "demo_paper_3",
            "title": "Automated Literature Review Using LLMs: A Framework",
            "authors": ["Brown, Alice", "Johnson, David", "Wang, Ling"],
            "abstract": "Large language models enable automated literature review. We propose a framework for systematic review using GPT-4 and Claude.",
            "doi": "10.1038/s41586-2023-06543-2",
            "url": "https://nature.com/articles/demo3",
            "year": 2023,
            "journal": "Nature",
            "citation_count": 89,
        },
        {
            "id": "demo_paper_4",
            "title": "Precision Agriculture and AI: Opportunities and Challenges",
            "authors": ["Martinez, Carlos", "Taylor, Emma"],
            "abstract": "Artificial intelligence is transforming precision agriculture. This paper reviews AI applications in crop monitoring, yield prediction, and resource optimization.",
            "doi": "10.1007/s11119-023-10012-x",
            "url": "https://link.springer.com/article/demo4",
            "year": 2023,
            "journal": "Precision Agriculture",
            "citation_count": 31,
        },
        {
            "id": "demo_paper_5",
            "title": "Semantic Search for Scientific Literature: A Comparative Study",
            "authors": ["Anderson, Kate", "Chen, Min"],
            "abstract": "We compare semantic search engines for scientific literature, including Semantic Scholar, Google Scholar, and PubMed.",
            "doi": "10.1002/asi.24567",
            "url": "https://asistdl.onlinelibrary.wiley.com/demo5",
            "year": 2023,
            "journal": "Journal of the Association for Information Science and Technology",
            "citation_count": 12,
        },
    ]
    
    logger.info(f"Creating {count} mock papers for demo...")
    
    for i, paper_data in enumerate(mock_papers[:count]):
        paper = Paper(
            id=paper_data["id"],
            title=paper_data["title"],
            authors=paper_data["authors"],
            abstract=paper_data["abstract"],
            doi=paper_data["doi"],
            url=paper_data["url"],
            year=paper_data["year"],
            journal=paper_data["journal"],
            citation_count=paper_data["citation_count"],
            status=PaperStatus.AWAITING_PDF,  # Ready for acquisition
            sources=[PaperSource.SEMANTIC_SCHOLAR],
            source_ids={"semantic_scholar": f"ss_{i+1}"}
        )
        
        db.save_paper(paper)
        logger.info(f"Created: {paper.title[:50]}...")
    
    print(f"\n✅ Created {count} mock papers with status AWAITING_PDF")


def demo_generate_list(agent: AcquisitionAgent) -> None:
    """Demo: Generate acquisition list."""
    print("\n" + "="*80)
    print("STEP 1: GENERATE ACQUISITION LIST")
    print("="*80)
    
    count = agent.generate_acquisition_list()
    
    if count > 0:
        print(f"\n📝 Review the file: data/TO_ACQUIRE.csv")
        print(f"   It contains {count} papers with DOI links and suggested filenames.")


def demo_ingest_pdfs(agent: AcquisitionAgent) -> None:
    """Demo: Ingest PDFs from data/pdfs/."""
    print("\n" + "="*80)
    print("STEP 2: INGEST PDFs")
    print("="*80)
    
    # Check if any PDFs exist
    pdf_files = list(agent.pdf_dir.glob("*.pdf"))
    
    if not pdf_files:
        print("\n⚠️  No PDFs found in data/pdfs/")
        print("\nTo test the ingestion workflow:")
        print("1. Create empty test PDFs:")
        print("   touch data/pdfs/10.1016_j.compag.2023.107890.pdf")
        print("   touch data/pdfs/10.3390_w15081234.pdf")
        print("2. Re-run: python stage2.5_demo.py --ingest")
        return
    
    print(f"\n📂 Found {len(pdf_files)} PDF(s) in data/pdfs/")
    
    stats = agent.scan_and_ingest_pdfs()
    
    # Show summary
    print("\n" + "="*80)
    print("INGESTION SUMMARY")
    print("="*80)
    print(f"Matched:   {stats['matched']}")
    print(f"Unmatched: {stats['unmatched']}")
    print(f"Errors:    {stats['errors']}")


def demo_full_workflow(agent: AcquisitionAgent, db: DatabaseManager) -> None:
    """Run full demo with mock data."""
    print("\n" + "="*80)
    print("STAGE 2.5: FULL WORKFLOW DEMO")
    print("="*80)
    print("\nThis demo simulates the two-pass PDF acquisition workflow:")
    print("1. Abstract screening identifies 5 papers for full-text review")
    print("2. System generates TO_ACQUIRE.csv for manual download")
    print("3. After download, system matches PDFs to database")
    
    # Step 0: Create mock papers
    print("\n" + "="*80)
    print("STEP 0: SETUP (Creating Mock Papers)")
    print("="*80)
    create_mock_papers(db, count=5)
    
    # Step 1: Generate acquisition list
    demo_generate_list(agent)
    
    # Step 2: Prompt for manual download
    print("\n" + "="*80)
    print("STEP 2: MANUAL DOWNLOAD (Simulated)")
    print("="*80)
    print("\n📥 In a real workflow, you would:")
    print("   1. Open data/TO_ACQUIRE.csv")
    print("   2. Use DOI links to download PDFs via university library")
    print("   3. Save PDFs to data/pdfs/ using suggested filenames")
    print("\n🤖 For this demo, create test PDFs manually:")
    print("   touch data/pdfs/10.1016_j.compag.2023.107890.pdf")
    print("   touch data/pdfs/10.3390_w15081234.pdf")
    print("\nThen run: python stage2.5_demo.py --ingest")
    
    # Check if user wants to continue
    print("\n" + "="*80)
    print("Demo complete! Check data/TO_ACQUIRE.csv to see the acquisition list.")
    print("="*80)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Stage 2.5 Demo: PDF Acquisition Workflow"
    )
    parser.add_argument(
        "--generate",
        action="store_true",
        help="Generate TO_ACQUIRE.csv from papers with AWAITING_PDF status"
    )
    parser.add_argument(
        "--ingest",
        action="store_true",
        help="Ingest PDFs from data/pdfs/ and match to database"
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help="Run full demo with mock data"
    )
    parser.add_argument(
        "--create-mocks",
        type=int,
        metavar="N",
        help="Create N mock papers with AWAITING_PDF status"
    )
    parser.add_argument(
        "--prisma",
        action="store_true",
        help="Generate PRISMA 2020 flow diagram from current database state"
    )
    
    args = parser.parse_args()
    
    # Initialize
    agent = AcquisitionAgent()
    db = DatabaseManager()
    
    # Execute based on flags
    if args.create_mocks:
        create_mock_papers(db, count=args.create_mocks)
    elif args.generate:
        demo_generate_list(agent)
    elif args.ingest:
        demo_ingest_pdfs(agent)
    elif args.prisma:
        generate_prisma_report(output_formats=["text", "csv", "markdown"])
    elif args.full:
        demo_full_workflow(agent, db)
    else:
        parser.print_help()
        print("\n" + "="*80)
        print("QUICK START")
        print("="*80)
        print("\n1. Run full demo:")
        print("   python stage2.5_demo.py --full")
        print("\n2. After creating test PDFs, ingest them:")
        print("   python stage2.5_demo.py --ingest")
        print("\n3. Or use individual commands:")
        print("   python stage2.5_demo.py --create-mocks 3")
        print("   python stage2.5_demo.py --generate")
        print("   python stage2.5_demo.py --ingest")
        print("\n4. Generate PRISMA 2020 flow diagram:")
        print("   python stage2.5_demo.py --prisma")


if __name__ == "__main__":
    main()
