# Limitaciones técnicas identificadas
0. **Hallazgos de la prueba real (Streamlit Cloud, 26-nov-2026)**: confirmados en vivo `/article/identifiers/`, `/article/?code=` (JSON con título v12, año v65, revista v100) y `format=xmlrsps` (HTTP 200, `application/xml`, raíz `article`).
   `/collection/` devolvió `null` (se añadió respaldo `/collection/identifiers/` y consulta `?code=`, sin verificar). El primer artículo (2006, PID S1609-9117…) trajo
   XML válido con 3 autores, 2 resúmenes y 22 referencias pero **sin secciones de cuerpo**: los XML de artículos antiguos pueden no tener texto completo en `xmlrsps`.
   `probe` ahora revisa varios artículos recientes hasta hallar uno con cuerpo. Sin XML con cuerpo no hay "texto completo" por este camino (alternativa fuera de alcance: HTML del sitio).
   DOI, resumen y palabras clave del JSON aún sin confirmar (el paso 3 muestra `campos_article`); el DOI se completa desde el XML cuando falta.
1. **Sin verificación en vivo**: el entorno cloud no resuelve dominios de SciELO (DNS). Rutas ArticleMeta y mapeo JSON `vNN`
   (v880 PID, v237 DOI, v12 título, v83 resumen, v85 palabras clave, v10 autores, v65 fecha, v100/v400 revista/ISSN, v71 tipo)
   provienen de documentación pública/clientes de terceros; deben confirmarse con `main.py probe`.
2. `format=xmlrsps` (SciELO Publishing Schema, basado en JATS) se asume como mecanismo de XML; no confirmado en vivo.
   Si la respuesta es otro formato, `xml_formats` en config permite probar alternativas sin editar código.
3. Kernel y OAI-PMH: no implementados (rutas sin verificar; no se inventan).
4. La búsqueda temática local requiere un GET de metadatos por artículo: lenta en colecciones grandes.
   Mitigaciones: caché SQLite, límites por colección/tiempo, filtro ISSN. Pendiente medir rendimiento real.
5. `from/until` de ArticleMeta filtra por fecha de procesamiento, no de publicación.
6. Tipo documental: depende de que el JSON/JATS lo traiga (v71 / `article-type`); si falta, el filtro excluye el registro.
7. ñ→n y ç→c en la normalización puede unir palabras distintas (año/ano); es un compromiso deliberado.
8. Términos de ecuación sin operador entre sí producen error (no se asume AND).
9. Las pruebas offline usan XML **sintéticos**; falta añadir 2–3 XML reales (si su licencia lo permite) a `tests/fixtures/`.
