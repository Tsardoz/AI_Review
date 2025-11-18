"""
Integration modules for external APIs and data sources.

Provides clients for academic databases and other external services.
"""

from .semantic_scholar import SemanticScholarAPI
from .crossref import CrossRefAPI
from .arxiv import ArXivAPI

__all__ = [
    'SemanticScholarAPI',
    'CrossRefAPI',
    'ArXivAPI'
]