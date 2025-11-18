"""
Agent modules for the literature review system.

Provides specialized agents for different stages of the literature
review pipeline.
"""

from .research_agent import ResearchAgent
# Stage 3+ agents will be imported as they are implemented
# from .quality_agent import QualityAgent
# from .acquisition_agent import AcquisitionAgent
# from .summarizer_agent import SummarizerAgent
# from .citation_agent import CitationAgent

__all__ = [
    'ResearchAgent',
    # 'QualityAgent', 
    # 'AcquisitionAgent',
    # 'SummarizerAgent',
    # 'CitationAgent'
]
