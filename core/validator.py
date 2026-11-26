"""Validación de respuestas XML-JATS: HTTP, tipo de contenido, XML bien formado,
estructura JATS y contenido documental."""
from __future__ import annotations
from dataclasses import dataclass, field
from lxml import etree


def safe_parser() -> etree.XMLParser:
    return etree.XMLParser(resolve_entities=False, no_network=True, load_dtd=False,
                           dtd_validation=False, huge_tree=False, recover=False)


@dataclass
class ValidationResult:
    ok: bool
    reasons: list = field(default_factory=list)
    root_tag: str | None = None
    has_body: bool = False
    has_abstract: bool = False


def validate_xml(content: bytes, status: int | None, content_type: str = "") -> ValidationResult:
    reasons: list[str] = []
    if status != 200:
        return ValidationResult(False, [f"HTTP {status}"])
    if not content or not content.strip():
        return ValidationResult(False, ["respuesta vacía"])
    ct = (content_type or "").lower()
    if "html" in ct and "xml" not in ct:
        reasons.append(f"Content-Type no XML: {content_type}")
    try:
        root = etree.fromstring(content, safe_parser())
    except etree.XMLSyntaxError as e:
        return ValidationResult(False, reasons + [f"XML mal formado: {e}"])
    tag = etree.QName(root).localname
    res = ValidationResult(False, reasons, root_tag=tag)
    if tag != "article":
        res.reasons.append(f"raíz inesperada '{tag}' (se esperaba 'article' JATS)")
        return res
    if root.find("./front/article-meta") is None:
        res.reasons.append("falta front/article-meta")
        return res
    title = "".join(root.xpath("string(./front/article-meta/title-group/article-title)")).strip()
    if not title:
        res.reasons.append("sin article-title")
        return res
    res.has_body = root.find("./body") is not None and bool("".join(root.find("./body").itertext()).strip())
    res.has_abstract = root.find("./front/article-meta/abstract") is not None
    if not (res.has_body or res.has_abstract):
        res.reasons.append("sin contenido documental (ni body ni abstract)")
        return res
    if "html" in ct and "xml" not in ct:
        res.ok = True
        res.reasons.append("advertencia: Content-Type html pero XML válido")
        return res
    res.ok = True
    return res
