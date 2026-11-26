# Informe de pruebas
## Cloud (sandbox de Claude, 26-nov-2026)
- `pytest`: **39 passed** (booleano, normalización, filtros, deduplicación, XML, extracción, SQLite/exportación, diagnóstico).
- Conectividad: `articlemeta.scielo.org` y `www.scielo.br` → *Could not resolve host* (curl y `main.py probe`).
  Evidencia: `docs/INFORME_PRIMER_ARTICULO_cloud.md`. **Integración con SciELO: NO probada en cloud.**
- El panel de diagnóstico explicó correctamente el cero ("no se obtuvo ni un identificador… errores de red").
## Local (Windows) — PENDIENTE
Completar tras ejecutar: `python -m pytest -q`, `python main.py probe --collection per`, `python main.py search ...`.
| Prueba | Resultado | Fecha |
|---|---|---|
| pytest | | |
| probe (colecciones, identificadores, JSON, XML, extracción) | | |
| search pequeña (5–20 artículos) | | |

## Streamlit Cloud (26-nov-2026) — pestaña «Prueba real», colección per
Conectividad con ArticleMeta: **sí**. Pasos 1–5 reportados OK en la primera versión; el paso 5 salió con `secciones=[]` (XML sin cuerpo,
artículo de 2006), lo que mostró que el criterio de aprobación era laxo. Corregido: ahora exige secciones y busca un artículo con cuerpo. Pendiente re-ejecutar.
