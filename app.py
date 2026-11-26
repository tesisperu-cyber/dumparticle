"""Interfaz Streamlit de búsqueda temática y descarga XML SciELO."""
from pathlib import Path
import sys
import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
from dumparticle.client import ArticleMetaClient
from dumparticle.exporter import dump_articles

st.set_page_config(page_title="DumpArticle SciELO", page_icon="📚", layout="wide")
st.title("DumpArticle · SciELO")
st.caption("Buscador temático de artículos científicos y recuperación de sus documentos XML")

with st.sidebar:
    st.header("Configuración")
    base_url = st.text_input("API ArticleMeta (descarga XML)",
        value="https://articlemeta.scielo.org/api/v1/")
    search_url = st.text_input("SciELO Search (búsqueda temática)",
        value="https://search.scielo.org/")
    timeout = st.number_input("Timeout (segundos)", min_value=5, max_value=180, value=45)
    st.markdown("---")
    st.caption("La búsqueda temática descubre artículos. ArticleMeta se utiliza después para descargar el XML de cada PID.")

st.subheader("1. Buscar artículos por tema")
query = st.text_input("Tema o expresión de búsqueda",
    placeholder="Ej.: inteligencia artificial generativa en educación superior")
c1, c2, c3, c4 = st.columns(4)
with c1:
    collection = st.selectbox("Colección", ["Todas", "scl", "spa", "mex", "col", "chl", "arg", "cub", "ven", "prt", "zaf"])
with c2:
    language = st.selectbox("Idioma", ["Todos", "pt", "es", "en"])
with c3:
    year_from = st.number_input("Año desde (opcional)", min_value=1900, max_value=2100, value=2000)
with c4:
    year_to = st.number_input("Año hasta (opcional)", min_value=1900, max_value=2100, value=2026)
c5, c6 = st.columns(2)
with c5: issn = st.text_input("ISSN de revista (opcional)")
with c6: limit = st.number_input("Máximo de resultados", min_value=1, max_value=100, value=30)

if st.button("Buscar artículos", type="primary", disabled=not query.strip()):
    try:
        client = ArticleMetaClient(base_url=base_url, search_url=search_url, timeout=int(timeout))
        with st.spinner("Buscando artículos en SciELO..."):
            rows = client.search_articles(
                query=query,
                collection=None if collection == "Todas" else collection,
                issn=issn.strip() or None,
                year_from=int(year_from) if year_from else None,
                year_to=int(year_to) if year_to else None,
                language=None if language == "Todos" else language,
                limit=int(limit),
            )
        st.session_state["dumparticle_records"] = rows
        st.session_state["dumparticle_query"] = query
        if rows: st.success(f"Artículos recuperados: {len(rows)}")
        else: st.warning("La búsqueda no devolvió artículos con PID descargable y los filtros indicados.")
    except Exception as exc:
        st.error(f"No fue posible realizar la búsqueda temática: {exc}")
        st.info("No se ha sustituido la búsqueda temática por un recorrido general de identificadores.")

records = st.session_state.get("dumparticle_records", [])
if records:
    st.subheader("2. Revisar y seleccionar resultados")
    display_cols = ["title", "authors", "journal", "year", "doi", "collection", "language"]
    frame = pd.DataFrame(records)
    st.dataframe(frame[[c for c in display_cols if c in frame.columns]],
        use_container_width=True, hide_index=True)
    labels = {
        f"{i+1}. {r.get('title') or r['code']} | {r.get('year','')} | {r.get('doi') or r['code']}": r
        for i, r in enumerate(records)
    }
    selected_labels = st.multiselect("Artículos que deseas descargar",
        options=list(labels.keys()), default=list(labels.keys()))
    selected_records = [labels[label] for label in selected_labels]

    st.subheader("3. Descargar XML")
    xml_format = st.selectbox("Formato XML", ["xmlrsps", "xmlwos"], index=0)
    if st.button("Descargar XML seleccionados y crear ZIP", type="primary",
                 disabled=not selected_records):
        output_dir = ROOT / "outputs"
        output_dir.mkdir(exist_ok=True)
        output_path = output_dir / "dumparticle_scielo.zip"
        client = ArticleMetaClient(base_url=base_url, search_url=search_url, timeout=int(timeout))
        progress, status = st.progress(0.0), st.empty()
        try:
            report = dump_articles(
                client, selected_records, output_path, xml_format,
                progress_callback=lambda done, total: (
                    progress.progress(done / total if total else 1.0),
                    status.write(f"Procesados {done} de {total}")
                ),
            )
            st.success(f"XML descargados: {report['downloaded']} · Fallidos: {report['failed']}")
            st.dataframe(pd.DataFrame(report["manifest"]), use_container_width=True, hide_index=True)
            with open(output_path, "rb") as file_obj:
                st.download_button("Descargar ZIP", data=file_obj,
                    file_name=output_path.name, mime="application/zip")
        except Exception as exc:
            st.error(f"Error durante la descarga: {exc}")
else:
    st.markdown("### Flujo de trabajo")
    st.markdown("1. Escribir el tema. 2. Buscar artículos. 3. Revisar y seleccionar resultados. 4. Descargar los XML y conservar el manifiesto.")

st.caption("Nota técnica: SciELO Search y SciELO ArticleMeta son servicios distintos. La búsqueda temática se realiza en Search; ArticleMeta recupera el XML mediante el PID del artículo.")
