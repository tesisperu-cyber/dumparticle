"""DumpArticle SciELO: búsqueda temática por cosecha ArticleMeta + ecuación local."""
from pathlib import Path
import sys
import pandas as pd
import streamlit as st
ROOT=Path(__file__).resolve().parent
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from dumparticle.client import ArticleMetaClient,COLLECTIONS
from dumparticle.exporter import dump_articles
st.set_page_config(page_title='DumpArticle · SciELO',page_icon='📚',layout='wide')
st.title('DumpArticle · SciELO')
st.caption('Búsqueda temática mediante cosecha de metadatos ArticleMeta y evaluación local de ecuaciones booleanas.')
with st.sidebar:
 st.header('Configuración')
 base=st.text_input('API SciELO ArticleMeta',value='https://articlemeta.scielo.org/api/v1/')
 timeout=st.number_input('Timeout (segundos)',5,180,45)
 pause=st.number_input('Pausa entre solicitudes (segundos)',0.0,5.0,.3,.1)
 st.markdown('---')
 st.warning('La búsqueda recorre metadatos de ArticleMeta y filtra localmente. No utiliza search.scielo.org ni el archivo articles.json.zip.')
st.subheader('1. Ecuación temática')
eq=st.text_area('Ecuación booleana',value='("inteligencia artificial" OR "inteligência artificial" OR "artificial intelligence") AND (educ* OR ensino OR enseñanza OR teaching OR learning OR aprendizaje OR aprendizagem)',height=125)
st.caption('Operadores AND, OR, NOT; frases entre comillas; paréntesis; truncamiento con * al final. La búsqueda se aplica a título, resumen y palabras clave.')
all_cols=list(COLLECTIONS)
selected=st.multiselect('Colecciones SciELO',options=all_cols,default=['per','scl','col','chl','mex','arg','cub','ven','ury','cri','bol','spa','prt'],format_func=lambda x:f'{x} · {COLLECTIONS[x]}')
c1,c2,c3,c4=st.columns(4)
with c1: y0=st.number_input('Año inicial',1900,2100,2023)
with c2: y1=st.number_input('Año final',1900,2100,2026)
with c3: max_results=st.number_input('Máximo de coincidencias',1,5000,100)
with c4: max_scan=st.number_input('Máximo escaneo por colección',100,100000,3000,100)
c5,c6=st.columns(2)
with c5: max_seconds=st.number_input('Tiempo máximo por colección (segundos)',30,7200,600,30)
with c6: issn=st.text_input('ISSN (opcional)')
st.caption('La cosecha completa puede ser lenta. El año se filtra por metadatos; el PID se usa solo como preselección cuando contiene un año reconocible.')
if st.button('Buscar artículos',type='primary',disabled=not (eq.strip() and selected)):
 try:
  client=ArticleMetaClient(base_url=base,timeout=timeout,pause_seconds=pause)
  progress=st.progress(0); status=st.empty(); live=st.empty()
  def update(x):
   status.write(f"Colección {x['collection']}: {x['scanned']} registros examinados · {x['matched']} coincidencias · {x['found']} acumuladas")
  with st.spinner('Cosechando metadatos y evaluando la ecuación...'):
   rows=client.search_articles(eq,selected,issn.strip() or None,int(y0),int(y1),int(max_results),int(max_scan),int(max_seconds),update)
  st.session_state['da_rows']=rows; st.session_state['da_stats']=client.last_stats; st.session_state['da_eq']=eq
  if rows: st.success(f'Artículos encontrados: {len(rows)}')
  else: st.warning('No se encontraron coincidencias dentro de los límites de cosecha configurados.')
 except Exception as e: st.error(f'La búsqueda no pudo completarse: {e}')
rows=st.session_state.get('da_rows',[])
if rows:
 st.subheader('2. Resultados bibliográficos')
 df=pd.DataFrame(rows)
 st.dataframe(df[['title','authors','year','journal','doi','issn','collection','language','url']],use_container_width=True,hide_index=True)
 with st.expander('Control de cosecha por colección',expanded=True): st.dataframe(pd.DataFrame(st.session_state.get('da_stats',[])),use_container_width=True,hide_index=True)
 labels={f"{i+1}. {r.get('title') or r['code']} · {r.get('year')} · {r.get('collection')}":r for i,r in enumerate(rows)}
 chosen=st.multiselect('Selecciona los artículos que deseas descargar',list(labels),default=list(labels))
 fmt=st.selectbox('Formato XML',['xmlrsps','xmlwos'])
 if st.button('Descargar XML seleccionados y crear ZIP',type='primary',disabled=not chosen):
  outdir=ROOT/'outputs'; outdir.mkdir(exist_ok=True); path=outdir/'dumparticle_scielo.zip'
  client=ArticleMetaClient(base_url=base,timeout=timeout,pause_seconds=pause)
  p=st.progress(0); msg=st.empty()
  try:
   report=dump_articles(client,[labels[x] for x in chosen],path,fmt,lambda n,t:(p.progress(n/t),msg.write(f'Procesados {n}/{t}')))
   st.success(f"XML descargados: {report['downloaded']} · Fallidos: {report['failed']}")
   st.dataframe(pd.DataFrame(report['manifest']),use_container_width=True,hide_index=True)
   st.download_button('Descargar ZIP',path.read_bytes(),file_name=path.name,mime='application/zip')
  except Exception as e: st.error(f'Error al crear la descarga: {e}')
elif not rows:
 st.markdown('### Flujo de trabajo')
 st.markdown('1. Escribir la ecuación. 2. Elegir colecciones y límites. 3. Revisar los artículos coincidentes. 4. Seleccionar y descargar sus XML.')
st.caption('Los identificadores se recuperan automáticamente y se utilizan internamente para solicitar los XML a ArticleMeta.')
