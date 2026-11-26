"""Deduplicación: clave por DOI normalizado; si no hay, título normalizado+año;
si no, (colección, PID). Fusiona colecciones y conserva el registro más completo."""
from __future__ import annotations
from database.models import ArticleRecord
from .normalizer import normalize_text


def dedup_key(r: ArticleRecord) -> tuple:
    if r.doi:
        return ("doi", r.doi.lower().strip().removeprefix("https://doi.org/").removeprefix("http://dx.doi.org/"))
    if r.title and r.year:
        return ("ty", normalize_text(r.title), r.year)
    return ("pid", r.collection, r.pid)


def _score(r: ArticleRecord) -> int:
    return sum(bool(x) for x in (r.doi, r.title, r.abstract, r.keywords, r.authors, r.journal_title, r.year, r.issn))


def deduplicate(records: list[ArticleRecord]) -> list[ArticleRecord]:
    best: dict = {}
    cols: dict = {}
    for r in records:
        k = dedup_key(r)
        cols.setdefault(k, [])
        if r.collection not in cols[k]:
            cols[k].append(r.collection)
        if k not in best or _score(r) > _score(best[k]):
            best[k] = r
    out = []
    for k, r in best.items():
        r.collections = cols[k]
        out.append(r)
    return out
