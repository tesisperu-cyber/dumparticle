# DumpArticle SciELO

Aplicación Python para recuperar registros y descargar documentos XML individuales desde la API pública **SciELO ArticleMeta**. Está inspirada en el procesamiento `dumparticles.py` publicado por SciELO en `scieloorg/articles_meta`, pero reorganizada como una herramienta independiente, configurable y con interfaz Streamlit.

> **Alcance:** este proyecto es un cliente de la API ArticleMeta. No instala ni replica el servidor interno `articles_meta`, MongoDB, Thrift ni la infraestructura de SciELO. La disponibilidad de registros y formatos depende del servicio remoto.

## Funcionalidades

- Consultar identificadores de artículos mediante `article/identifiers`.
- Filtrar identificadores por colección, ISSN y código.
- Descargar XML de artículos individuales en `xmlrsps` o `xmlwos`.
- Empaquetar documentos recuperados en un ZIP con estructura `coleccion/ISSN/codigo.xml`.
- Guardar un manifiesto CSV con estado, código, colección, ISSN, formato y errores.
- Usar la interfaz Streamlit (`app.py`) o la línea de comandos.
- Configurar URL, timeout, tamaño de página y pausas entre solicitudes.

## Fuente original y adaptación

El script de referencia es [`processing/dumparticles.py`](https://github.com/scieloorg/articles_meta/blob/master/processing/dumparticles.py), del proyecto [`scieloorg/articles_meta`](https://github.com/scieloorg/articles_meta).

El original recorre los identificadores de toda la red SciELO por lotes de 1.000, solicita el XML individual y guarda los documentos en un ZIP. Esta implementación conserva ese flujo central, pero añade:
- límites de descarga para evitar cosechas masivas accidentales;
- filtros por colección e ISSN;
- control de errores HTTP y reintentos;
- registro de resultados y fallos;
- separación entre cliente API, proceso de descarga e interfaz.

Consulte la licencia del proyecto original antes de redistribuir fragmentos derivados. Este repositorio incluye una nota de atribución; revise y complete la licencia elegida para su distribución.

## Requisitos

- Python 3.10 o superior.
- Conexión a Internet.
- Acceso HTTP(S) a `articlemeta.scielo.org`.

## Instalación local (Windows)

```powershell
git clone https://github.com/USUARIO/dumparticle-scielo.git
cd dumparticle-scielo

py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1

python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Ejecutar la interfaz

```powershell
streamlit run app.py
```

La aplicación permite seleccionar colección, ISSN, formato XML y máximo de artículos. El ZIP se genera bajo `outputs/` y también se ofrece para descargar desde la interfaz.

## Ejecutar desde terminal

Descargar hasta 20 documentos de la colección brasileña (`scl`):

```bash
python -m dumparticle.cli --collection scl --limit 20 --xml-format xmlrsps --output outputs/scielo_dump.zip
```

Filtrar por ISSN:

```bash
python -m dumparticle.cli --issn 0102-XXXX --limit 50 --output outputs/issn_dump.zip
```

Descargar por códigos concretos:

```bash
python -m dumparticle.cli --codes S0102-XXXX2024000100001,S0102-XXXX2024000100002 --output outputs/codes_dump.zip
```

Consultar opciones:

```bash
python -m dumparticle.cli --help
```

## Formatos XML

- `xmlrsps`: formato SciELO Publishing Schema (cuando esté disponible para el registro).
- `xmlwos`: formato XML orientado a Web of Science (cuando esté disponible para el registro).

La disponibilidad y el contenido pueden variar por artículo. Que la API devuelva un XML no significa necesariamente que contenga el cuerpo completo (`body`). El manifiesto registra el resultado de cada solicitud; el usuario debe validar la estructura y cobertura del texto completo.

## Estructura del proyecto

```text
dumparticle-scielo/
├── app.py
├── dumparticle/
│   ├── __init__.py
│   ├── client.py
│   ├── exporter.py
│   └── cli.py
├── tests/
│   ├── test_exporter.py
│   └── test_client.py
├── outputs/                 # resultados locales (no se versionan)
├── .github/workflows/tests.yml
├── .gitignore
├── requirements.txt
├── README.md
├── NOTICE
└── LICENSE
```

## API utilizada

Base URL por defecto: `https://articlemeta.scielo.org/api/v1/`

Rutas principales:
- `GET article/identifiers?offset=0`
- `GET article?code={code}&format={xmlrsps|xmlwos}`

La documentación de ArticleMeta describe los servicios REST para recuperar registros de artículos, revistas, fascículos y colecciones. SciELO recomienda archivos de lote para cargas iniciales completas: recuperar todos los registros por HTTP puede tomar varios días.

## Variables de entorno

| Variable | Descripción | Valor predeterminado |
|---|---|---|
| `SCIELO_ARTICLEMETA_URL` | URL base de ArticleMeta | `https://articlemeta.scielo.org/api/v1/` |
| `SCIELO_TIMEOUT` | Timeout por solicitud, segundos | `45` |
| `SCIELO_PAGE_SIZE` | Tamaño de página solicitado | `1000` |

## Pruebas

```bash
python -m pytest -q
```

Las pruebas usan respuestas simuladas (`requests-mock` no es necesario) y no descargan datos reales. Para una validación operativa, ejecute una descarga pequeña y conserve el manifiesto.

## Uso responsable

- No ejecute cosechas completas sin evaluar el volumen, la conectividad y las condiciones del servicio.
- Use límites bajos para pruebas iniciales.
- Respete las políticas, licencias y condiciones de uso de los contenidos de cada revista.
- No elimine la atribución a SciELO ni presente esta herramienta como un producto oficial de SciELO.

## Próximos pasos

1. Validar conectividad actual y formatos XML con una muestra pequeña de artículos.
2. Comparar la estructura XML descargada con el XML-JATS esperado.
3. Integrar el módulo probado en `scielo-explorer` conservando la trazabilidad entre identificador, metadatos y texto completo.
