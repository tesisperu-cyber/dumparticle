"""Descarga de XML-JATS vía ArticleMeta (format=xmlrsps = SciELO Publishing Schema, JATS).
Valida y guarda el original en disco solo si es válido; si no, conserva evidencia (.invalid)."""
from __future__ import annotations
import hashlib
from dataclasses import dataclass
from pathlib import Path
from .validator import validate_xml


@dataclass
class XmlOutcome:
    ok: bool
    path: str | None
    reasons: list
    content: bytes = b""


class XmlDownloader:
    def __init__(self, settings, am, repo, diag):
        self.s, self.am, self.repo, self.diag = settings, am, repo, diag

    def download(self, rec) -> XmlOutcome:
        self.diag.inc("xml_requested", collection=rec.collection)
        last = XmlOutcome(False, None, ["sin intentos"])
        for fmt in self.s.xml_formats:
            res = self.am.article_xml(rec.collection, rec.pid, fmt)
            vr = validate_xml(res.content, res.status, res.content_type) if res.error is None else None
            reasons = vr.reasons if vr else [res.error]
            valid = bool(vr and vr.ok)
            d = Path(self.s.xml_dir) / rec.collection
            d.mkdir(parents=True, exist_ok=True)
            path = d / (f"{rec.pid}.xml" if valid else f"{rec.pid}.invalid.txt")
            if res.content:
                path.write_bytes(res.content)
            sha = hashlib.sha256(res.content).hexdigest() if res.content else None
            self.repo.upsert_xml(rec.collection, rec.pid, fmt, str(path) if res.content else None, res.status,
                                 res.content_type, len(res.content), sha, valid, reasons)
            if valid:
                self.diag.inc("xml_ok", collection=rec.collection)
                return XmlOutcome(True, str(path), reasons, res.content)
            last = XmlOutcome(False, str(path) if res.content else None, reasons)
        self.diag.inc("xml_invalid", collection=rec.collection)
        return last
