"""Interfaz de línea de comandos."""
from __future__ import annotations

import argparse

from .client import ArticleMetaClient
from .exporter import dump_articles


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Descarga XML de artículos SciELO mediante ArticleMeta.")
    parser.add_argument("--collection", help="Acrónimo de colección, por ejemplo scl.")
    parser.add_argument("--issn", help="ISSN para filtrar identificadores.")
    parser.add_argument("--codes", help="Códigos separados por coma.")
    parser.add_argument("--limit", type=int, default=10, help="Máximo de artículos (predeterminado: 10).")
    parser.add_argument("--xml-format", choices=["xmlrsps", "xmlwos"], default="xmlrsps")
    parser.add_argument("--output", default="outputs/dumparticle_scielo.zip")
    parser.add_argument("--base-url", default=None)
    parser.add_argument("--timeout", type=int, default=45)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    client = ArticleMetaClient(base_url=args.base_url, timeout=args.timeout)
    if args.codes:
        identifiers = [
            {"collection": args.collection or "", "code": code.strip(), "issn": args.issn or ""}
            for code in args.codes.split(",") if code.strip()
        ]
    else:
        identifiers = client.iter_identifiers(
            collection=args.collection,
            issn=args.issn,
            limit=args.limit,
        )
    report = dump_articles(client, identifiers, args.output, args.xml_format)
    print(
        f"ZIP: {report['output_path']} | Total: {report['total']} | "
        f"Descargados: {report['downloaded']} | Fallidos: {report['failed']}"
    )


if __name__ == "__main__":
    main()
