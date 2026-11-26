"""Interfaz Streamlit para DumpArticle SciELO."""
from pathlib import Path
import sys

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dumparticle.client import ArticleMetaClient
from dumparticle.exporter import dump_articles

st.set_page_config(page_title="DumpArticle SciELO", page_icon="📚", layout="wide")
st.title("DumpArticle · SciELO")
st.caption("Recuperación controlada de XML de artículos mediante SciELO ArticleMeta")

with st.sidebar:
    st.header("Configuración")
    base_url = st.text_input(
        "API ArticleMeta",
        value="https://articlemeta.scielo.org/api/v1/",
        help="Puede cambiarse si SciELO publica una URL alternativa."
    )
    timeout = st.number_input("Timeout (segundos)", min_value=5, max_value=180, value=45)
    st.markdown("---")
    st.caption("Empiece con una muestra pequeña. No ejecute una cosecha masiva sin evaluar el volumen.")

col1, col2, col3 = st.columns(3)
with col1:
    collection = st.text_input("Colección (acrónimo)", value="scl", help="Ej.: scl. Deje vacío para todas.")
with col2:
    issn = st.text_input("ISSN (opcional)", value="")
with col3:
    xml_format = st.selectbox("Formato XML", ["xmlrsps", "xmlwos"], index=0)

limit = st.number_input("Máximo de artículos a descargar", min_value=1, max_value=5000, value=10, step=1)
st.info("La búsqueda de identificadores recorre las páginas de ArticleMeta y aplica los filtros localmente. No es una búsqueda temática.")

if st.button("Consultar identificadores", type="secondary"):
    try:
        client = ArticleMetaClient(base_url=base_url, timeout=int(timeout))
        with st.spinner("Consultando identificadores en ArticleMeta..."):
            records = client.iter_identifiers(
                collection=collection.strip() or None,
                issn=issn.strip() or None,
                limit=int(limit),
            )
            st.session_state["dumparticle_records"] = records
        st.success(f"Identificadores recuperados: {len(records)}")
    except Exception as exc:
        st.error(f"No fue posible consultar ArticleMeta: {exc}")

records = st.session_state.get("dumparticle_records", [])
if records:
    st.subheader("Identificadores recuperados")
    frame = pd.DataFrame(records)
    st.dataframe(frame, use_container_width=True, hide_index=True)
    if st.button("Descargar XML y crear ZIP", type="primary"):
        output_dir = ROOT / "outputs"
        output_dir.mkdir(exist_ok=True)
        output_path = output_dir / "dumparticle_scielo.zip"
        client = ArticleMetaClient(base_url=base_url, timeout=int(timeout))
        progress = st.progress(0.0)
        status = st.empty()
        try:
            report = dump_articles(
                client=client,
                identifiers=records,
                output_path=output_path,
                xml_format=xml_format,
                progress_callback=lambda done, total: (
                    progress.progress(done / total if total else 1.0),
                    status.write(f"Procesados {done} de {total}")
                ),
            )
            st.success(f"Proceso terminado. XML recuperados: {report['downloaded']} · Fallidos: {report['failed']}")
            st.dataframe(pd.DataFrame(report["manifest"]), use_container_width=True, hide_index=True)
            with open(output_path, "rb") as file_obj:
                st.download_button(
                    "Descargar ZIP",
                    data=file_obj,
                    file_name=output_path.name,
                    mime="application/zip",
                )
        except Exception as exc:
            st.error(f"Error durante la descarga: {exc}")
else:
    st.markdown("### Flujo de trabajo")
    st.markdown("1. Consultar identificadores.  2. Revisar la muestra y sus códigos.  3. Descargar XML.  4. Verificar el manifiesto y el contenido de los XML.")
