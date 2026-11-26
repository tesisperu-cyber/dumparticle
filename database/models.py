from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Optional

SCHEMA = """
CREATE TABLE IF NOT EXISTS articles (
    collection TEXT NOT NULL, pid TEXT NOT NULL,
    doi TEXT, title TEXT, titles_all TEXT, authors TEXT, journal_title TEXT, issn TEXT,
    year INTEGER, doc_type TEXT, abstract TEXT, keywords TEXT,
    url_original TEXT, url_site TEXT, metadata_complete INTEGER DEFAULT 0,
    processing_date TEXT, fetched_at TEXT DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (collection, pid)
);
CREATE TABLE IF NOT EXISTS xml_files (
    collection TEXT NOT NULL, pid TEXT NOT NULL, fmt TEXT, path TEXT,
    http_status INTEGER, content_type TEXT, bytes INTEGER, sha256 TEXT,
    valid INTEGER, reasons TEXT, fetched_at TEXT DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (collection, pid)
);
CREATE TABLE IF NOT EXISTS fulltext (
    collection TEXT NOT NULL, pid TEXT NOT NULL, title TEXT, authors TEXT, affiliations TEXT,
    abstracts TEXT, keywords TEXT, sections TEXT, ref_count INTEGER, refs TEXT,
    has_body INTEGER, extracted_at TEXT DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (collection, pid)
);
CREATE TABLE IF NOT EXISTS runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT, started_at TEXT, finished_at TEXT,
    config TEXT, diagnostics TEXT
);
"""


@dataclass
class ArticleRecord:
    collection: str
    pid: str
    doi: Optional[str] = None
    title: Optional[str] = None
    titles_all: dict = field(default_factory=dict)
    authors: list = field(default_factory=list)
    journal_title: Optional[str] = None
    issn: Optional[str] = None
    year: Optional[int] = None
    doc_type: Optional[str] = None
    abstract: Optional[str] = None
    keywords: list = field(default_factory=list)
    url_original: Optional[str] = None
    url_site: Optional[str] = None
    processing_date: Optional[str] = None
    collections: list = field(default_factory=list)  # tras deduplicar

    @property
    def metadata_complete(self) -> bool:
        return bool(self.pid and self.title and self.year and self.journal_title)

    def search_fields(self):
        return (" . ".join(self.titles_all.values()) if self.titles_all else self.title,
                self.abstract, " ; ".join(self.keywords))

    def to_dict(self):
        return asdict(self)
