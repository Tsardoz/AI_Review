"""
SQLite database layer for the literature review system.

Provides CRUD operations for Papers, Summaries, Citations, and caching.
Uses raw SQL for simplicity and performance.
"""

import sqlite3
import json
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from contextlib import contextmanager

from .models import (
    Paper, PaperSource, PaperStatus, SearchResult, Summary, Citation,
    ProcessingCheckpoint, CacheEntry
)
from ..utils.logger import get_logger


class DatabaseManager:
    """Manage SQLite database operations."""
    
    def __init__(self, db_path: str = "./data/literature_review.db"):
        """Initialize database manager."""
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.logger = get_logger("database")
        self._initialize_db()
    
    @contextmanager
    def get_connection(self):
        """Context manager for database connections."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            self.logger.error(f"Database error: {str(e)}")
            raise
        finally:
            conn.close()
    
    def _initialize_db(self):
        """Create tables if they don't exist."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Papers table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS papers (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    authors TEXT NOT NULL DEFAULT '[]',
                    abstract TEXT,
                    doi TEXT UNIQUE,
                    url TEXT,
                    pdf_url TEXT,
                    year INTEGER NOT NULL,
                    journal TEXT,
                    conference TEXT,
                    volume TEXT,
                    issue TEXT,
                    pages TEXT,
                    sources TEXT NOT NULL DEFAULT '[]',
                    source_ids TEXT NOT NULL DEFAULT '{}',
                    status TEXT NOT NULL DEFAULT 'discovered',
                    discovered_at TEXT NOT NULL,
                    last_updated TEXT NOT NULL,
                    citation_count INTEGER DEFAULT 0,
                    relevance_score REAL,
                    quality_score REAL,
                    pdf_path TEXT,
                    full_text TEXT,
                    metadata TEXT DEFAULT '{}'
                )
            """)
            
            # Summaries table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS summaries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    paper_id TEXT NOT NULL UNIQUE,
                    abstract TEXT NOT NULL,
                    key_contributions TEXT DEFAULT '[]',
                    methodology TEXT,
                    findings TEXT,
                    limitations TEXT,
                    future_work TEXT,
                    generated_at TEXT NOT NULL,
                    llm_provider TEXT NOT NULL,
                    llm_model TEXT NOT NULL,
                    tokens_used INTEGER DEFAULT 0,
                    cost_usd REAL DEFAULT 0,
                    quality_score REAL,
                    hallucination_risk REAL,
                    manually_reviewed INTEGER DEFAULT 0,
                    reviewer_notes TEXT,
                    metadata TEXT DEFAULT '{}',
                    FOREIGN KEY (paper_id) REFERENCES papers(id)
                )
            """)
            
            # Citations table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS citations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    paper_id TEXT NOT NULL UNIQUE,
                    bibtex TEXT,
                    chicago_author_date TEXT,
                    mla TEXT,
                    apa TEXT,
                    validated INTEGER DEFAULT 0,
                    doi_validated INTEGER DEFAULT 0,
                    url_validated INTEGER DEFAULT 0,
                    validation_errors TEXT DEFAULT '[]',
                    generated_at TEXT NOT NULL,
                    metadata TEXT DEFAULT '{}',
                    FOREIGN KEY (paper_id) REFERENCES papers(id)
                )
            """)
            
            # Checkpoints table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS checkpoints (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    stage TEXT NOT NULL,
                    status TEXT NOT NULL,
                    papers_processed INTEGER DEFAULT 0,
                    papers_total INTEGER DEFAULT 0,
                    started_at TEXT NOT NULL,
                    completed_at TEXT,
                    error_message TEXT,
                    metadata TEXT DEFAULT '{}',
                    created_at TEXT NOT NULL
                )
            """)
            
            # Cache table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS cache (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    cache_key TEXT NOT NULL UNIQUE,
                    source TEXT NOT NULL,
                    data TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    hits INTEGER DEFAULT 0
                )
            """)
            
            # Create indices for performance
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_papers_doi ON papers(doi)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_papers_status ON papers(status)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_papers_year ON papers(year)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_summaries_paper_id ON summaries(paper_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_citations_paper_id ON citations(paper_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_cache_expires ON cache(expires_at)")
            
            self.logger.info("Database initialized successfully")
    
    # === Paper Operations ===
    
    def save_paper(self, paper: Paper) -> bool:
        """Save or update a paper."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Check if paper exists
                cursor.execute("SELECT id FROM papers WHERE id = ?", (paper.id,))
                exists = cursor.fetchone() is not None
                
                json_fields = {
                    'authors': json.dumps(paper.authors),
                    'sources': json.dumps([s.value for s in paper.sources]),
                    'source_ids': json.dumps(paper.source_ids),
                    'metadata': json.dumps(paper.metadata),
                }
                
                if exists:
                    cursor.execute("""
                        UPDATE papers SET
                            title = ?, abstract = ?, doi = ?, url = ?, pdf_url = ?,
                            year = ?, journal = ?, conference = ?, volume = ?, issue = ?, pages = ?,
                            sources = ?, source_ids = ?, status = ?, last_updated = ?,
                            citation_count = ?, relevance_score = ?, quality_score = ?,
                            pdf_path = ?, full_text = ?, metadata = ?
                        WHERE id = ?
                    """, (
                        paper.title, paper.abstract, paper.doi, paper.url, paper.pdf_url,
                        paper.year, paper.journal, paper.conference, paper.volume, paper.issue, paper.pages,
                        json_fields['sources'], json_fields['source_ids'], paper.status.value, paper.last_updated.isoformat(),
                        paper.citation_count, paper.relevance_score, paper.quality_score,
                        paper.pdf_path, paper.full_text, json_fields['metadata'],
                        paper.id
                    ))
                else:
                    cursor.execute("""
                        INSERT INTO papers (
                            id, title, authors, abstract, doi, url, pdf_url,
                            year, journal, conference, volume, issue, pages,
                            sources, source_ids, status, discovered_at, last_updated,
                            citation_count, relevance_score, quality_score,
                            pdf_path, full_text, metadata
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        paper.id, paper.title, json_fields['authors'], paper.abstract, paper.doi,
                        paper.url, paper.pdf_url, paper.year, paper.journal, paper.conference,
                        paper.volume, paper.issue, paper.pages,
                        json_fields['sources'], json_fields['source_ids'], paper.status.value,
                        paper.discovered_at.isoformat(), paper.last_updated.isoformat(),
                        paper.citation_count, paper.relevance_score, paper.quality_score,
                        paper.pdf_path, paper.full_text, json_fields['metadata']
                    ))
                
                self.logger.debug(f"Paper saved: {paper.id}")
                return True
        except Exception as e:
            self.logger.error(f"Error saving paper: {str(e)}")
            return False
    
    def get_paper(self, paper_id: str) -> Optional[Paper]:
        """Retrieve a paper by ID."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM papers WHERE id = ?", (paper_id,))
                row = cursor.fetchone()
                
                if not row:
                    return None
                
                return self._row_to_paper(row)
        except Exception as e:
            self.logger.error(f"Error retrieving paper: {str(e)}")
            return None
    
    def get_papers_by_status(self, status: PaperStatus, limit: int = 100) -> List[Paper]:
        """Get papers by status."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT * FROM papers WHERE status = ? ORDER BY last_updated DESC LIMIT ?",
                    (status.value, limit)
                )
                return [self._row_to_paper(row) for row in cursor.fetchall()]
        except Exception as e:
            self.logger.error(f"Error retrieving papers by status: {str(e)}")
            return []
    
    def get_all_papers(self, limit: int = None) -> List[Paper]:
        """Get all papers."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                query = "SELECT * FROM papers ORDER BY last_updated DESC"
                if limit:
                    query += f" LIMIT {limit}"
                cursor.execute(query)
                return [self._row_to_paper(row) for row in cursor.fetchall()]
        except Exception as e:
            self.logger.error(f"Error retrieving all papers: {str(e)}")
            return []
    
    def count_papers(self, status: Optional[PaperStatus] = None) -> int:
        """Count papers, optionally by status."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                if status:
                    cursor.execute("SELECT COUNT(*) FROM papers WHERE status = ?", (status.value,))
                else:
                    cursor.execute("SELECT COUNT(*) FROM papers")
                return cursor.fetchone()[0]
        except Exception as e:
            self.logger.error(f"Error counting papers: {str(e)}")
            return 0
    
    def _row_to_paper(self, row) -> Paper:
        """Convert database row to Paper object."""
        return Paper(
            id=row['id'],
            title=row['title'],
            authors=json.loads(row['authors']),
            abstract=row['abstract'],
            doi=row['doi'],
            url=row['url'],
            pdf_url=row['pdf_url'],
            year=row['year'],
            journal=row['journal'],
            conference=row['conference'],
            volume=row['volume'],
            issue=row['issue'],
            pages=row['pages'],
            sources=[PaperSource(s) for s in json.loads(row['sources'])],
            source_ids=json.loads(row['source_ids']),
            status=PaperStatus(row['status']),
            discovered_at=datetime.fromisoformat(row['discovered_at']),
            last_updated=datetime.fromisoformat(row['last_updated']),
            citation_count=row['citation_count'],
            relevance_score=row['relevance_score'],
            quality_score=row['quality_score'],
            pdf_path=row['pdf_path'],
            full_text=row['full_text'],
            metadata=json.loads(row['metadata'])
        )
    
    # === Summary Operations ===
    
    def save_summary(self, summary: Summary) -> bool:
        """Save a summary."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO summaries (
                        paper_id, abstract, key_contributions, methodology, findings,
                        limitations, future_work, generated_at, llm_provider, llm_model,
                        tokens_used, cost_usd, quality_score, hallucination_risk,
                        manually_reviewed, reviewer_notes, metadata
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    summary.paper_id, summary.abstract,
                    json.dumps(summary.key_contributions),
                    summary.methodology, summary.findings,
                    summary.limitations, summary.future_work,
                    summary.generated_at.isoformat(), summary.llm_provider, summary.llm_model,
                    summary.tokens_used, summary.cost_usd, summary.quality_score,
                    summary.hallucination_risk, int(summary.manually_reviewed),
                    summary.reviewer_notes, json.dumps(summary.metadata)
                ))
                return True
        except Exception as e:
            self.logger.error(f"Error saving summary: {str(e)}")
            return False
    
    def get_summary(self, paper_id: str) -> Optional[Summary]:
        """Retrieve a summary by paper ID."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM summaries WHERE paper_id = ?", (paper_id,))
                row = cursor.fetchone()
                
                if not row:
                    return None
                
                return Summary(
                    paper_id=row['paper_id'],
                    abstract=row['abstract'],
                    key_contributions=json.loads(row['key_contributions']),
                    methodology=row['methodology'],
                    findings=row['findings'],
                    limitations=row['limitations'],
                    future_work=row['future_work'],
                    generated_at=datetime.fromisoformat(row['generated_at']),
                    llm_provider=row['llm_provider'],
                    llm_model=row['llm_model'],
                    tokens_used=row['tokens_used'],
                    cost_usd=row['cost_usd'],
                    quality_score=row['quality_score'],
                    hallucination_risk=row['hallucination_risk'],
                    manually_reviewed=bool(row['manually_reviewed']),
                    reviewer_notes=row['reviewer_notes'],
                    metadata=json.loads(row['metadata'])
                )
        except Exception as e:
            self.logger.error(f"Error retrieving summary: {str(e)}")
            return None
    
    # === Citation Operations ===
    
    def save_citation(self, citation: Citation) -> bool:
        """Save a citation."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO citations (
                        paper_id, bibtex, chicago_author_date, mla, apa,
                        validated, doi_validated, url_validated, validation_errors,
                        generated_at, metadata
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    citation.paper_id, citation.bibtex, citation.chicago_author_date,
                    citation.mla, citation.apa,
                    int(citation.validated), int(citation.doi_validated),
                    int(citation.url_validated), json.dumps(citation.validation_errors),
                    citation.generated_at.isoformat(), json.dumps(citation.metadata)
                ))
                return True
        except Exception as e:
            self.logger.error(f"Error saving citation: {str(e)}")
            return False
    
    def get_citation(self, paper_id: str) -> Optional[Citation]:
        """Retrieve a citation by paper ID."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM citations WHERE paper_id = ?", (paper_id,))
                row = cursor.fetchone()
                
                if not row:
                    return None
                
                return Citation(
                    paper_id=row['paper_id'],
                    bibtex=row['bibtex'],
                    chicago_author_date=row['chicago_author_date'],
                    mla=row['mla'],
                    apa=row['apa'],
                    validated=bool(row['validated']),
                    doi_validated=bool(row['doi_validated']),
                    url_validated=bool(row['url_validated']),
                    validation_errors=json.loads(row['validation_errors']),
                    generated_at=datetime.fromisoformat(row['generated_at']),
                    metadata=json.loads(row['metadata'])
                )
        except Exception as e:
            self.logger.error(f"Error retrieving citation: {str(e)}")
            return None
    
    # === Cache Operations ===
    
    def get_cached_result(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Retrieve cached search result if still valid."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT data, expires_at FROM cache WHERE cache_key = ?",
                    (cache_key,)
                )
                row = cursor.fetchone()
                
                if not row:
                    return None
                
                expires_at = datetime.fromisoformat(row['expires_at'])
                if expires_at < datetime.utcnow():
                    # Cache expired
                    cursor.execute("DELETE FROM cache WHERE cache_key = ?", (cache_key,))
                    return None
                
                # Update hit count
                cursor.execute(
                    "UPDATE cache SET hits = hits + 1 WHERE cache_key = ?",
                    (cache_key,)
                )
                
                return json.loads(row['data'])
        except Exception as e:
            self.logger.error(f"Error retrieving cached result: {str(e)}")
            return None
    
    def cache_search_result(self, cache_key: str, source: PaperSource, data: Dict[str, Any], ttl_hours: int = 24):
        """Cache search result for later retrieval."""
        try:
            expires_at = datetime.utcnow() + timedelta(hours=ttl_hours)
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO cache (cache_key, source, data, created_at, expires_at)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    cache_key, source.value, json.dumps(data),
                    datetime.utcnow().isoformat(), expires_at.isoformat()
                ))
                self.logger.debug(f"Cached result: {cache_key}")
        except Exception as e:
            self.logger.error(f"Error caching result: {str(e)}")
    
    def cleanup_expired_cache(self):
        """Remove expired cache entries."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM cache WHERE expires_at < ?", (datetime.utcnow().isoformat(),))
                deleted = cursor.rowcount
                self.logger.info(f"Cleaned up {deleted} expired cache entries")
        except Exception as e:
            self.logger.error(f"Error cleaning cache: {str(e)}")
    
    # === Checkpoint Operations ===
    
    def save_checkpoint(self, checkpoint: ProcessingCheckpoint) -> bool:
        """Save a processing checkpoint."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO checkpoints (
                        stage, status, papers_processed, papers_total,
                        started_at, completed_at, error_message, metadata, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    checkpoint.stage, checkpoint.status, checkpoint.papers_processed,
                    checkpoint.papers_total, checkpoint.started_at.isoformat(),
                    checkpoint.completed_at.isoformat() if checkpoint.completed_at else None,
                    checkpoint.error_message, json.dumps(checkpoint.metadata),
                    datetime.utcnow().isoformat()
                ))
                return True
        except Exception as e:
            self.logger.error(f"Error saving checkpoint: {str(e)}")
            return False
    
    def get_latest_checkpoint(self, stage: str) -> Optional[ProcessingCheckpoint]:
        """Get latest checkpoint for a stage."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT * FROM checkpoints WHERE stage = ? ORDER BY created_at DESC LIMIT 1",
                    (stage,)
                )
                row = cursor.fetchone()
                
                if not row:
                    return None
                
                return ProcessingCheckpoint(
                    stage=row['stage'],
                    status=row['status'],
                    papers_processed=row['papers_processed'],
                    papers_total=row['papers_total'],
                    started_at=datetime.fromisoformat(row['started_at']),
                    completed_at=datetime.fromisoformat(row['completed_at']) if row['completed_at'] else None,
                    error_message=row['error_message'],
                    metadata=json.loads(row['metadata'])
                )
        except Exception as e:
            self.logger.error(f"Error retrieving checkpoint: {str(e)}")
            return None


# Global database instance
_db_manager: Optional[DatabaseManager] = None


def get_db() -> DatabaseManager:
    """Get or create global database manager."""
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
    return _db_manager
