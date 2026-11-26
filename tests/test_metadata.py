from core.articlemeta import parse_article_json
from core.deduplicator import deduplicate
from database.models import ArticleRecord
from core.harvester import Harvester
from core.diagnostics import Diagnostics
from config.settings import Settings
from database.repository import Repository

# NOTA: este dict es una ESTRUCTURA SUPUESTA (campos ISIS vNN) para probar el parser
# defensivo. No es un registro real. La estructura real se confirma con `main.py probe`.
ASSUMED = {"code": "S0000-00002024000100001", "collection": "per",
           "article": {"v12": [{"l": "es", "_": "Título de prueba"}, {"l": "en", "_": "Test title"}],
                       "v83": [{"l": "es", "a": "Resumen de prueba sobre educación."}],
                       "v85": [{"l": "es", "k": "educación"}], "v10": [{"s": "Quispe", "n": "Ana"}],
                       "v65": [{"_": "20240300"}], "v237": [{"_": "10.0000/x"}]},
           "title": {"v100": [{"_": "Revista Prueba"}], "v400": [{"_": "0000-0000"}]}}


def test_parse_defensivo():
    r = parse_article_json(ASSUMED, "per", "u", "www.scielo.org.pe")
    assert r.pid == "S0000-00002024000100001" and r.year == 2024 and r.doi == "10.0000/x"
    assert r.title == "Título de prueba" and r.metadata_complete
    assert r.url_site.endswith("pid=S0000-00002024000100001")


def test_parse_vacio_no_inventa():
    r = parse_article_json({}, "per")
    assert r.title is None and not r.metadata_complete


def test_dedup():
    a = ArticleRecord("per", "P1", doi="10.1/A", title="T", year=2020)
    b = ArticleRecord("scl", "P1", doi="https://doi.org/10.1/a", title="T", year=2020, abstract="x", keywords=["k"])
    c = ArticleRecord("col", "P9", title="Otro", year=2021)
    out = deduplicate([a, b, c])
    assert len(out) == 2
    merged = [r for r in out if r.doi][0]
    assert set(merged.collections) == {"per", "scl"} and merged.abstract == "x"


class FakeAM:
    """Cliente falso: prueba la LÓGICA del cosechador (no simula datos de SciELO)."""
    def __init__(self, ids, recs): self.ids, self.recs = ids, recs
    def iter_identifiers(self, col, **kw): yield from self.ids.get(col, [])
    def domain(self, col): return None
    def article_json(self, col, pid):
        from core.client import FetchResult
        import json
        d = self.recs.get(pid)
        return FetchResult("u", 200, "application/json", json.dumps(d).encode()) if d else FetchResult("u", 404)


def _rec(pid, title, year, abstract="", col="per"):
    return {"code": pid, "collection": col, "article": {"v12": [{"l": "es", "_": title}], "v83": [{"l": "es", "a": abstract}],
            "v65": [{"_": f"{year}0101"}]}, "title": {"v100": [{"_": "Rev"}]}}


def test_harvester_filtros_y_diagnostico(tmp_path):
    s = Settings(equation="educ*", collections=["per"], year_from=2020, year_to=2024, db_path=str(tmp_path / "t.db"))
    ids = {"per": [{"code": "A"}, {"code": "B"}, {"code": "C"}, {"code": "D"}]}
    recs = {"A": _rec("A", "Educación virtual", 2022), "B": _rec("B", "Educación vieja", 2010),
            "C": _rec("C", "Cardiología", 2023), "D": None}
    diag = Diagnostics()
    out = Harvester(s, FakeAM(ids, recs), Repository(s.db_path), diag).run()
    assert [r.pid for r in out] == ["A"]
    c = diag.c
    assert (c["received"], c["complete"], c["temporal_ok"], c["thematic_ok"]) == (3, 3, 2, 1)
    assert diag.identifiers_listed == 4


def test_cero_explicado(tmp_path):
    s = Settings(equation="zzz", collections=["per"], db_path=str(tmp_path / "t.db"))
    diag = Diagnostics()
    Harvester(s, FakeAM({"per": [{"code": "A"}]}, {"A": _rec("A", "Educación", 2022)}), Repository(s.db_path), diag).run()
    assert "ninguno satisface la ecuación" in diag.explain()
    d2 = Diagnostics()
    assert "ni un identificador" in d2.explain()


def test_extract_objects_formatos():
    from core.articlemeta import extract_objects
    assert extract_objects([{"code": "a"}, 3]) == [{"code": "a"}]
    assert extract_objects({"objects": [{"code": "a"}]}) == [{"code": "a"}]
    assert extract_objects({"per": {"code": "per"}, "scl": {"code": "scl"}}) == [{"code": "per"}, {"code": "scl"}]
    assert extract_objects({"code": "x"}) == [{"code": "x"}]
    assert extract_objects("texto") == [] and extract_objects(None) == [] and extract_objects(5) == []


def test_parse_json_no_dict_no_revienta():
    for bad in ("x", None, [], 3):
        r = parse_article_json(bad, "per")
        assert r.title is None


def test_probe_logica_sin_red(tmp_path, monkeypatch):
    """Prueba la lógica de selección de `probe` con un servicio falso (no simula SciELO real):
    el primer artículo sin cuerpo se salta y se elige el que sí tiene secciones."""
    import argparse, core.articlemeta as am_mod, main as m
    from core.client import FetchResult
    import json
    from pathlib import Path
    fx = Path(__file__).parent / "fixtures"
    con_cuerpo = (fx / "synthetic_jats_fixture.xml").read_bytes()
    sin_cuerpo = b"<article><front><article-meta><title-group><article-title>T</article-title></title-group><abstract><p>R</p></abstract></article-meta></front></article>"

    class Fake:
        def __init__(self, http, s): self._domains = {"per": "www.scielo.org.pe"}
        def collections(self): return FetchResult("u", 200, "application/json", b"[]")
        def domain(self, c): return "www.scielo.org.pe"
        def identifiers_page(self, col, o, l, **kw):
            return FetchResult("u", 200, "application/json", json.dumps({"objects": [{"code": "A"}, {"code": "B"}]}).encode())
        def article_xml(self, col, pid, fmt):
            return FetchResult("u", 200, "application/xml", sin_cuerpo if pid == "A" else con_cuerpo)
        def article_json(self, col, pid):
            d = {"code": pid, "article": {"v12": [{"l": "es", "_": "T"}], "v65": [{"_": "20240101"}]}, "title": {"v100": [{"_": "R"}]}}
            return FetchResult("u", 200, "application/json", json.dumps(d).encode())

    monkeypatch.setattr(am_mod, "ArticleMetaClient", Fake)
    s = Settings(exports_dir=str(tmp_path))
    code = m.cmd_probe(argparse.Namespace(collection="per", pid=None, scan=5, from_date=None), s)
    rep = (tmp_path / "informe_primer_articulo.md").read_text(encoding="utf-8")
    assert code == 0 and "válidos_sin_cuerpo=1" in rep and "Resultado global: APROBADO" in rep
