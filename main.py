"""CLI de scielo_pybot.
  python main.py init-db
  python main.py probe [--collection per] [--pid S...]      # PRIMERA PRUEBA con artículo real
  python main.py check-equation "<ecuación>" "<texto>"
  python main.py parse-xml archivo.xml
  python main.py search --config config.json [--equation ... --year-from ... ]
  python main.py export --fmt csv|xlsx|json
"""
from __future__ import annotations
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from config.settings import Settings
from core.boolean_engine import compile_query, BooleanSyntaxError
from core.jats_parser import parse_jats
from core.validator import validate_xml
from database.repository import Repository


def cmd_init_db(a, s):
    Repository(s.db_path).close()
    print(f"Base de datos inicializada: {s.db_path}")


def cmd_check(a, s):
    try:
        print(compile_query(a.equation).matches(a.text))
    except BooleanSyntaxError as e:
        print(f"Error de sintaxis: {e}")
        return 2


def cmd_parse(a, s):
    content = Path(a.file).read_bytes()
    v = validate_xml(content, 200, "application/xml")
    print("Validación:", v)
    if v.ok:
        p = parse_jats(content)
        print(json.dumps({k: p[k] for k in ("title", "doi", "year", "journal_title", "has_body")}, ensure_ascii=False, indent=2))
        for sec in p["sections"]:
            print(f"- [{sec['category']}] {sec['title']!r}: {len(sec['text'])} caracteres")
        print("Referencias:", len(p["references"]))


def cmd_export(a, s):
    repo = Repository(s.db_path)
    print("Exportado:", repo.export(a.fmt, s.exports_dir))


def cmd_search(a, s):
    from core.pipeline import run_search
    if a.equation:
        s.equation = a.equation
    if a.year_from:
        s.year_from = a.year_from
    if a.year_to:
        s.year_to = a.year_to
    if a.collections:
        s.collections = a.collections.split(",")
    if a.max_results:
        s.max_results = a.max_results
    matches, diag, repo = run_search(s)
    print(f"{len(matches)} artículo(s) coinciden.")
    for r in matches:
        print(f"  [{r.collection}] {r.pid} ({r.year}) {r.title}")
    print(diag.format())
    for fmt in ("csv", "xlsx", "json"):
        print("Exportado:", repo.export(fmt, s.exports_dir))


