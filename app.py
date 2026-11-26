"""Interfaz web (Streamlit) de scielo_pybot.  Ejecutar:  streamlit run app.py"""
from __future__ import annotations
import json
import tempfile
from pathlib import Path

import streamlit as st

from config.settings import Settings
from core.boolean_engine import compile_query, BooleanSyntaxError
from core.jats_parser import parse_jats
from core.validator import validate_xml

st.set_page_config(page_title="PYBOT · Recuperador SciELO", page_icon="📚", layout="wide")
st.title("📚 PYBOT · Recuperador bibliográfico SciELO")
st.caption("Búsqueda booleana, descarga de XML-JATS y extracción de texto completo. "
           "Estado: probado offline; la conexión con ArticleMeta se verifica en la pestaña «Prueba real».")

base = Settings.load("config.json")
cols_all = base.all_collections()

with st.sidebar:
    st.header("Parámetros")
    equation = st.text_area("Ecuación temática", base.equation, height=140,
                            placeholder='Ej.: (educ* OR ensino) AND ("inteligencia artificial" OR "inteligência artificial")')
    collections = st.multiselect("Colecciones", list(cols_all), default=base.collections,
                                 format_func=lambda c: f"{c} · {cols_all[c]}")
    c1, c2 = st.columns(2)
    year_from = c1.number_input("Año inicial", 0, 2100, base.year_from or 0, help="0 = sin límite")
    year_to = c2.number_input("Año final", 0, 2100, base.year_to or 0, help="0 = sin límite")
    max_results = st.number_input("Máximo de resultados", 1, 5000, base.max_results)
    max_per_col = st.number_input("Máx. registros por colección", 1, 100000, base.max_records_per_collection)
    max_secs = st.number_input("Tiempo máx. por colección (s)", 5, 3600, base.max_seconds_per_collection)
    issn = st.text_input("ISSN (opcional)", base.issn or "")
    doc_type = st.text_input("Tipo documental (opcional)", base.doc_type or "")
    download_xml = st.checkbox("Descargar XML-JATS y extraer texto", value=base.download_xml)


def current_settings() -> Settings:
    s = Settings.load("config.json")
    s.equation, s.collections = equation, collections
    s.year_from, s.year_to = (int(year_from) or None), (int(year_to) or None)
    s.max_results, s.max_records_per_collection = int(max_results), int(max_per_col)
    s.max_seconds_per_collection = int(max_secs)
    s.issn, s.doc_type = issn.strip() or None, doc_type.strip() or None
    s.download_xml = download_xml
    return s


tab_probe, tab_search, tab_eq, tab_xml = st.tabs(["🔬 Prueba real", "🔎 Búsqueda", "🧪 Probar ecuación", "📄 Analizar XML"])

with tab_probe:
    st.write("Recupera **un artículo real** y verifica cada paso (colecciones, PID, metadatos, XML, extracción).")
    pc1, pc2 = st.columns(2)
    p_col = pc1.selectbox("Colección", list(cols_all), index=0)
    p_pid = pc2.text_input("PID (vacío = buscar uno con cuerpo de texto)")
    pc3, pc4 = st.columns(2)
    p_scan = pc3.number_input("Artículos a revisar", 1, 200, 25)
    p_from = pc4.text_input("Procesados desde (AAAA-MM-DD)", "2020-01-01")
    if st.button("Ejecutar prueba real"):
        from main import cmd_probe
        import argparse, io, contextlib
        buf = io.StringIO()
        try:
            with contextlib.redirect_stdout(buf):
                code = cmd_probe(argparse.Namespace(collection=p_col, pid=p_pid or None, scan=int(p_scan), from_date=p_from or None), current_settings())
        except Exception as e:  # la prueba nunca debe tumbar la app: se muestra el error real
            import traceback
            code = 1
            buf.write("\nERROR INESPERADO EN LA PRUEBA:\n" + traceback.format_exc())
        (st.success if code == 0 else st.error)("APROBADO" if code == 0 else "NO APROBADO")
        st.code(buf.getvalue())
        rep = Path(current_settings().exports_dir) / "informe_primer_articulo.md"
        if rep.exists():
            st.download_button("Descargar informe", rep.read_text(encoding="utf-8"), "informe_primer_articulo.md")

with tab_search:
    if st.button("Buscar", type="primary"):
        try:
            if not equation.strip():
                raise BooleanSyntaxError("Escriba su ecuación en la barra lateral antes de buscar.")
            compile_query(equation)
        except BooleanSyntaxError as e:
            st.error(f"Error en la ecuación: {e}")
        else:
            from core.pipeline import run_search
            with st.spinner("Consultando SciELO…"):
                matches, diag, repo = run_search(current_settings())
            st.session_state["repo"], st.session_state["diag"] = repo, diag
            st.session_state["keys"] = [(r.collection, r.pid) for r in matches]
            st.subheader(f"{len(matches)} artículo(s) coinciden")
            if matches:
                st.dataframe([{"colección": r.collection, "pid": r.pid, "año": r.year, "título": r.title,
                               "revista": r.journal_title, "doi": r.doi} for r in matches], use_container_width=True)
            st.text(diag.format())
    repo = st.session_state.get("repo")
    if repo:
        st.divider()
        fmt = st.radio("Exportar", ["csv", "xlsx", "json"], horizontal=True)
        if st.button("Generar archivo"):
            path = repo.export(fmt, current_settings().exports_dir, keys=st.session_state.get("keys"))
            st.download_button(f"Descargar {Path(path).name}", Path(path).read_bytes(), Path(path).name)

with tab_eq:
    txt = st.text_area("Texto a evaluar (título + resumen + palabras clave)",
                       "Uso de inteligencia artificial en la educación superior")
    if st.button("Evaluar ecuación"):
        try:
            res = compile_query(equation).matches(txt)
            (st.success if res else st.warning)("COINCIDE" if res else "NO coincide")
        except BooleanSyntaxError as e:
            st.error(f"Error en la ecuación: {e}")

with tab_xml:
    up = st.file_uploader("Suba un XML-JATS", type=["xml"])
    if up:
        content = up.getvalue()
        v = validate_xml(content, 200, "application/xml")
        st.write("Validación:", "✅ válido" if v.ok else f"❌ {v.reasons}")
        if v.ok:
            p = parse_jats(content)
            st.markdown(f"**{p['title']}**  \nDOI: {p['doi']} · Año: {p['year']} · Revista: {p['journal_title']}")
            st.write("Autores:", "; ".join(a["name"] for a in p["authors"]) or "—")
            for ab in p["abstracts"]:
                with st.expander(f"Resumen ({ab['lang']})"):
                    st.write(ab["text"])
            for sec in p["sections"]:
                with st.expander(f"[{sec['category']}] {sec['title']}"):
                    st.write(sec["text"])
            st.write(f"Referencias: {len(p['references'])}")
            st.download_button("Descargar JSON extraído", json.dumps(p, ensure_ascii=False, indent=2), "extraccion.json")
