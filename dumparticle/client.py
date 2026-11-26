"""Conectores de búsqueda SciELO y descarga XML mediante ArticleMeta."""
from __future__ import annotations
import os, time, re
from typing import Any
from urllib.parse import urljoin
import requests

class ArticleMetaError(RuntimeError):
    """Error controlado al consultar servicios SciELO."""

class ArticleMetaClient:
    def __init__(self, base_url=None, timeout=None, page_size=None, session=None,
                 pause_seconds=0.25, search_url=None):
        self.base_url = (base_url or os.getenv("SCIELO_ARTICLEMETA_URL",
            "https://articlemeta.scielo.org/api/v1/")).rstrip("/") + "/"
        self.search_url = search_url or os.getenv("SCIELO_SEARCH_URL", "https://search.scielo.org/")
        self.timeout = timeout or float(os.getenv("SCIELO_TIMEOUT", "45"))
        self.page_size = page_size or int(os.getenv("SCIELO_PAGE_SIZE", "50"))
        self.session = session or requests.Session()
        self.pause_seconds = max(0.0, pause_seconds)
        self.session.headers.update({"User-Agent": "DumpArticle-SciELO/0.2.0 (academic literature retrieval)"})

    def _get(self, url, params=None):
        last_error = None
        for attempt in range(3):
            try:
                response = self.session.get(url, params=params, timeout=self.timeout)
                response.raise_for_status()
                return response
            except requests.RequestException as exc:
                last_error = exc
                if attempt < 2:
                    retry_after = response.headers.get("Retry-After") if "response" in locals() else None
                    try: delay = float(retry_after) if retry_after else 1.5 * (attempt + 1)
                    except ValueError: delay = 1.5 * (attempt + 1)
                    time.sleep(min(delay, 15))
        raise ArticleMetaError(f"Fallo al consultar {url}: {last_error}") from last_error

    def search_articles(self, query, collection=None, issn=None, year_from=None,
                        year_to=None, language=None, limit=50):
        """Descubre artículos por tema mediante SciELO Search."""
        query = (query or "").strip()
        if not query: raise ValueError("Escribe un tema o expresión de búsqueda.")
        if limit < 1: raise ValueError("El límite debe ser mayor que cero.")
        params = {"q": query, "format": "json", "count": min(max(limit, 1), 100)}
        if language and language.lower() not in {"all", "todos"}: params["lang"] = language.lower()
        response = self._get(self.search_url, params=params)
        try: payload = response.json()
        except ValueError as exc:
            raise ArticleMetaError("SciELO Search no devolvió JSON. La interfaz puede haber cambiado o estar bloqueando la consulta.") from exc
        docs = _extract_documents(payload)
        if not docs:
            raise ArticleMetaError("La respuesta de SciELO Search no contiene una lista reconocible de artículos. No se continuará con identificadores generales.")
        rows, wanted_issn = [], _normalize_issn(issn) if issn else ""
        for doc in docs:
            row = _normalize_search_doc(doc)
            if not row["code"]: continue
            if collection and row["collection"] and row["collection"].lower() != collection.lower(): continue
            if wanted_issn and _normalize_issn(row["issn"]) != wanted_issn: continue
            if year_from and row["year"].isdigit() and int(row["year"]) < year_from: continue
            if year_to and row["year"].isdigit() and int(row["year"]) > year_to: continue
            row["search_query"] = query
            rows.append(row)
            if len(rows) >= limit: break
        return rows

    def get_article_xml(self, code, xml_format="xmlrsps"):
        if xml_format not in {"xmlrsps", "xmlwos"}: raise ValueError("xml_format debe ser 'xmlrsps' o 'xmlwos'.")
        response = self._get(urljoin(self.base_url, "article"), {"code": code, "format": xml_format})
        content = response.text
        if not content.strip(): raise ArticleMetaError(f"Respuesta XML vacía para el código {code}.")
        if not content.lstrip().startswith("<"): raise ArticleMetaError(f"La respuesta para {code} no parece ser XML.")
        return content

def _extract_documents(payload: Any):
    candidates = []
    if isinstance(payload, list): candidates.append(payload)
    elif isinstance(payload, dict):
        for key in ("docs", "results", "objects", "articles", "records"):
            if isinstance(payload.get(key), list): candidates.append(payload[key])
        response = payload.get("response")
        if isinstance(response, dict) and isinstance(response.get("docs"), list): candidates.append(response["docs"])
        data = payload.get("data")
        if isinstance(data, dict):
            for key in ("docs", "results", "objects", "articles"):
                if isinstance(data.get(key), list): candidates.append(data[key])
    for candidate in candidates:
        if candidate and all(isinstance(item, dict) for item in candidate): return candidate
    return []

def _first(value):
    if isinstance(value, list): return _first(value[0]) if value else ""
    if isinstance(value, dict):
        for key in ("en", "es", "pt", "value", "text"):
            if value.get(key): return _first(value[key])
        return ""
    return str(value).strip() if value is not None else ""

def _normalize_search_doc(doc):
    code = _first(doc.get("pid") or doc.get("code") or doc.get("article_pid") or doc.get("id"))
    title = _first(doc.get("title") or doc.get("title_display") or doc.get("article_title"))
    authors = doc.get("authors") or doc.get("author") or doc.get("author_display") or ""
    if isinstance(authors, list): authors = "; ".join(_first(a) for a in authors if _first(a))
    journal = _first(doc.get("journal_title") or doc.get("ta") or doc.get("journal") or doc.get("source"))
    year = _first(doc.get("publication_year") or doc.get("year") or doc.get("date"))
    year_match = re.search(r"(19|20)\d{2}", year or "")
    doi = _first(doc.get("doi") or doc.get("DOI"))
    issn = _first(doc.get("issn") or doc.get("journal_issn"))
    collection = _first(doc.get("collection") or doc.get("in"))
    language = _first(doc.get("la") or doc.get("language"))
    abstract = _first(doc.get("abstract") or doc.get("description"))
    url = _first(doc.get("url") or doc.get("link") or doc.get("url_document"))
    return {"code":code,"title":title,"authors":str(authors),"journal":journal,
            "year":year_match.group(0) if year_match else "", "doi":doi,"issn":issn,
            "collection":collection,"language":language,"abstract":abstract,"url":url}

def _normalize_issn(value):
    return "".join(ch for ch in value.upper() if ch.isalnum())
