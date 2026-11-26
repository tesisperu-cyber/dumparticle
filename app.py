"""DumpArticle SciELO: búsqueda temática por cosecha ArticleMeta + ecuación local."""
from pathlib import Path
import sys

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dumparticle.client import ArticleMetaClient, COLLECTIONS
from dumparticle.exporter import dump_articles

st.set_page_config(page_title="DumpArticle · SciELO", page_icon="📚", layout="wide")
st.title("DumpArticle · SciELO")
st.caption(
    "Búsqueda temática mediante cosecha de metadatos ArticleMeta "
    "y evaluación local de ecuaciones booleanas."
)

# Estado persistente de la última ejecución.
st.session_state.setdefault("da_rows", [])
st.session_state.setdefault("da_stats", [])
st.session_state.setdefault("da_eq", "")
st.session_state.setdefault("da_error", "")
st.session_state.setdefault("da_search_done", False)

with st.sidebar:
    st.header("Configuración")
    base = st.text_input(
        "API SciELO ArticleMeta",
        value="https://articlemeta.scielo.org/api/v1/",
    )
    timeout = st.number_input("Timeout (segundos)", 5, 180, 45)
    pause = st.number_input(
        "Pausa entre solicitudes (segundos)", 0.0, 5.0, 0.3, 0.1
    )
    st.markdown("---")
    st.warning(
        "La búsqueda recorre metadatos de ArticleMeta y filtra localmente. "
        "No utiliza search.scielo.org ni el archivo articles.json.zip."
    )

st.subheader("1. Ecuación temática")
eq = st.text_area(
    "Ecuación booleana",
    value=(
        '("inteligencia artificial" OR "inteligência artificial" '
        'OR "artificial intelligence") AND '
        "(educ* OR ensino OR enseñanza OR teaching OR learning "
        "OR aprendizaje OR aprendizagem)"
    ),
    height=125,
)
st.caption(
    "Operadores AND, OR, NOT; frases entre comillas; paréntesis; "
    "truncamiento con * al final. La búsqueda se aplica a título, "
    "resumen y palabras clave."
)

all_cols = list(COLLECTIONS)
default_cols = [
    code for code in
    ["per", "scl", "col", "chl", "mex", "arg", "cub", "ven", "ury", "cri", "bol", "spa", "prt"]
    if code in all_cols
]
selected = st.multiselect(
    "Colecciones SciELO",
    options=all_cols,
    default=default_cols,
    format_func=lambda x: f"{x} · {COLLECTIONS[x]}",
)

c1, c2, c3, c4 = st.columns(4)
with c1:
    y0 = st.number_input("Año inicial", 1900, 2100, 2023)
with c2:
    y1 = st.number_input("Año final", 1900, 2100, 2026)
with c3:
    max_results = st.number_input("Máximo de coincidencias", 1, 5000, 100)
with c4:
    max_scan = st.number_input(
        "Máximo escaneo por colección", 100, 100000, 3000, 100
    )

c5, c6 = st.columns(2)
with c5:
    max_seconds = st.number_input(
        "Tiempo máximo por colección (segundos)", 30, 7200, 600, 30
    )
with c6:
    issn = st.text_input("ISSN (opcional)")

st.caption(
    "La cosecha puede ser lenta. El año se filtra por metadatos; "
    "el PID se usa solo como preselección cuando contiene un año reconocible."
)

if y0 > y1:
    st.error("El año inicial no puede ser posterior al año final.")

search_clicked = st.button(
    "Buscar artículos",
    type="primary",
    disabled=not (eq.strip() and selected) or y0 > y1,
)

if search_clicked:
    # Evita mostrar resultados antiguos como si pertenecieran a esta búsqueda.
    st.session_state["da_rows"] = []
    st.session_state["da_stats"] = []
    st.session_state["da_eq"] = eq
    st.session_state["da_error"] = ""
    st.session_state["da_search_done"] = False

    progress = st.progress(0)
    status = st.empty()
    live = st.empty()
    stats_placeholder = st.empty()

    try:
        client = ArticleMetaClient(
            base_url=base.strip(),
            timeout=int(timeout),
            pause_seconds=float(pause),
        )

        def update(info):
            """Actualiza el estado visible sin presuponer métricas no documentadas."""
            collection = info.get("collection", "—")
            scanned = info.get("scanned", 0)
            matched = info.get("matched", 0)
            found = info.get("found", 0)
            status.write(
                f"**Colección {collection}:** {scanned} registros examinados · "
                f"{matched} coincidencias · {found} acumuladas"
            )
            live.json(info)

        with st.spinner("Cosechando metadatos y evaluando la ecuación..."):
            rows = client.search_articles(
                eq,
                selected,
                issn.strip() or None,
                int(y0),
                int(y1),
                int(max_results),
                int(max_scan),
                int(max_seconds),
                update,
            )

        st.session_state["da_rows"] = rows or []
        st.session_state["da_stats"] = getattr(client, "last_stats", []) or []
        st.session_state["da_search_done"] = True
        progress.progress(100)
        status.success("La búsqueda terminó.")

    except Exception as exc:
        st.session_state["da_error"] = f"{type(exc).__name__}: {exc}"
        # Conserva las estadísticas parciales si el cliente llegó a crearlas.
        if "client" in locals():
            st.session_state["da_stats"] = getattr(client, "last_stats", []) or []
        st.session_state["da_search_done"] = True
        status.error("La búsqueda se interrumpió antes de completarse.")
        progress.empty()

