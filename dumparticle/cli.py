"""CLI para buscar artículos por tema y descargar XML."""
from __future__ import annotations
import argparse
from .client import ArticleMetaClient
from .exporter import dump_articles

def build_parser():
    parser = argparse.ArgumentParser(description="Busca artículos SciELO por tema y descarga sus XML.")
    parser.add_argument("query", help="Tema o expresión de búsqueda")
    parser.add_argument("--collection", help="Código de colección")
    parser.add_argument("--issn", help="ISSN de la revista")
    parser.add_argument("--year-from", type=int)
    parser.add_argument("--year-to", type=int)
    parser.add_argument("--language", choices=["pt", "es", "en"])
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--xml-format", choices=["xmlrsps", "xmlwos"], default="xmlrsps")
    parser.add_argument("--output", default="outputs/dumparticle_scielo.zip")
    parser.add_argument("--base-url", default=None)
    parser.add_argument("--search-url", default=None)
    parser.add_argument("--timeout", type=int, default=45)
    return parser

def main():
    args = build_parser().parse_args()
    client = ArticleMetaClient(base_url=args.base_url, search_url=args.search_url, timeout=args.timeout)
    records = client.search_articles(
        args.query, collection=args.collection, issn=args.issn,
        year_from=args.year_from, year_to=args.year_to,
        language=args.language, limit=args.limit,
    )
    report = dump_articles(client, records, args.output, args.xml_format)
    print(f"ZIP: {report['output_path']} | Artículos: {report['total']} | "
          f"Descargados: {report['downloaded']} | Fallidos: {report['failed']}")

if __name__ == "__main__":
    main()
