from pathlib import Path
from core.jats_parser import parse_jats, sections_by_category, classify_section
from database.repository import Repository

FX = Path(__file__).parent / "fixtures" / "synthetic_jats_fixture.xml"


def test_metadatos():
    p = parse_jats(FX.read_bytes())
    assert p["doi"] == "10.0000/prueba.2024.001" and p["year"] == 2024
    assert p["ids"]["publisher-id"] == "S0000-00002024000100001"
    assert p["titles"]["en"].startswith("Artificial") and p["title"].startswith("Inteligencia")
    assert p["journal_title"] == "Revista de Prueba"


def test_autores_afiliaciones():
    p = parse_jats(FX.read_bytes())
    assert [a["name"] for a in p["authors"]] == ["Ana Quispe", "João Silva"]
    assert p["authors"][0]["affiliations"] == ["Universidad Ficticia, Lima, Perú"]
    assert p["authors"][1]["affiliations"] == ["Universidade Fictícia, São Paulo, Brasil"]


def test_resumen_keywords():
    p = parse_jats(FX.read_bytes())
    assert {a["lang"] for a in p["abstracts"]} == {"es", "en"}
    assert p["keywords"][0]["keywords"] == ["inteligencia artificial", "educación"]


def test_secciones_conservan_etiqueta_original():
    p = parse_jats(FX.read_bytes())
    cats = sections_by_category(p)
    assert cats["introduccion"][0]["title"] == "1. Introducción"
    assert cats["metodologia"][0]["title"] == "Materiales y métodos"
    assert "Subsección" in cats["metodologia"][0]["text"]
    assert {"resultados", "discusion", "conclusiones", "otra"} <= set(cats)
    assert cats["otra"][0]["title"] == "Marco ético"


def test_referencias_no_inventadas():
    p = parse_jats(FX.read_bytes())
    assert len(p["references"]) == 2 and p["references"][1]["doi"] == "10.1/abc"


def test_clasificacion():
    assert classify_section("Considerações finais", None) == "conclusiones"
    assert classify_section("Algo", "results") == "resultados"
    assert classify_section("Algo", None) == "otra"


def test_ausente_no_inventa():
    xml = b"<article><front><article-meta><title-group><article-title>T</article-title></title-group><abstract><p>R</p></abstract></article-meta></front></article>"
    p = parse_jats(xml)
    assert p["sections"] == [] and not p["has_body"] and p["references"] == [] and p["authors"] == []


def test_almacenamiento_y_exportacion(tmp_path):
    from database.models import ArticleRecord
    repo = Repository(str(tmp_path / "t.db"))
    repo.upsert_article(ArticleRecord("per", "P", title="T", year=2024, journal_title="R"))
    repo.upsert_fulltext("per", "P", parse_jats(FX.read_bytes()))
    for fmt in ("csv", "xlsx", "json"):
        assert Path(repo.export(fmt, str(tmp_path))).exists()
