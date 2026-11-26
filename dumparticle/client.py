"""Cliente HTTP para la API SciELO ArticleMeta."""
from __future__ import annotations

import os
import time
from typing import Any, Iterator

import requests


class ArticleMetaError(RuntimeError):
    """Error controlado al consultar ArticleMeta."""


class ArticleMetaClient:
    def __init__(
        self,
        base_url: str | None = None,
        timeout: int | float | None = None,
        page_size: int | None = None,
        session: requests.Session | None = None,
        pause_seconds: float = 0.0,
    ) -> None:
        self.base_url = (base_url or os.getenv(
            "SCIELO_ARTICLEMETA_URL",
            "https://articlemeta.scielo.org/api/v1/"
        )).rstrip("/") + "/"
        self.timeout = timeout or float(os.getenv("SCIELO_TIMEOUT", "45"))
        self.page_size = page_size or int(os.getenv("SCIELO_PAGE_SIZE", "1000"))
        self.session = session or requests.Session()
        self.pause_seconds = max(0.0, pause_seconds)
        self.session.headers.update({"User-Agent": "DumpArticle-SciELO/0.1.0"})

    def _get(self, endpoint: str, params: dict[str, Any] | None = None) -> requests.Response:
        url = self.base_url + endpoint.lstrip("/")
        last_error: Exception | None = None
        for attempt in range(3):
            try:
                response = self.session.get(url, params=params, timeout=self.timeout)
                response.raise_for_status()
                return response
            except requests.RequestException as exc:
                last_error = exc
                if attempt < 2:
                    time.sleep(1.5 * (attempt + 1))
        raise ArticleMetaError(f"Fallo al consultar {url}: {last_error}") from last_error

    def iter_identifiers(
        self,
        collection: str | None = None,
        issn: str | None = None,
        code: str | None = None,
        limit: int | None = None,
    ) -> list[dict[str, str]]:
        """Recorre identificadores paginados y aplica filtros locales."""
        offset = 0
        found: list[dict[str, str]] = []
        normalized_issn = _normalize_issn(issn) if issn else None

        while True:
            response = self._get("article/identifiers", {"offset": offset})
            try:
                payload = response.json()
            except ValueError as exc:
                raise ArticleMetaError("ArticleMeta devolvió una respuesta que no es JSON.") from exc

            objects = payload.get("objects", []) if isinstance(payload, dict) else []
            if not objects:
                break

            for item in objects:
                item_collection = str(item.get("collection", "")).strip()
                item_code = str(item.get("code", "")).strip()
                item_issn = _issn_from_code(item_code)

                if collection and item_collection.lower() != collection.lower():
                    continue
                if code and item_code.lower() != code.lower():
                    continue
                if normalized_issn and _normalize_issn(item_issn) != normalized_issn:
                    continue

                found.append({
                    "collection": item_collection,
                    "code": item_code,
                    "issn": item_issn,
                })
                if limit is not None and len(found) >= limit:
                    return found

            offset += self.page_size
            if self.pause_seconds:
                time.sleep(self.pause_seconds)

        return found

    def get_article_xml(self, code: str, xml_format: str = "xmlrsps") -> str:
        if xml_format not in {"xmlrsps", "xmlwos"}:
            raise ValueError("xml_format debe ser 'xmlrsps' o 'xmlwos'.")
        response = self._get("article", {"code": code, "format": xml_format})
        content = response.text
        if not content.strip():
            raise ArticleMetaError(f"Respuesta XML vacía para el código {code}.")
        return content


def _normalize_issn(value: str) -> str:
    return "".join(ch for ch in value.upper() if ch.isalnum())


def _issn_from_code(code: str) -> str:
    """Intenta obtener el ISSN de códigos SciELO habituales; no lo inventa."""
    # Los identificadores clásicos contienen el ISSN después del prefijo de colección.
    if len(code) >= 14 and code[0].isalpha():
        candidate = code[1:10]
        if len(candidate) == 9 and candidate[4] == "-":
            return candidate
    return ""
