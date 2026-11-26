# DumpArticle SciELO

Aplicación Python para **buscar artículos científicos por tema en SciELO** y descargar sus documentos XML mediante SciELO ArticleMeta.

## Flujo funcional

1. El usuario escribe un tema o expresión de búsqueda.
2. La aplicación consulta SciELO Search (`https://search.scielo.org/`) en formato JSON.
3. Normaliza los resultados que incluyen un PID/código de artículo y permite aplicar filtros de colección, ISSN, año e idioma.
4. El usuario revisa los resultados y selecciona los artículos.
5. SciELO ArticleMeta recupera el XML individual mediante `article?code=PID&format=xmlrsps|xmlwos`.
6. La aplicación genera un ZIP con los XML y un `manifest.csv` que conserva título, autores, revista, año, DOI, PID, URL, consulta y estado de descarga.

**Importante:** SciELO Search y ArticleMeta son servicios distintos. Search descubre los artículos; ArticleMeta recupera sus documentos XML. Los identificadores se manejan internamente y no se solicitan al usuario.

## Estado y limitación de validación

El conector utiliza el endpoint web de búsqueda de SciELO con `q`, `format=json`, `count` y `lang`. La estructura JSON puede cambiar y el servicio puede limitar solicitudes automatizadas. El proyecto incluye pruebas simuladas para validar el procesamiento de respuestas, pero estas no demuestran disponibilidad en vivo. Antes de utilizarlo como recuperador de producción, se debe ejecutar una búsqueda real pequeña y verificar el JSON devuelto y la descarga de un XML.

Si SciELO Search no devuelve JSON o una estructura reconocible, la aplicación informa el error. **No recurre silenciosamente a descargar identificadores generales**, porque eso no cumpliría la búsqueda temática solicitada.

## Requisitos

- Python 3.10 o superior.
- Conexión a Internet.
- Acceso HTTP(S) a `search.scielo.org` y `articlemeta.scielo.org`.

## Instalación local (Windows)

```powershell
git clone https://github.com/USUARIO/dumparticle-scielo.git
cd dumparticle-scielo
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Ejecutar Streamlit

```powershell
streamlit run app.py
```

## Ejecutar pruebas

```bash
python -m pytest -q
```

Las pruebas utilizan respuestas simuladas. No descargan datos reales.

## Servicios y rutas

- SciELO Search: `https://search.scielo.org/` — descubrimiento por texto libre.
- SciELO ArticleMeta: `https://articlemeta.scielo.org/api/v1/article` — recuperación del XML por PID/código.
- Formatos: `xmlrsps` (SciELO Publishing Schema) y `xmlwos` (cuando estén disponibles para el registro).

## Variables de entorno

| Variable | Descripción | Predeterminado |
|---|---|---|
| `SCIELO_ARTICLEMETA_URL` | Base de ArticleMeta | `https://articlemeta.scielo.org/api/v1/` |
| `SCIELO_SEARCH_URL` | URL de búsqueda | `https://search.scielo.org/` |
| `SCIELO_TIMEOUT` | Timeout en segundos | `45` |
| `SCIELO_PAGE_SIZE` | Reservado para paginación | `50` |

## Uso responsable

- Comenzar con muestras pequeñas.
- Respetar las condiciones de uso y licencias de cada publicación.
- La disponibilidad de XML y el contenido de texto completo dependen del artículo.
- No presentar la herramienta como producto oficial de SciELO.

## Referencias técnicas

- [SciELO Project Documentation](https://scielo.readthedocs.io/)
- [SciELO ArticleMeta API](https://articlemeta.scielo.org/api/v1/)
- [SciELO Search](https://search.scielo.org/)
- [SciELO Publishing Schema](https://docs.scielo.org/projects/scielo-publishing-schema/)
