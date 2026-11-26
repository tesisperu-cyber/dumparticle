"""Panel de diagnóstico: contadores por fase + explicación de 'cero resultados'."""
from __future__ import annotations
import time
from collections import defaultdict

KEYS = [
    ("requested", "Registros solicitados (metadatos)"),
    ("received", "Registros recibidos"),
    ("complete", "Metadatos completos"),
    ("incomplete", "Metadatos incompletos"),
    ("temporal_ok", "Coincidencias temporales/filtros (año, ISSN, tipo)"),
    ("thematic_ok", "Coincidencias temáticas"),
    ("identified", "Artículos identificados (con PID)"),
    ("xml_requested", "XML solicitados"),
    ("xml_ok", "XML recuperados y válidos"),
    ("xml_invalid", "XML inválidos / no disponibles"),
    ("fulltext_ok", "Textos completos extraídos"),
]


class Diagnostics:
    def __init__(self):
        self.t0 = time.time()
        self.c = defaultdict(int)
        self.per_collection = defaultdict(lambda: defaultdict(int))
        self.http_errors = defaultdict(int)
        self.notes: list[str] = []
        self.identifiers_listed = 0

    def inc(self, key: str, n: int = 1, collection: str | None = None):
        self.c[key] += n
        if collection:
            self.per_collection[collection][key] += n

    def http_error(self, label: str):
        self.http_errors[str(label)] += 1

    def note(self, msg: str):
        self.notes.append(msg)

    def explain(self) -> str:
        c = self.c
        if c["thematic_ok"] > 0:
            return f"{c['thematic_ok']} registro(s) coinciden con la ecuación."
        if self.identifiers_listed == 0:
            return ("CERO porque no se obtuvo ni un identificador del servicio: "
                    f"errores HTTP/red = {dict(self.http_errors) or 'ninguno registrado'}. "
                    "Revise conectividad y endpoint (python main.py probe).")
        if c["received"] == 0:
            return (f"CERO porque se listaron {self.identifiers_listed} identificadores pero no se recibió ningún "
                    f"registro de metadatos. Errores: {dict(self.http_errors)}.")
        if c["complete"] == 0:
            return (f"CERO porque ninguno de los {c['received']} registros recibidos tiene metadatos completos "
                    "(pid+título+año+revista): probable diferencia en el formato JSON de ArticleMeta; revise el parser.")
        if c["temporal_ok"] == 0:
            return (f"CERO porque de {c['complete']} registros completos ninguno pasa los filtros "
                    "(año/ISSN/tipo documental). Amplíe el rango o quite filtros.")
        return (f"CERO coincidencias temáticas: se evaluaron {c['temporal_ok']} registros que pasan filtros "
                f"(de {c['received']} recibidos) y ninguno satisface la ecuación. Esto es un resultado real de la "
                "muestra revisada, no un error; aumente max_records_per_collection o relaje la ecuación.")

    def to_dict(self) -> dict:
        return {
            "counters": {k: self.c[k] for k, _ in KEYS},
            "identifiers_listed": self.identifiers_listed,
            "http_errors": dict(self.http_errors),
            "per_collection": {k: dict(v) for k, v in self.per_collection.items()},
            "notes": self.notes,
            "elapsed_seconds": round(time.time() - self.t0, 2),
            "explanation": self.explain(),
        }

    def format(self) -> str:
        d = self.to_dict()
        lines = ["=== PANEL DE DIAGNÓSTICO ===", f"Identificadores listados: {d['identifiers_listed']}"]
        for k, label in KEYS:
            lines.append(f"{label}: {d['counters'][k]}")
        lines.append(f"Errores HTTP/red: {d['http_errors'] or 'ninguno'}")
        lines.append(f"Tiempo de ejecución: {d['elapsed_seconds']} s")
        if d["per_collection"]:
            lines.append("Por colección:")
            for col, v in d["per_collection"].items():
                lines.append(f"  {col}: " + ", ".join(f"{k}={n}" for k, n in v.items()))
        for n in d["notes"]:
            lines.append(f"Nota: {n}")
        lines.append("Explicación: " + d["explanation"])
        return "\n".join(lines)