# Mostrar siempre el resultado y las estadísticas, incluso si hay cero coincidencias.
if st.session_state["da_error"]:
    st.error(f"**Error durante la búsqueda:** {st.session_state['da_error']}")
    st.info(
        "Una búsqueda interrumpida no debe interpretarse como una búsqueda "
        "completada sin resultados. Revisa las estadísticas parciales."
    )

rows = st.session_state.get("da_rows", [])
stats = st.session_state.get("da_stats", [])

if st.session_state.get("da_search_done") and not st.session_state["da_error"]:
    if rows:
        st.success(f"Artículos encontrados: {len(rows)}")
    else:
        st.warning(
            "La búsqueda terminó, pero no devolvió coincidencias. "
            "Esto no demuestra por sí solo que SciELO carezca de artículos "
            "sobre el tema: revisa los registros cosechados y el filtrado."
        )

if st.session_state.get("da_search_done"):
    st.subheader("2. Control de cosecha por colección")
    if stats:
        stats_df = pd.DataFrame(stats)
        st.dataframe(stats_df, use_container_width=True, hide_index=True)

        # Resumen solo de columnas presentes en las estadísticas reales.
        numeric_cols = stats_df.select_dtypes(include="number").columns.tolist()
        if numeric_cols:
            summary = {
                col: pd.to_numeric(stats_df[col], errors="coerce").fillna(0).sum()
                for col in numeric_cols
            }
            st.caption("Totales de las columnas numéricas informadas por el cliente:")
            st.json(summary)
    else:
        st.info(
            "El cliente no proporcionó estadísticas de cosecha "
            "(last_stats vacío o no disponible)."
        )

if rows:
    st.subheader("3. Resultados bibliográficos")
    df = pd.DataFrame(rows)

    display_cols = [
        col for col in
        ["title", "authors", "year", "journal", "doi", "issn", "collection", "language", "url"]
        if col in df.columns
    ]
    st.dataframe(
        df[display_cols],
        use_container_width=True,
        hide_index=True,
    )

    labels = {
        (
            f"{i + 1}. {row.get('title') or row.get('code', 'Sin título')} · "
            f"{row.get('year', 'Año desconocido')} · "
            f"{row.get('collection', 'Colección desconocida')}"
        ): row
        for i, row in enumerate(rows)
    }
    chosen = st.multiselect(
        "Selecciona los artículos que deseas descargar",
        list(labels),
        default=list(labels),
    )
    fmt = st.selectbox("Formato XML", ["xmlrsps", "xmlwos"])

    if st.button(
        "Descargar XML seleccionados y crear ZIP",
        type="primary",
        disabled=not chosen,
    ):
        outdir = ROOT / "outputs"
        outdir.mkdir(exist_ok=True)
        path = outdir / "dumparticle_scielo.zip"
        client = ArticleMetaClient(
            base_url=base.strip(),
            timeout=int(timeout),
            pause_seconds=float(pause),
        )
        download_progress = st.progress(0)
        message = st.empty()

        try:
            def download_update(done, total):
                if total:
                    download_progress.progress(min(done / total, 1.0))
                message.write(f"Procesados {done}/{total}")

            report = dump_articles(
                client,
                [labels[label] for label in chosen],
                path,
                fmt,
                download_update,
            )
            st.success(
                f"XML descargados: {report['downloaded']} · "
                f"Fallidos: {report['failed']}"
            )
            if report.get("manifest"):
                st.dataframe(
                    pd.DataFrame(report["manifest"]),
                    use_container_width=True,
                    hide_index=True,
                )
            st.download_button(
                "Descargar ZIP",
                path.read_bytes(),
                file_name=path.name,
                mime="application/zip",
            )
        except Exception as exc:
            st.error(f"Error al crear la descarga: {type(exc).__name__}: {exc}")

elif not st.session_state.get("da_search_done"):
    st.markdown("### Flujo de trabajo")
    st.markdown(
        "1. Escribir la ecuación. 2. Elegir colecciones y límites. "
        "3. Revisar los artículos coincidentes. "
        "4. Seleccionar y descargar sus XML."
    )

st.caption(
    "Los identificadores se recuperan automáticamente y se utilizan "
    "internamente para solicitar los XML a ArticleMeta."
)
