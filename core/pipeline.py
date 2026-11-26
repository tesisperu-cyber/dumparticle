"""Orquesta: cosecha -> deduplicación -> XML -> extracción -> almacenamiento -> diagnóstico."""
from __future__ import annotations
from datetime import datetime, timezone
from dataclasses import asdict
from .client import HttpClient
from .articlemeta import ArticleMetaClient
from .harvester import Harvester
from .deduplicator import deduplicate
from .xml_downloader import XmlDownloader
from .jats_parser import parse_jats
from .diagnostics import Diagnostics
from database.repository import Repository


def run_search(settings, am_factory=None):
    started = datetime.now(timezone.utc).isoformat()
    diag = Diagnostics()
    repo = Repository(settings.db_path)
    http = HttpClient(settings, diag)
    am = am_factory(http, settings) if am_factory else ArticleMetaClient(http, settings)
    am.collections()  # carga dominios de colección (si responde)
    matches = deduplicate(Harvester(settings, am, repo, diag).run())[: settings.max_results]
    if settings.download_xml:
        dl = XmlDownloader(settings, am, repo, diag)
        for rec in matches:
            out = dl.download(rec)
            if out.ok:
                parsed = parse_jats(out.content)
                if not rec.doi and parsed.get("doi"):
                    rec.doi = parsed["doi"]
                    repo.upsert_article(rec)
                if parsed["has_body"]:
                    repo.upsert_fulltext(rec.collection, rec.pid, parsed)
                    diag.inc("fulltext_ok", collection=rec.collection)
                else:
                    diag.note(f"{rec.collection}/{rec.pid}: XML válido sin cuerpo (solo metadatos/resumen)")
    repo.save_run(started, datetime.now(timezone.utc).isoformat(), asdict(settings), diag.to_dict())
    return matches, diag, repo
