from __future__ import annotations
import json
import sqlite3
from pathlib import Path
import pandas as pd
from .models import SCHEMA, ArticleRecord


class Repository:
    def __init__(self, db_path: str):
        self.path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)
        self.conn.commit()

    def close(self):
        self.conn.close()

    # --- artículos ---
    def upsert_article(self, r: ArticleRecord):
        self.conn.execute(
            """INSERT OR REPLACE INTO articles (collection,pid,doi,title,titles_all,authors,journal_title,issn,year,
               doc_type,abstract,keywords,url_original,url_site,metadata_complete,processing_date)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (r.collection, r.pid, r.doi, r.title, json.dumps(r.titles_all, ensure_ascii=False),
             json.dumps(r.authors, ensure_ascii=False), r.journal_title, r.issn, r.year, r.doc_type,
             r.abstract, json.dumps(r.keywords, ensure_ascii=False), r.url_original, r.url_site,
             int(r.metadata_complete), r.processing_date))
        self.conn.commit()

    def get_article(self, collection: str, pid: str) -> ArticleRecord | None:
        row = self.conn.execute("SELECT * FROM articles WHERE collection=? AND pid=?", (collection, pid)).fetchone()
        if not row:
            return None
        return ArticleRecord(collection=row["collection"], pid=row["pid"], doi=row["doi"], title=row["title"],
                             titles_all=json.loads(row["titles_all"] or "{}"), authors=json.loads(row["authors"] or "[]"),
                             journal_title=row["journal_title"], issn=row["issn"], year=row["year"],
                             doc_type=row["doc_type"], abstract=row["abstract"],
                             keywords=json.loads(row["keywords"] or "[]"), url_original=row["url_original"],
                             url_site=row["url_site"], processing_date=row["processing_date"])

    # --- XML ---
    def upsert_xml(self, collection, pid, fmt, path, status, ctype, nbytes, sha, valid, reasons):
        self.conn.execute(
            "INSERT OR REPLACE INTO xml_files (collection,pid,fmt,path,http_status,content_type,bytes,sha256,valid,reasons)"
            " VALUES (?,?,?,?,?,?,?,?,?,?)",
            (collection, pid, fmt, path, status, ctype, nbytes, sha, int(valid), json.dumps(reasons, ensure_ascii=False)))
        self.conn.commit()

    # --- texto completo ---
    def upsert_fulltext(self, collection, pid, parsed: dict):
        self.conn.execute(
            "INSERT OR REPLACE INTO fulltext (collection,pid,title,authors,affiliations,abstracts,keywords,sections,"
            "ref_count,refs,has_body) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (collection, pid, parsed.get("title"),
             json.dumps(parsed["authors"], ensure_ascii=False), json.dumps(parsed["affiliations"], ensure_ascii=False),
             json.dumps(parsed["abstracts"], ensure_ascii=False), json.dumps(parsed["keywords"], ensure_ascii=False),
             json.dumps(parsed["sections"], ensure_ascii=False), len(parsed["references"]),
             json.dumps(parsed["references"], ensure_ascii=False), int(parsed["has_body"])))
        self.conn.commit()

    def save_run(self, started, finished, config: dict, diagnostics: dict):
        self.conn.execute("INSERT INTO runs (started_at,finished_at,config,diagnostics) VALUES (?,?,?,?)",
                          (started, finished, json.dumps(config, ensure_ascii=False, default=str),
                           json.dumps(diagnostics, ensure_ascii=False, default=str)))
        self.conn.commit()

    # --- exportación ---
    def to_dataframe(self) -> pd.DataFrame:
        return pd.read_sql_query(
            """SELECT a.collection, a.pid, a.doi, a.title, a.authors, a.journal_title, a.issn, a.year, a.doc_type,
                      a.abstract, a.keywords, a.url_original, a.url_site, a.metadata_complete,
                      x.valid AS xml_valid, x.path AS xml_path, f.has_body, f.ref_count, f.sections
               FROM articles a LEFT JOIN xml_files x ON x.collection=a.collection AND x.pid=a.pid
               LEFT JOIN fulltext f ON f.collection=a.collection AND f.pid=a.pid""", self.conn)

    def export(self, fmt: str, out_dir: str, name: str = "resultados", keys=None) -> str:
        """keys: iterable de (colección, pid). Si se da, exporta SOLO esos (los de la búsqueda);
        si no, exporta toda la caché local (todo lo descargado alguna vez)."""
        Path(out_dir).mkdir(parents=True, exist_ok=True)
        df = self.to_dataframe()
        if keys is not None:
            ks = set(keys)
            df = df[[(c, p) in ks for c, p in zip(df["collection"], df["pid"])]]
        p = Path(out_dir) / f"{name}.{fmt}"
        if fmt == "csv":
            df.to_csv(p, index=False, encoding="utf-8-sig")
        elif fmt in ("xlsx", "excel"):
            p = p.with_suffix(".xlsx")
            import re
            _ilegal = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")  # caracteres que openpyxl rechaza
            df = df.map(lambda v: _ilegal.sub("", v)[:32000] if isinstance(v, str) else v)
            df.to_excel(p, index=False)
        elif fmt == "json":
            df.to_json(p, orient="records", force_ascii=False, indent=2)
        else:
            raise ValueError(f"Formato no soportado: {fmt}")
        return str(p)
