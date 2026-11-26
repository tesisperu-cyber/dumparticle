"""Descarga XML individuales y genera ZIP más manifiesto CSV."""
from __future__ import annotations

import csv
import io
import re
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Iterable

from .client import ArticleMetaClient


def _safe_part(value: str, fallback: str = "unknown") -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", str(value or "")).strip("._")
    return cleaned or fallback


def dump_articles(
    client: ArticleMetaClient,
    identifiers: Iterable[dict[str, str]],
    output_path: str | Path,
    xml_format: str = "xmlrsps",
    progress_callback: Callable[[int, int], None] | None = None,
) -> dict:
    items = list(identifiers)
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    manifest: list[dict[str, str]] = []
    downloaded = 0
    failed = 0

    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, allowZip64=True) as archive:
        for index, item in enumerate(items, start=1):
            collection = item.get("collection", "")
            code = item.get("code", "")
            issn = item.get("issn", "") or "ISSN_no_identificado"
            status = "ERROR"
            error = ""
            xml_path = ""

            try:
                xml_text = client.get_article_xml(code, xml_format=xml_format, collection=collection)
                collection_folder = _safe_part(collection)
                issn_folder = _safe_part(issn)
                filename = _safe_part(code) + ".xml"
                xml_path = f"{collection_folder}/{issn_folder}/{filename}"
                archive.writestr(xml_path, xml_text.encode("utf-8"))
                status = "DESCARGADO"
                downloaded += 1
            except Exception as exc:  # se conserva el fallo en el manifiesto
                error = str(exc)[:500]
                failed += 1

            manifest.append({
                "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                "collection": collection,
                "issn": issn,
                "code": code,
                "title": item.get("title", ""),
                "authors": item.get("authors", ""),
                "journal": item.get("journal", ""),
                "year": item.get("year", ""),
                "doi": item.get("doi", ""),
                "language": item.get("language", ""),
                "source_url": item.get("url", ""),
                "search_query": item.get("search_query", ""),
                "xml_format": xml_format,
                "status": status,
                "zip_path": xml_path,
                "error": error,
            })
            if progress_callback:
                progress_callback(index, len(items))

        buffer = io.StringIO(newline="")
        fields = ["timestamp_utc", "collection", "issn", "code", "title", "authors",
                  "journal", "year", "doi", "language", "source_url", "search_query",
                  "xml_format", "status", "zip_path", "error"]
        writer = csv.DictWriter(buffer, fieldnames=fields)
        writer.writeheader()
        writer.writerows(manifest)
        archive.writestr("manifest.csv", buffer.getvalue().encode("utf-8-sig"))
        archive.writestr(
            "README.txt",
            (
                "DumpArticle SciELO - resultado de descarga\n"
                f"Generado (UTC): {datetime.now(timezone.utc).isoformat()}\n"
                f"Formato XML: {xml_format}\n"
                f"Identificadores procesados: {len(items)}\n"
                f"XML descargados: {downloaded}\n"
                f"Fallidos: {failed}\n"
                "Consulte manifest.csv para el estado individual de cada registro.\n"
                "La descarga de XML no garantiza que todos los documentos incluyan el cuerpo completo.\n"
            ).encode("utf-8")
        )

    return {
        "output_path": str(output),
        "total": len(items),
        "downloaded": downloaded,
        "failed": failed,
        "manifest": manifest,
    }
