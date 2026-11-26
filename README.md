# DumpArticle · SciELO v0.3.0

Buscador temático basado en la arquitectura del cuaderno `buscador_scielo_cascada_GROBIDOKOK.ipynb`. Recupera identificadores y fichas desde SciELO ArticleMeta, aplica una ecuación booleana local sobre título, resumen y palabras clave, permite seleccionar artículos y descarga XML mediante ArticleMeta.

## Qué hace
- Cosecha paginada por colección mediante `article/identifiers/`.
- Recupera fichas individuales con `article/`.
- Ecuaciones `AND`, `OR`, `NOT`, frases entre comillas, paréntesis y truncamiento final `*`.
- Normaliza acentos antes de evaluar términos.
- Filtros por año e ISSN; límite de coincidencias, registros escaneados y tiempo por colección.
- Deduplicación por DOI o título+año+ISSN.
- Descarga XML `xmlrsps`/`xmlwos`, ZIP y `manifest.csv`.
- Control de cosecha por colección para transparentar límites y cobertura.

## Diferencia importante
SciELO ArticleMeta no ofrece aquí una búsqueda booleana temática remota. La aplicación recorre metadatos por colección y evalúa la ecuación localmente. Por tanto, el resultado depende de los límites configurados y del orden/cobertura del catálogo. Un resultado cero no demuestra que SciELO no tenga artículos sobre el tema.

## Ejecutar localmente
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Desplegar en Streamlit Community Cloud
1. Descomprime el ZIP.
2. Sustituye los archivos del repositorio por el contenido del proyecto.
3. Haz commit y push a GitHub.
4. Streamlit Cloud reconstruirá la aplicación.

## Recomendación de primera prueba
- Una colección (por ejemplo `scl` o `per`).
- Máximo 100 resultados.
- Máximo 500 registros escaneados.
- 300–600 segundos.
- Verifica el resumen por colección antes de ampliar el escaneo.

## Limitaciones y validación
Las pruebas incluidas verifican el parser booleano, la normalización y la paginación con respuestas simuladas. No certifican disponibilidad en tiempo real de ArticleMeta ni que todas las colecciones permitan cosecha desde Streamlit Cloud. La descarga XML se debe probar con PIDs reales después del despliegue. No incluye en esta versión el cosechador OAI-PMH alternativo, la cascada XML del sitio → HTML → PDF/GROBID ni los enriquecimientos OpenAlex/SCImago del notebook; se pueden integrar como módulos posteriores. El filtro de idioma tampoco está expuesto en esta versión.

## Procedencia
Adaptación de la lógica de recuperación temática del cuaderno del usuario. La ecuación se evalúa sobre `title`, `abstract` y `keywords` de las fichas ArticleMeta. Los campos no disponibles se conservan vacíos; no se inventan metadatos.
