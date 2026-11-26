"""Configuración central. Todo valor es modificable vía JSON (config.json) o CLI,
sin editar código fuente. Nuevas colecciones: añadir en 'extra_collections'."""
from __future__ import annotations
import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional

BASE_DIR = Path(__file__).resolve().parent.parent

# Códigos de colección SciELO solicitados en el proyecto.
DEFAULT_COLLECTIONS = {
    "per": "Perú", "scl": "Brasil", "col": "Colombia", "chl": "Chile",
    "mex": "México", "arg": "Argentina", "cub": "Cuba", "ven": "Venezuela",
    "ury": "Uruguay", "cri": "Costa Rica", "bol": "Bolivia",
    "spa": "España", "prt": "Portugal",
}


@dataclass
class Settings:
    # --- búsqueda temática ---
    equation: str = ""
    collections: list = field(default_factory=lambda: list(DEFAULT_COLLECTIONS))
    extra_collections: dict = field(default_factory=dict)   # {"codigo": "Nombre"}
    year_from: Optional[int] = None
    year_to: Optional[int] = None
    max_results: int = 100
    max_records_per_collection: int = 500
    max_seconds_per_collection: int = 120
    issn: Optional[str] = None
    doc_type: Optional[str] = None          # p.ej. "research-article" (JATS) o código SciELO
    # --- servicios ---
    articlemeta_base: str = "https://articlemeta.scielo.org/api/v1"
    identifiers_page_size: int = 1000
    request_timeout: int = 30
    retries: int = 3
    user_agent: str = "PYBOT-SciELO/0.1 (investigacion academica; contacto: Pedro)"
    # --- XML ---
    download_xml: bool = True
    xml_formats: list = field(default_factory=lambda: ["xmlrsps"])
    # --- rutas ---
    db_path: str = str(BASE_DIR / "scielo_pybot.sqlite")
    xml_dir: str = str(BASE_DIR / "data" / "xml")
    exports_dir: str = str(BASE_DIR / "exports")
    logs_dir: str = str(BASE_DIR / "logs")

    def all_collections(self) -> dict:
        d = dict(DEFAULT_COLLECTIONS)
        d.update(self.extra_collections or {})
        return d

    @classmethod
    def load(cls, path: str | Path | None) -> "Settings":
        s = cls()
        if path and Path(path).exists():
            data = json.loads(Path(path).read_text(encoding="utf-8"))
            for k, v in data.items():
                if k.startswith("_"):
                    continue
                if not hasattr(s, k):
                    raise KeyError(f"Parámetro desconocido en config: {k}")
                setattr(s, k, v)
        return s

    def save(self, path: str | Path) -> None:
        Path(path).write_text(json.dumps(asdict(self), indent=2, ensure_ascii=False), encoding="utf-8")
