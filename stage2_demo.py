"""
Stage 2 Demo: Single-Source Search with Semantic Scholar

Demonstrates:
- Query formulation from research domain
- Searching Semantic Scholar API
- Parsing and storing results
- Database persistence
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from src.core.models import ResearchDomain
from src.core.database import DatabaseManager
from src.core.config import get_config
from src.agents.research_agent import ResearchAgent


def main():
    print("=" * 70)
    print("STAGE 2 DEMO: Single-Source Literature Search")
    print("=" * 70)
    print()
    
    # Initialize database
    print("📊 Initializing database...")
    db = DatabaseManager("./data/stage2_demo.db")
    print("✓ Database initialized\n")
    
    # Load configuration
    print("⚙️  Loading configuration...")
    config = get_config()
    research_domain_config = config.get('research_domain')
    print(f"✓ Research domain: {research_domain_config['name']}\n")
    
    # Create research domain model
    domain = ResearchDomain(
        name=research_domain_config['name'],
        subject_type=research_domain_config['subject_type'],
        keywords=research_domain_config['keywords'],
        description=research_domain_config.get('description', '')
    )
    
    print(f"🔍 Research Domain:")
    print(f"   Name: {domain.name}")
    print(f"   Subject: {domain.subject_type}")
    print(f"   Keywords: {', '.join(domain.keywords[:3])}...")
    print()
    
    # Initialize Research Agent
    print("🤖 Initializing Research Agent...")
    agent = ResearchAgent(db)
    print("✓ Research Agent ready\n")
    
    # Execute search (using fewer papers for demo)
    print("🔎 Executing literature search...")
    print("   (This will generate queries and search Semantic Scholar)")
    print()
    
    try:
        stats = agent.search_literature(
            research_domain=domain,
            max_queries=2,  # Limit to 2 queries for demo
            papers_per_query=10  # 10 papers per query
        )
        
        print("=" * 70)
        print("SEARCH RESULTS")
        print("=" * 70)
        print()
        print(f"✓ Queries executed: {stats['queries_executed']}")
        print(f"  Queries:")
        for i, query in enumerate(stats['queries'], 1):
            print(f"    {i}. \"{query}\"")
        print()
        print(f"✓ Total papers found: {stats['total_papers_found']}")
        print(f"✓ Unique papers: {stats['unique_papers']}")
        print(f"✓ Papers stored in database: {stats['papers_stored']}")
        print()
        
        # Show some paper details
        if stats['papers_stored'] > 0:
            print("=" * 70)
            print("SAMPLE PAPERS")
            print("=" * 70)
            print()
            
            papers = db.get_all_papers(limit=3)
            for i, paper in enumerate(papers[:3], 1):
                print(f"{i}. {paper.title}")
                print(f"   Authors: {', '.join(paper.authors[:2])}{'...' if len(paper.authors) > 2 else ''}")
                print(f"   Year: {paper.year}")
                print(f"   Citations: {paper.citation_count}")
                print(f"   Journal: {paper.journal or 'N/A'}")
                if paper.doi:
                    print(f"   DOI: {paper.doi}")
                print()
        
        print("=" * 70)
        print("✓ STAGE 2 DEMO COMPLETE")
        print("=" * 70)
        print()
        print(f"Database saved to: ./data/stage2_demo.db")
        print()
        
    except Exception as e:
        print("=" * 70)
        print("✗ ERROR OCCURRED")
        print("=" * 70)
        print()
        print(f"Error: {str(e)}")
        print()
        print("Note: If you see rate limiting errors, the Semantic Scholar API")
        print("      may be temporarily unavailable or rate-limited.")
        print("      The system includes retry logic and will handle this gracefully.")
        return 1
    
    return 0


if __name__ == '__main__':
    exit(main())
