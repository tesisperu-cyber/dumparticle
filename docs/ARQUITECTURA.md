# Arquitectura
```
main.py (CLI) ─> core/pipeline.py ─> harvester ─> articlemeta ─> client (HTTP, reintentos)
                                  │        └─> boolean_engine + normalizer
                                  ├─> deduplicator
                                  ├─> xml_downloader ─> validator
                                  ├─> jats_parser
                                  └─> database/repository (SQLite) ─> export CSV/XLSX/JSON
core/diagnostics.py (contadores por fase)   config/settings.py (todo configurable)
```
Cambios respecto al esquema propuesto: se añadieron `core/pipeline.py` (orquestación testeable por separado) y
`core/diagnostics.py` (panel exigido en §9). `kernel.py` es un adaptador desactivado hasta verificar rutas.

Decisiones: (1) sin `eval`: lexer + parser descendente recursivo + AST. (2) XML con `resolve_entities=False`,
`no_network=True` (anti-XXE). (3) Caché en SQLite: reanudar sin repetir peticiones. (4) Los filtros de año se aplican
al año de publicación del metadato, no a `from/until` del servicio (que se refiere a fecha de procesamiento).
(5) XML inválido se conserva como `.invalid.txt` para diagnóstico. (6) PID de ArticleMeta ≠ ID de Kernel: no se mezclan.
(7) Etiquetas de sección originales se conservan; categoría normalizada en campo aparte; secciones no estándar → `otra`.
