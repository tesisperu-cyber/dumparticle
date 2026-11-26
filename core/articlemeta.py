"""Cliente de la ArticleMeta RESTful API de SciELO.
Rutas usadas (base configurable en settings.articlemeta_base):
  GET /collection/                      -> lista de colecciones
  GET /article/identifiers/             -> ?collection=&issn=&from=&until=&limit=&offset=
  GET /article/                         -> ?collection=&code=<PID>[&format=xmlrsps]
ESTADO: rutas contrastadas con documentación pública y clientes de terceros, pero NO
verificadas con llamadas en vivo desde el entorno cloud (sin DNS hacia SciELO).
Ejecute `python main.py probe` para verificarlas; el parser JSON es defensivo y el
diagnóstico informa si los metadatos llegan incompletos."""
from __future__ import annotations
from typing import Iterator, Optional
from database.models import ArticleRecord
from .client import HttpClient, FetchResult


def _first(lst, key="_"):
    if isinstance(lst, list) and lst:
        x = lst[0]
        return x.get(key) if isinstance(x, dict) else x
    return None


def extract_objects(data) -> list:
    """Normaliza respuestas de formas distintas a una lista de dicts, sin asumir el formato:
    lista | {'objects': [...]} | {'items'|'results'|'data': [...]} | dict de dicts | dict único."""
    if isinstance(data, list):
        return [x for x in data if isinstance(x, dict)]
    if isinstance(data, dict):
        for k in ("objects", "items", "results", "data"):
            if isinstance(data.get(k), list):
                return [x for x in data[k] if isinstance(x, dict)]
        if data and all(isinstance(v, dict) for v in data.values()):
            return list(data.values())
        return [data] if data else []
    return []


def _year(v) -> Optional[int]:
    if v and str(v)[:4].isdigit():
        return int(str(v)[:4])
    return None


def parse_article_json(data: dict, collection: str | None = None, url: str | None = None,
                       domain: str | None = None) -> ArticleRecord:
    """Convierte la respuesta JSON (campos ISIS 'vNN') en ArticleRecord.
    Mapeo asumido (a confirmar con respuesta real): v880=PID, v237=DOI, v12=títulos [{l,_}],
    v83=resúmenes [{l,a}], v85=palabras clave [{l,k}], v10=autores [{s,n}], v65=fecha,
    v35/v400=ISSN, v71=tipo documental; revista en data['title'] v100."""
    if not isinstance(data, dict):
        data = {}
    art = data.get("article") if isinstance(data.get("article"), dict) else {}
    jr = data.get("title") if isinstance(data.get("title"), dict) else {}
    pid = data.get("code") or _first(art.get("v880")) or ""
    col = data.get("collection") or collection or ""
    titles = {}
    for t in art.get("v12") or []:
        if isinstance(t, dict) and t.get("_"):
            titles.setdefault(t.get("l") or "und", t["_"].strip())
    abstracts = [a.get("a") for a in (art.get("v83") or []) if isinstance(a, dict) and a.get("a")]
    kws = []
    for k in art.get("v85") or []:
        if isinstance(k, dict):
            v = k.get("k") or k.get("_")
            if v:
                kws.append(v.strip())
    authors = []
    for a in art.get("v10") or []:
        if isinstance(a, dict):
            nm = " ".join(x for x in [a.get("n"), a.get("s")] if x)
            if nm:
                authors.append(nm)
    pref = next((l for l in ("es", "pt", "en") if l in titles), None)
    title = titles[pref] if pref else (next(iter(titles.values())) if titles else None)
    rec = ArticleRecord(
        collection=col, pid=pid, doi=data.get("doi") or _first(art.get("v237")),
        title=title, titles_all=titles, authors=authors,
        journal_title=_first(jr.get("v100")) or _first(art.get("v30")),
        issn=_first(jr.get("v400")) or _first(art.get("v35")),
        year=_year(_first(art.get("v65"))), doc_type=_first(art.get("v71")),
        abstract=" ".join(abstracts) or None, keywords=kws, url_original=url,
        processing_date=data.get("processing_date"),
        url_site=(f"http://{domain}/scielo.php?script=sci_arttext&pid={pid}" if domain and pid else None),
    )
    return rec


class ArticleMetaClient:
    def __init__(self, http: HttpClient, settings):
        self.http, self.s = http, settings
        self.base = settings.articlemeta_base.rstrip("/")
        self._domains: dict = {}

    def collections(self) -> FetchResult:
        """Prueba rutas en orden hasta reconocer colecciones (la ruta '/collection/' devolvió 'null'
        en una prueba real; '/collection/identifiers/' es un respaldo aún sin verificar)."""
        res = None
        for path in ("/collection/", "/collection/identifiers/"):
            res = self.http.get(f"{self.base}{path}")
            if not res.ok:
                continue
            try:
                items = extract_objects(res.json())
            except ValueError:
                self.http.diag.http_error("json_invalido:collection")
                continue
            doms = {c.get("code"): c.get("domain") for c in items if c.get("code")}
            if doms:
                self._domains = doms
                break
        return res

    def domain(self, collection: str):
        """Dominio web de la colección; si no se conoce, intenta '/collection/?code=XXX' una vez."""
        if collection not in self._domains and collection not in getattr(self, "_tried", set()):
            self._tried = getattr(self, "_tried", set()) | {collection}
            res = self.http.get(f"{self.base}/collection/", params={"code": collection})
            if res.ok:
                try:
                    for c in extract_objects(res.json()):
                        if c.get("code") == collection and c.get("domain"):
                            self._domains[collection] = c["domain"]
                except ValueError:
                    pass
        return self._domains.get(collection)

    def identifiers_page(self, collection: str, offset: int, limit: int,
                         issn: str | None = None, from_date=None, until_date=None) -> FetchResult:
        params = {"collection": collection, "limit": limit, "offset": offset}
        if issn:
            params["issn"] = issn
        if from_date:
            params["from"] = from_date
        if until_date:
            params["until"] = until_date
        return self.http.get(f"{self.base}/article/identifiers/", params=params)

    def iter_identifiers(self, collection: str, **kw) -> Iterator[dict]:
        """Itera {'code': PID, 'collection':..., ...}. Se detiene al agotar o por error."""
        offset, limit = 0, self.s.identifiers_page_size
        while True:
            res = self.identifiers_page(collection, offset, limit, **kw)
            if not res.ok:
                return
            try:
                data = res.json()
            except ValueError:
                self.http.diag.http_error("json_invalido:identifiers")
                return
            objs = extract_objects(data)
            if not objs:
                self.http.diag.note(f"[{collection}] identifiers sin objetos reconocibles: {str(data)[:150]!r}")
                return
            for o in objs:
                yield o
            offset += len(objs)
            total = (data.get("meta") or {}).get("total") if isinstance(data, dict) else None
            if total is not None and offset >= total:
                return

    def article_json(self, collection: str, pid: str) -> FetchResult:
        return self.http.get(f"{self.base}/article/", params={"collection": collection, "code": pid})

    def article_xml(self, collection: str, pid: str, fmt: str = "xmlrsps") -> FetchResult:
        return self.http.get(f"{self.base}/article/",
                             params={"collection": collection, "code": pid, "format": fmt})