def cmd_probe(a, s):
    """Primera prueba obligatoria. Busca (hasta --scan artículos) uno cuyo XML-JATS tenga CUERPO,
    porque los XML de artículos antiguos suelen traer solo metadatos+referencias. Todo se informa con lo recibido."""
    from core.client import HttpClient
    from core.articlemeta import ArticleMetaClient, parse_article_json, extract_objects
    from core.diagnostics import Diagnostics
    scan = int(getattr(a, "scan", 25) or 25)
    from_date = getattr(a, "from_date", "2020-01-01") or None
    diag = Diagnostics()
    http = HttpClient(s, diag)
    am = ArticleMetaClient(http, s)
    out = Path(s.exports_dir) / "probe"
    out.mkdir(parents=True, exist_ok=True)
    steps, ok_all = [], True
    col, pid = a.collection, a.pid

    def step(name, ok, detail):
        nonlocal ok_all
        ok_all &= bool(ok)
        steps.append((name, bool(ok), detail))
        print(f"[{'OK ' if ok else 'FALLA'}] {name}: {detail}")

    r = am.collections()
    (out / "collections.raw").write_bytes(r.content or (r.error or "").encode())
    prev = r.content[:200].decode("utf-8", "replace").replace("\n", " ") if r.content else ""
    step("1. Colecciones (ArticleMeta)", r.ok and len(am._domains) > 0,
         f"HTTP {r.status} {r.content_type} {r.error or ''} | {len(am._domains)} colecciones reconocidas | "
         f"dominio de {col}={am.domain(col)!r} | inicio={prev!r}")

    cands = [pid] if pid else []
    if not pid:
        ids = am.identifiers_page(col, 0, scan, from_date=from_date)
        (out / "identifiers.raw").write_bytes(ids.content or (ids.error or "").encode())
        objs = []
        if ids.ok:
            try:
                objs = extract_objects(ids.json().get("objects", ids.json()) if isinstance(ids.json(), dict) else ids.json())
            except ValueError:
                pass
        cands = [o.get("code") or o.get("pid") for o in objs if (o.get("code") or o.get("pid"))]
        step("2. Identificadores", bool(cands),
             f"HTTP {ids.status}; {len(cands)} PID desde {from_date}; primeros={cands[:3]}")
    if not cands:
        step("3. Metadatos", False, "sin PID: no se puede continuar")
    else:
        fmts = s.xml_formats
        chosen = first_valid = None
        stats = {"invalidos": 0, "validos_sin_cuerpo": 0, "revisados": 0}
        for c in cands:
            stats["revisados"] += 1
            for fmt in fmts:
                rx = am.article_xml(col, c, fmt)
                v = validate_xml(rx.content, rx.status, rx.content_type) if rx.error is None else None
                if not (v and v.ok):
                    stats["invalidos"] += 1
                    continue
                parsed = parse_jats(rx.content)
                item = (c, fmt, rx, v, parsed)
                first_valid = first_valid or item
                if parsed["sections"]:
                    chosen = item
                else:
                    stats["validos_sin_cuerpo"] += 1
                break
            if chosen:
                break
        sel = chosen or first_valid
        use_pid = sel[0] if sel else cands[0]
        rj = am.article_json(col, use_pid)
        (out / f"{use_pid}.json").write_bytes(rj.content or b"")
        rec, keys = None, []
        if rj.ok:
            try:
                dj = rj.json()
                rec = parse_article_json(dj, col, rj.url, am.domain(col))
                keys = sorted((dj.get("article") or {}).keys()) if isinstance(dj, dict) else []
            except ValueError:
                pass
        step("3. Metadatos JSON", rec is not None and rec.metadata_complete,
             f"PID={use_pid} DOI={getattr(rec,'doi',None)} título={getattr(rec,'title',None)!r} año={getattr(rec,'year',None)} "
             f"revista={getattr(rec,'journal_title',None)!r} autores={len(getattr(rec,'authors',[]) or [])} "
             f"resumen={'sí' if getattr(rec,'abstract',None) else 'no'} palabras_clave={len(getattr(rec,'keywords',[]) or [])} "
             f"campos_article={keys}")
        if sel:
            _, fmt, rx, v, parsed = sel
            (out / f"{use_pid}.{fmt}.xml").write_bytes(rx.content)
            step(f"4. XML-JATS ({fmt})", True, f"HTTP {rx.status} {rx.content_type} {len(rx.content)} bytes; raíz={v.root_tag}; validación={v.reasons or 'sin observaciones'}")
            secs = [(x["category"], x["title"], len(x["text"])) for x in parsed["sections"]]
            step("5. Extracción de secciones", bool(parsed["sections"]),
                 f"título={parsed['title']!r} autores={len(parsed['authors'])} afiliaciones={len(parsed['affiliations'])} "
                 f"resúmenes={len(parsed['abstracts'])} palabras_clave={sum(len(k['keywords']) for k in parsed['keywords'])} "
                 f"secciones={secs} referencias={len(parsed['references'])} doi_xml={parsed['doi']} | "
                 f"revisados={stats['revisados']} válidos_sin_cuerpo={stats['validos_sin_cuerpo']} inválidos={stats['invalidos']}"
                 + ("" if parsed["sections"] else " | NINGÚN XML del lote trae cuerpo: pruebe otra colección/--from-date más reciente"))
        else:
            step("4. XML-JATS", False, f"ningún XML válido en {stats['revisados']} artículos revisados (inválidos={stats['invalidos']})")
    rep = out.parent / "informe_primer_articulo.md"
    lines = ["# Informe de recuperación de un artículo real", f"Generado: {datetime.now(timezone.utc).isoformat()}",
             f"Colección: {col}", "", "| Paso | Resultado | Detalle |", "|---|---|---|"]
    lines += [f"| {n} | {'OK' if o else 'FALLA'} | {str(d).replace('|','/')} |" for n, o, d in steps]
    lines += ["", "Resultado global: " + ("APROBADO" if ok_all else "NO APROBADO"), "", diag.format()]
    rep.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nInforme: {rep}\nResultado global: {'APROBADO' if ok_all else 'NO APROBADO'}")
    return 0 if ok_all else 1


def main(argv=None):
    ap = argparse.ArgumentParser(prog="scielo_pybot")
    ap.add_argument("--config", default="config.json")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("init-db")
    p = sub.add_parser("probe"); p.add_argument("--collection", default="per"); p.add_argument("--pid")
    p.add_argument("--scan", type=int, default=25, help="artículos a revisar buscando uno con cuerpo")
    p.add_argument("--from-date", default="2020-01-01", help="fecha de procesamiento mínima (AAAA-MM-DD)")
    p = sub.add_parser("check-equation"); p.add_argument("equation"); p.add_argument("text")
    p = sub.add_parser("parse-xml"); p.add_argument("file")
    p = sub.add_parser("export"); p.add_argument("--fmt", default="csv", choices=["csv", "xlsx", "json"])
    p = sub.add_parser("search"); p.add_argument("--equation"); p.add_argument("--year-from", type=int)
    p.add_argument("--year-to", type=int); p.add_argument("--collections"); p.add_argument("--max-results", type=int)
    a = ap.parse_args(argv)
    s = Settings.load(a.config)
    fn = {"init-db": cmd_init_db, "probe": cmd_probe, "check-equation": cmd_check, "parse-xml": cmd_parse,
          "export": cmd_export, "search": cmd_search}[a.cmd]
    return fn(a, s) or 0


if __name__ == "__main__":
    sys.exit(main())
