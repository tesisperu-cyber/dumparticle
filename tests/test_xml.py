from pathlib import Path
from core.validator import validate_xml

FX = Path(__file__).parent / "fixtures"


def test_valido():
    v = validate_xml((FX / "synthetic_jats_fixture.xml").read_bytes(), 200, "application/xml")
    assert v.ok and v.has_body and v.has_abstract and v.root_tag == "article"


def test_http_error():
    assert not validate_xml(b"<a/>", 404, "text/xml").ok


def test_no_xml():
    v = validate_xml(b"<html><body>no</body></html>", 200, "text/html")
    assert not v.ok


def test_mal_formado():
    assert not validate_xml(b"<article><front>", 200, "text/xml").ok


def test_sin_contenido_documental():
    v = validate_xml((FX / "synthetic_no_body.xml").read_bytes(), 200, "text/xml")
    assert not v.ok and any("sin contenido" in r for r in v.reasons)


def test_vacio():
    assert not validate_xml(b"", 200, "text/xml").ok


def test_xxe_no_resuelve_entidades():
    evil = b'<?xml version="1.0"?><!DOCTYPE a [<!ENTITY x SYSTEM "file:///etc/passwd">]><article><front><article-meta><title-group><article-title>&x;</article-title></title-group></article-meta></front></article>'
    from core.jats_parser import parse_jats
    v = validate_xml(evil, 200, "text/xml")
    title = (parse_jats(evil)["title"] or "") if v.ok else ""
    assert "root:" not in title  # la entidad externa nunca se resuelve
