"""
PRISMA 2020 Flow Diagram Generator

Automatically generates PRISMA-compliant flow diagrams from database state.
Tracks paper counts at each stage of the systematic review process.

References:
    Page, M. J., et al. (2021). The PRISMA 2020 statement: an updated guideline
    for reporting systematic reviews. BMJ, 372.
"""

from typing import Dict, List, Tuple
from collections import defaultdict, Counter
from pathlib import Path

from ..core.database import DatabaseManager
from ..core.models import PaperStatus, PaperSource, ExclusionReason
from ..utils.logger import get_logger


class PRISMAFlowGenerator:
    """Generate PRISMA 2020-compliant flow diagrams."""
    
    def __init__(self, db: DatabaseManager = None):
        """Initialize PRISMA flow generator."""
        self.db = db or DatabaseManager()
        self.logger = get_logger("prisma_generator")
    
    def generate_flow_stats(self) -> Dict:
        """
        Generate statistics for PRISMA flow diagram.
        
        Returns:
            Dictionary with counts for each PRISMA stage
        """
        self.logger.info("Generating PRISMA flow statistics")
        
        # Get all papers
        papers = self.db.get_all_papers()
        
        # Initialize counters
        stats = {
            "identification": {
                "total_records": len(papers),
                "records_by_source": Counter(),
                "duplicates_removed": 0,  # Placeholder for future implementation
            },
            "screening": {
                "records_screened": 0,
                "records_excluded": 0,
                "exclusion_reasons": Counter(),
            },
            "eligibility": {
                "reports_sought": 0,
                "reports_not_retrieved": 0,
                "reports_assessed": 0,
                "reports_excluded": 0,
                "fulltext_exclusion_reasons": Counter(),
            },
            "included": {
                "studies_included": 0,
            },
        }
        
        # Process each paper
        for paper in papers:
            # Track sources
            for source in paper.sources:
                stats["identification"]["records_by_source"][source.value] += 1
            
            # Screening phase (abstract-based)
            if paper.status in [PaperStatus.SCREENED_IN, PaperStatus.SCREENED_OUT, 
                               PaperStatus.AWAITING_PDF, PaperStatus.PDF_ACQUIRED,
                               PaperStatus.TEXT_EXTRACTED, PaperStatus.SYNTHESIZED,
                               PaperStatus.VALIDATED, PaperStatus.ARCHIVED]:
                stats["screening"]["records_screened"] += 1
                
            if paper.status == PaperStatus.SCREENED_OUT:
                stats["screening"]["records_excluded"] += 1
                if paper.exclusion_reason:
                    stats["screening"]["exclusion_reasons"][paper.exclusion_reason.value] += 1
            
            # Eligibility phase (full-text)
            if paper.status in [PaperStatus.AWAITING_PDF, PaperStatus.PDF_ACQUIRED,
                               PaperStatus.TEXT_EXTRACTED, PaperStatus.SYNTHESIZED,
                               PaperStatus.VALIDATED, PaperStatus.ARCHIVED]:
                stats["eligibility"]["reports_sought"] += 1
            
            if paper.status == PaperStatus.AWAITING_PDF:
                stats["eligibility"]["reports_not_retrieved"] += 1
            
            if paper.status in [PaperStatus.PDF_ACQUIRED, PaperStatus.TEXT_EXTRACTED,
                               PaperStatus.SYNTHESIZED, PaperStatus.VALIDATED,
                               PaperStatus.ARCHIVED, PaperStatus.REJECTED]:
                stats["eligibility"]["reports_assessed"] += 1
            
            if paper.status == PaperStatus.REJECTED:
                stats["eligibility"]["reports_excluded"] += 1
                if paper.exclusion_reason:
                    stats["eligibility"]["fulltext_exclusion_reasons"][paper.exclusion_reason.value] += 1
            
            # Included studies
            if paper.status in [PaperStatus.VALIDATED, PaperStatus.ARCHIVED]:
                stats["included"]["studies_included"] += 1
        
        return stats
    
    def generate_text_report(self) -> str:
        """
        Generate text-based PRISMA flow report.
        
        Returns:
            Formatted text report
        """
        stats = self.generate_flow_stats()
        
        report = []
        report.append("="*80)
        report.append("PRISMA 2020 FLOW DIAGRAM")
        report.append("="*80)
        report.append("")
        
        # Identification
        report.append("IDENTIFICATION")
        report.append("-" * 40)
        report.append(f"Records identified from databases: {stats['identification']['total_records']}")
        
        if stats['identification']['records_by_source']:
            report.append("\nRecords by source:")
            for source, count in stats['identification']['records_by_source'].items():
                report.append(f"  • {source}: {count}")
        
        if stats['identification']['duplicates_removed'] > 0:
            report.append(f"\nDuplicates removed: {stats['identification']['duplicates_removed']}")
        
        report.append("")
        
        # Screening
        report.append("SCREENING")
        report.append("-" * 40)
        report.append(f"Records screened: {stats['screening']['records_screened']}")
        report.append(f"Records excluded: {stats['screening']['records_excluded']}")
        
        if stats['screening']['exclusion_reasons']:
            report.append("\nExclusion reasons (abstract screening):")
            for reason, count in sorted(stats['screening']['exclusion_reasons'].items(),
                                       key=lambda x: x[1], reverse=True):
                report.append(f"  • {reason.replace('_', ' ').title()}: {count}")
        
        report.append("")
        
        # Eligibility
        report.append("ELIGIBILITY")
        report.append("-" * 40)
        report.append(f"Reports sought for retrieval: {stats['eligibility']['reports_sought']}")
        report.append(f"Reports not retrieved: {stats['eligibility']['reports_not_retrieved']}")
        report.append(f"Reports assessed for eligibility: {stats['eligibility']['reports_assessed']}")
        report.append(f"Reports excluded: {stats['eligibility']['reports_excluded']}")
        
        if stats['eligibility']['fulltext_exclusion_reasons']:
            report.append("\nExclusion reasons (full-text review):")
            for reason, count in sorted(stats['eligibility']['fulltext_exclusion_reasons'].items(),
                                       key=lambda x: x[1], reverse=True):
                report.append(f"  • {reason.replace('_', ' ').title()}: {count}")
        
        report.append("")
        
        # Included
        report.append("INCLUDED")
        report.append("-" * 40)
        report.append(f"Studies included in review: {stats['included']['studies_included']}")
        
        report.append("")
        report.append("="*80)
        
        return "\n".join(report)
    
    def export_to_csv(self, output_path: str = "./data/prisma_stats.csv") -> None:
        """
        Export PRISMA statistics to CSV format.
        
        Args:
            output_path: Path to save CSV file
        """
        import csv
        
        stats = self.generate_flow_stats()
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["Stage", "Metric", "Count"])
            
            # Identification
            writer.writerow(["Identification", "Total Records", stats['identification']['total_records']])
            for source, count in stats['identification']['records_by_source'].items():
                writer.writerow(["Identification", f"Records from {source}", count])
            
            # Screening
            writer.writerow(["Screening", "Records Screened", stats['screening']['records_screened']])
            writer.writerow(["Screening", "Records Excluded", stats['screening']['records_excluded']])
            for reason, count in stats['screening']['exclusion_reasons'].items():
                writer.writerow(["Screening", f"Excluded: {reason}", count])
            
            # Eligibility
            writer.writerow(["Eligibility", "Reports Sought", stats['eligibility']['reports_sought']])
            writer.writerow(["Eligibility", "Reports Not Retrieved", stats['eligibility']['reports_not_retrieved']])
            writer.writerow(["Eligibility", "Reports Assessed", stats['eligibility']['reports_assessed']])
            writer.writerow(["Eligibility", "Reports Excluded", stats['eligibility']['reports_excluded']])
            for reason, count in stats['eligibility']['fulltext_exclusion_reasons'].items():
                writer.writerow(["Eligibility", f"Excluded: {reason}", count])
            
            # Included
            writer.writerow(["Included", "Studies Included", stats['included']['studies_included']])
        
        self.logger.info(f"PRISMA statistics exported to {output_file}")
        print(f"\n✅ PRISMA statistics exported to {output_file}")
    
    def generate_markdown_diagram(self) -> str:
        """
        Generate Markdown-formatted PRISMA flow diagram.
        
        Returns:
            Markdown representation of flow diagram
        """
        stats = self.generate_flow_stats()
        
        md = []
        md.append("# PRISMA 2020 Flow Diagram")
        md.append("")
        md.append("## Identification")
        md.append("")
        md.append(f"**Records identified from databases:** {stats['identification']['total_records']}")
        md.append("")
        
        if stats['identification']['records_by_source']:
            md.append("### Records by source:")
            for source, count in stats['identification']['records_by_source'].items():
                md.append(f"- {source}: {count}")
            md.append("")
        
        md.append("↓")
        md.append("")
        
        md.append("## Screening")
        md.append("")
        md.append(f"**Records screened:** {stats['screening']['records_screened']}")
        md.append("")
        md.append(f"**Records excluded ({stats['screening']['records_excluded']}):**")
        
        if stats['screening']['exclusion_reasons']:
            for reason, count in sorted(stats['screening']['exclusion_reasons'].items(),
                                       key=lambda x: x[1], reverse=True):
                md.append(f"- {reason.replace('_', ' ').title()}: {count}")
        md.append("")
        md.append("↓")
        md.append("")
        
        md.append("## Eligibility")
        md.append("")
        md.append(f"**Reports sought for retrieval:** {stats['eligibility']['reports_sought']}")
        md.append(f"**Reports not retrieved:** {stats['eligibility']['reports_not_retrieved']}")
        md.append("")
        md.append(f"**Reports assessed for eligibility:** {stats['eligibility']['reports_assessed']}")
        md.append("")
        md.append(f"**Reports excluded ({stats['eligibility']['reports_excluded']}):**")
        
        if stats['eligibility']['fulltext_exclusion_reasons']:
            for reason, count in sorted(stats['eligibility']['fulltext_exclusion_reasons'].items(),
                                       key=lambda x: x[1], reverse=True):
                md.append(f"- {reason.replace('_', ' ').title()}: {count}")
        md.append("")
        md.append("↓")
        md.append("")
        
        md.append("## Included")
        md.append("")
        md.append(f"**Studies included in review:** {stats['included']['studies_included']}")
        md.append("")
        
        return "\n".join(md)
    
    def export_to_markdown(self, output_path: str = "./data/PRISMA_FLOW.md") -> None:
        """
        Export PRISMA flow diagram to Markdown file.
        
        Args:
            output_path: Path to save Markdown file
        """
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        md = self.generate_markdown_diagram()
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(md)
        
        self.logger.info(f"PRISMA flow diagram exported to {output_file}")
        print(f"\n✅ PRISMA flow diagram exported to {output_file}")


def generate_prisma_report(output_formats: List[str] = ["text", "csv", "markdown"]) -> None:
    """
    Convenience function to generate PRISMA report in multiple formats.
    
    Args:
        output_formats: List of formats to generate ("text", "csv", "markdown")
    """
    generator = PRISMAFlowGenerator()
    
    if "text" in output_formats:
        report = generator.generate_text_report()
        print(report)
    
    if "csv" in output_formats:
        generator.export_to_csv()
    
    if "markdown" in output_formats:
        generator.export_to_markdown()
