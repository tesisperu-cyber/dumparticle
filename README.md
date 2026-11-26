# scielo_pybot — Recuperador bibliográfico SciELO (PYBOT)

Módulo nuevo, independiente y verificable: busca artículos en SciELO (ArticleMeta), filtra con una
ecuación booleana propia, descarga XML-JATS, extrae secciones y guarda en SQLite (export CSV/Excel/JSON).
Responsable de validación humana: Pedro.

## Estado honesto (léase primero)
| Componente | Estado |
|---|---|
| Motor booleano, normalizador, parser JATS, validador, deduplicador, SQLite, exportación, diagnóstico | **Probado** (44 pruebas offline pasan) |
| Cliente ArticleMeta (rutas, parser JSON `vNN`) | **Implementado, NO verificado en vivo**: el entorno cloud no resuelve `articlemeta.scielo.org` |
| Recuperación de un artículo real (Fase 3) | **PENDIENTE**: ejecútela en su PC con `python main.py probe` |
| Kernel / OAI-PMH | No implementado (rutas sin verificar; ver docs/LIMITACIONES.md) |
Los XML de `tests/fixtures/` son **sintéticos** (solo estructura JATS), no artículos reales.

## Instalación en Windows (PowerShell)
```powershell
# 1. Instale Python 3.11+ desde https://www.python.org/downloads/ (marque "Add python.exe to PATH")
cd C:\ruta\scielo_pybot
python -m venv .venv
.\.venv\Scripts\Activate.ps1        # si falla: Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
pip install -r requirements.txt
python -m pytest -q                  # debe dar 44 passed
python main.py init-db
python main.py probe --collection per      # PRIMERA PRUEBA con artículo real
jupyter notebook notebooks/scielo_demo.ipynb
```
**Si `probe` da APROBADO**, ya hay metadatos, PID, DOI, XML válido y secciones reales. Se genera
`exports/informe_primer_articulo.md` y los crudos en `exports/probe/`. **Envíeme esa carpeta/informe**
si algún paso falla y ajusto el parser con la respuesta real.

## Interfaz web (Streamlit)
```powershell
streamlit run app.py
```
Pestañas: prueba real, búsqueda con panel de diagnóstico y exportación, probar ecuación, analizar un XML subido.
Para Streamlit Cloud: *Main file path* = `app.py`. Ojo: no está verificado que ese servidor alcance SciELO; use la pestaña «Prueba real» para comprobarlo.

## Uso
```powershell
python main.py check-equation "(educ* OR ensino) AND ""inteligencia artificial""" "La inteligencia artificial en la educación"
python main.py parse-xml ruta\archivo.xml
python main.py search --equation "educ*" --year-from 2020 --year-to 2026 --collections per,scl --max-results 20
python main.py export --fmt xlsx
```
Todos los filtros (ecuación, colecciones, años, máximos, tiempo, ISSN, tipo) están en `config.json`
sin tocar código. Colecciones nuevas: `"extra_collections": {"mex2": "Nombre"}` y añadir el código en `collections`.

## Su propia ecuación (cualquier tema)
`config.json` se entrega **con la ecuación vacía**: cada usuario escribe la suya. Sin ecuación, `search` se detiene con un
mensaje de error (así no descarga artículos de cualquier tema).
1. Abra `config.json` y escriba su ecuación en `"equation"` (comillas internas escapadas: `\"`), o
2. pásela por consola: `python main.py search --equation "(educ* OR ensino) AND ensino"`, o
3. escríbala en la barra lateral de la interfaz Streamlit.
Para no subir su ecuación a Git, copie `config.json` a `config.local.json` (ya está en `.gitignore`) y use
`python main.py --config config.local.json search`.

## Sintaxis de ecuaciones
`AND`, `OR`, `NOT` (**en MAYÚSCULAS**), paréntesis, `"frases"`, `prefijo*`. `A NOT B` = `A AND NOT B`.
Precedencia NOT > AND > OR. Términos juntos sin operador dan error explícito. Tildes y mayúsculas se ignoran (ñ=n).
Se evalúa sobre título (todos los idiomas) + resumen + palabras clave.

## Diagnóstico
Cada ejecución imprime el panel (solicitados, recibidos, completos/incompletos, filtros, temáticos, XML ok/inválidos,
textos, errores HTTP, tiempo) y **explica por qué hay cero** en la fase donde ocurrió.
