"""Extracción desde XML-JATS. Conserva etiquetas originales de sección y NO inventa
contenido ausente: lo que no existe queda vacío/None."""
from __future__ import annotations
import re
from lxml import etree
from .normalizer import normalize_text
from .validator import safe_parser

XML_LANG = "{http://www.w3.org/XML/1998/namespace}lang"

_CATS = [
    ("introduccion", ("introduc", "antecedentes", "background")),
    ("metodologia", ("metod", "materiales", "materiais", "methods", "materials", "procedimiento", "diseno")),
    ("resultados", ("resultad", "results", "findings", "hallazgos")),
    ("discusion", ("discus", "discussion")),
    ("conclusiones", ("conclus", "consideraciones finales", "consideracoes finais", "final remarks")),
]
_SECTYPE = {"intro": "introduccion", "methods": "metodologia", "materials": "metodologia",
            "results": "resultados", "discussion": "discusion", "conclusions": "conclusiones"}


def _txt(el) -> str:
    if el is None:
        return ""
    return re.sub(r"\s+", " ", "".join(el.itertext())).strip()


def classify_section(title: str | None, sec_type: str | None) -> str:
    t = normalize_text(title)
    for cat, pats in _CATS:
        if any(t.startswith(p) or f" {p}" in f" {t}" for p in pats):
            return cat
    if sec_type:
        for part in re.split(r"[|,; ]+", sec_type.lower()):
            if part in _SECTYPE:
                return _SECTYPE[part]
    return "otra"


def _aff_text(aff) -> str:
    orig = aff.xpath("./institution[@content-type='original']")
    if orig:
        return _txt(orig[0])
    import copy
    a = copy.deepcopy(aff)
    for lab in a.xpath(".//label"):
        parent, tail = lab.getparent(), lab.tail or ""
        prev = lab.getprevious()
        if prev is not None:
            prev.tail = (prev.tail or "") + tail
        else:
            parent.text = (parent.text or "") + tail
        parent.remove(lab)  # remove() descarta el 'tail', por eso se conservó arriba
    return _txt(a)


def parse_jats(content: bytes | str) -> dict:
    if isinstance(content, str):
        content = content.encode("utf-8")
    root = etree.fromstring(content, safe_parser())
    am = root.find("./front/article-meta")
    jm = root.find("./front/journal-meta")
    out: dict = {"article_type": root.get("article-type"), "lang": root.get(XML_LANG)}

    # identificadores
    ids = {}
    if am is not None:
        for aid in am.findall("./article-id"):
            ids.setdefault(aid.get("pub-id-type") or "other", _txt(aid))
    out["ids"] = ids
    out["doi"] = ids.get("doi")

    # título(s)
    titles = {}
    if am is not None:
        t = am.find("./title-group/article-title")
        if t is not None:
            titles[t.get(XML_LANG) or root.get(XML_LANG) or "orig"] = _txt(t)
        for tt in am.findall("./title-group/trans-title-group"):
            x = tt.find("./trans-title")
            if x is not None:
                titles[tt.get(XML_LANG) or "trans"] = _txt(x)
    out["titles"] = titles
    out["title"] = next(iter(titles.values()), None)

    # afiliaciones
    aff_map = {}
    if am is not None:
        for aff in am.xpath(".//aff"):
            aff_map[aff.get("id")] = _aff_text(aff)
    out["affiliations"] = [{"id": k, "text": v} for k, v in aff_map.items()]

    # autores
    authors = []
    if am is not None:
        for c in am.xpath("./contrib-group/contrib[not(@contrib-type) or @contrib-type='author']"):
            sn, gn = _txt(c.find("./name/surname")), _txt(c.find("./name/given-names"))
            name = " ".join(x for x in (gn, sn) if x) or _txt(c.find("./collab"))
            if not name:
                continue
            rids = [x.get("rid") for x in c.findall("./xref[@ref-type='aff']")]
            authors.append({"name": name, "surname": sn, "given_names": gn,
                            "affiliation_ids": rids,
                            "affiliations": [aff_map[r] for r in rids if r in aff_map]})
    out["authors"] = authors

    # revista / fecha
    out["journal_title"] = _txt(jm.find(".//journal-title")) if jm is not None and jm.find(".//journal-title") is not None else None
    out["issn"] = [{"type": i.get("pub-type") or i.get("publication-format"), "value": _txt(i)}
                   for i in (jm.findall(".//issn") if jm is not None else [])]
    year = None
    if am is not None:
        y = am.find("./pub-date/year")
        year = int(_txt(y)) if y is not None and _txt(y).isdigit() else None
    out["year"] = year

    # resúmenes y palabras clave
    abstracts = []
    if am is not None:
        for ab in am.findall("./abstract") + am.findall("./trans-abstract"):
            abstracts.append({"lang": ab.get(XML_LANG) or root.get(XML_LANG), "text": _txt(ab)})
    out["abstracts"] = abstracts
    kws = []
    if am is not None:
        for g in am.findall("./kwd-group"):
            kws.append({"lang": g.get(XML_LANG), "keywords": [_txt(k) for k in g.findall("./kwd")]})
    out["keywords"] = kws

    # cuerpo
    body = root.find("./body")
    sections = []
    if body is not None:
        for sec in body.findall("./sec"):
            title = _txt(sec.find("./title")) or None
            sections.append({"title": title, "sec_type": sec.get("sec-type"),
                             "category": classify_section(title, sec.get("sec-type")),
                             "text": _txt(sec)})
        if not sections and _txt(body):
            sections.append({"title": None, "sec_type": None, "category": "cuerpo_sin_secciones",
                             "text": _txt(body)})
    out["sections"] = sections
    out["has_body"] = bool(sections)

    # referencias
    refs = []
    for r in root.xpath("./back//ref-list/ref"):
        cit = r.find("./mixed-citation")
        if cit is None:
            cit = r.find("./element-citation")
        doi = r.xpath("string(.//pub-id[@pub-id-type='doi'])").strip() or None
        refs.append({"id": r.get("id"), "text": _txt(cit if cit is not None else r), "doi": doi})
    out["references"] = refs
    return out


def sections_by_category(parsed: dict) -> dict:
    res: dict = {}
    for s in parsed["sections"]:
        res.setdefault(s["category"], []).append(s)
    return res
