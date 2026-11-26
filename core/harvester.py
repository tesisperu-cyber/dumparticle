"""Cosechador: descubrimiento (identificadores) -> metadatos -> filtros -> ecuación booleana.
Usa caché SQLite para no repetir peticiones. Respeta límites por colección y por tiempo."""
from __future__ import annotations
import time
from database.models import ArticleRecord
from .articlemeta import ArticleMetaClient, parse_article_json
from .boolean_engine import compile_query
from .diagnostics import Diagnostics


class Harvester:
    def __init__(self, settings, am: ArticleMetaClient, repo, diag: Diagnostics):
        self.s, self.am, self.repo, self.diag = settings, am, repo, diag
        self.query = compile_query(settings.equation) if settings.equation.strip() else None

    def _filters_ok(self, r: ArticleRecord) -> bool:
        s = self.s
        if s.year_from and (r.year is None or r.year < s.year_from):
            return False
        if s.year_to and (r.year is None or r.year > s.year_to):
            return False
        if s.issn and (not r.issn or r.issn.replace("-", "") != s.issn.replace("-", "")):
            return False
        if s.doc_type and (not r.doc_type or r.doc_type.lower() != s.doc_type.lower()):
            return False
        return True

    def fetch_record(self, collection: str, pid: str) -> ArticleRecord | None:
        cached = self.repo.get_article(collection, pid)
        if cached:
            return cached
        self.diag.inc("requested", collection=collection)
        res = self.am.article_json(collection, pid)
        if not res.ok:
            return None
        try:
            data = res.json()
        except ValueError:
            self.diag.http_error("json_invalido:article")
            return None
        self.diag.inc("received", collection=collection)
        rec = parse_article_json(data, collection, res.url, self.am.domain(collection))
        rec.pid = rec.pid or pid
        rec.collection = rec.collection or collection
        self.repo.upsert_article(rec)
        return rec

    def run(self) -> list[ArticleRecord]:
        matches: list[ArticleRecord] = []
        for col in self.s.collections:
            t0, seen = time.time(), 0
            for ident in self.am.iter_identifiers(col, issn=self.s.issn):
                if len(matches) >= self.s.max_results:
                    self.diag.note(f"Se alcanzó max_results={self.s.max_results}")
                    return matches
                if seen >= self.s.max_records_per_collection:
                    self.diag.note(f"[{col}] límite de registros por colección ({seen})")
                    break
                if time.time() - t0 > self.s.max_seconds_per_collection:
                    self.diag.note(f"[{col}] límite de tiempo ({self.s.max_seconds_per_collection}s)")
                    break
                self.diag.identifiers_listed += 1
                pid = ident.get("code") if isinstance(ident, dict) else None
                if not pid:
                    continue
                seen += 1
                rec = self.fetch_record(col, pid)
                if rec is None:
                    continue
                if not rec.doi and isinstance(ident, dict):
                    rec.doi = ident.get("doi")
                if rec.metadata_complete:
                    self.diag.inc("complete", collection=col)
                else:
                    self.diag.inc("incomplete", collection=col)
                if not self._filters_ok(rec):
                    continue
                self.diag.inc("temporal_ok", collection=col)
                if self.query and not self.query.matches(*rec.search_fields()):
                    continue
                self.diag.inc("thematic_ok", collection=col)
                if rec.pid:
                    self.diag.inc("identified", collection=col)
                matches.append(rec)
        return matches
