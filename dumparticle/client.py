"""Recuperador temático local basado en la cosecha de metadatos SciELO ArticleMeta.
La ecuación booleana se evalúa localmente sobre título, resumen y palabras clave.
"""
from __future__ import annotations
import os, re, time, unicodedata, html
from urllib.parse import urljoin
import requests

class ArticleMetaError(RuntimeError): pass

COLLECTIONS = {
    "scl":"Brasil", "per":"Perú", "col":"Colombia", "chl":"Chile", "mex":"México",
    "arg":"Argentina", "cub":"Cuba", "ven":"Venezuela", "ury":"Uruguay",
    "cri":"Costa Rica", "bol":"Bolivia", "spa":"España", "prt":"Portugal", "sza":"Sudáfrica"
}
DOMAINS = {"scl":"www.scielo.br", "col":"www.scielo.org.co", "spa":"scielo.isciii.es", "chl":"www.scielo.cl",
"per":"www.scielo.org.pe", "mex":"www.scielo.org.mx", "arg":"www.scielo.org.ar", "cub":"scielo.sld.cu",
"ven":"www.scielo.org.ve", "ury":"www.scielo.edu.uy", "cri":"www.scielo.sa.cr", "bol":"www.scielo.org.bo",
"prt":"www.scielo.mec.pt", "sza":"www.scielo.org.za"}

_TOK = re.compile(r'"([^"]+)"|(\()|(\))|([^\s()"]+)')
_QUOTES = {ord(ch): '"' for ch in "\u201c\u201d\u201e\u201f\u00ab\u00bb\u2033\u301d\u301e\uff02"}
def strip_accents(s):
    return ''.join(c for c in unicodedata.normalize('NFD', str(s or '').lower()) if unicodedata.category(c) != 'Mn')
def tokenize(eq):
    out=[]
    for m in _TOK.finditer((eq or '').translate(_QUOTES)):
        if m.group(1) is not None: out.append(('T',m.group(1)))
        elif m.group(2): out.append(('(',))
        elif m.group(3): out.append((')',))
        else:
            w=m.group(4); out.append(('OP',w.upper()) if w.upper() in ('AND','OR','NOT') else ('T',w))
    return out
def compile_equation(eq):
    toks=tokenize(eq)
    if not toks: raise ValueError('Escribe una ecuación de búsqueda.')
    pos=[0]
    def peek(): return toks[pos[0]] if pos[0]<len(toks) else None
    def take(): t=toks[pos[0]]; pos[0]+=1; return t
    def factor():
        t=peek()
        if t is None: raise ValueError('Ecuación incompleta.')
        if t==('OP','NOT'): take(); return ('NOT',factor())
        if t[0]=='(': 
            take(); n=expr()
            if peek()!=(')',): raise ValueError('Paréntesis sin cerrar.')
            take(); return n
        if t[0]=='T':
            take(); term=strip_accents(t[1]); trunc=term.endswith('*'); term=term.rstrip('*')
            if not term: raise ValueError('El comodín * debe acompañar una palabra.')
            pat=r'(?<!\w)'+r'\s+'.join(re.escape(x) for x in term.split())+(r'' if trunc else r'(?!\w)')
            return ('TERM',re.compile(pat))
        raise ValueError(f'Token inesperado: {t}')
    def term():
        nodes=[factor()]
        while peek() and (peek()==('OP','AND') or peek()[0] in ('T','(') or peek()==('OP','NOT')):
            if peek()==('OP','AND'): take()
            nodes.append(factor())
        return nodes[0] if len(nodes)==1 else ('AND',nodes)
    def expr():
        nodes=[term()]
        while peek()==('OP','OR'): take(); nodes.append(term())
        return nodes[0] if len(nodes)==1 else ('OR',nodes)
    tree=expr()
    if pos[0]!=len(toks): raise ValueError(f'Elementos sobrantes en la ecuación: {toks[pos[0]]}')
    def ev(n,txt):
        if n[0]=='TERM': return bool(n[1].search(txt))
        if n[0]=='NOT': return not ev(n[1],txt)
        if n[0]=='AND': return all(ev(x,txt) for x in n[1])
        return any(ev(x,txt) for x in n[1])
    return lambda text: ev(tree,strip_accents(text))

def _first(items,key='_'):
    for x in items or []:
        if isinstance(x,dict) and x.get(key): return x[key]
    return None
def _list(obj,key):
    v=(obj or {}).get(key) or []
    return v if isinstance(v,list) else [v]
def _doi(v):
    m=re.search(r'10\.\d{4,9}/[^\s"<>]+',str(v or ''),re.I)
    return m.group(0).rstrip('.,;)\'"').lower() if m else ''
def _norm_issn(v): return re.sub(r'[^0-9Xx]','',str(v or '')).upper()
def _year_from_pid(code):
    # PID SciELO clásico suele codificar el año inmediatamente después del ISSN.
    m=re.search(r'S\d{4}-?\d{3}[\dXx](19\d{2}|20\d{2})',str(code or ''),re.I)
    return int(m.group(1)) if m else None

class ArticleMetaClient:
    def __init__(self,base_url=None,timeout=45,pause_seconds=.25,session=None):
        self.base_url=(base_url or os.getenv('SCIELO_ARTICLEMETA_URL','https://articlemeta.scielo.org/api/v1/')).rstrip('/')+'/'
        self.timeout=int(timeout); self.pause=max(0,float(pause_seconds)); self.session=session or requests.Session()
        self.session.headers.update({'User-Agent':'DumpArticle-SciELO/0.3.0 (thematic metadata harvesting)'})
    def _get(self,url,params=None,timeout=None):
        try: r=self.session.get(url,params=params,timeout=timeout or self.timeout)
        except requests.RequestException as e: raise ArticleMetaError(f'Error de conexión con SciELO: {e}') from e
        time.sleep(self.pause)
        if r.status_code==403: raise ArticleMetaError(f'SciELO rechazó la solicitud (HTTP 403): {r.url}. No se harán reintentos ciegos.')
        if r.status_code==429: raise ArticleMetaError('SciELO aplicó límite de solicitudes (HTTP 429). Reduce el ritmo y vuelve a intentar más tarde.')
        try: r.raise_for_status()
        except requests.RequestException as e: raise ArticleMetaError(f'Fallo HTTP consultando {r.url}: {e}') from e
        return r
    def _json(self,url,params=None):
        try:return self._get(url,params).json()
        except ValueError as e: raise ArticleMetaError(f'ArticleMeta no devolvió JSON válido: {url}') from e
    def identifiers_page(self,collection,offset=0,limit=100,issn=None):
        p={'collection':collection,'limit':min(100,int(limit)),'offset':int(offset)}
        if issn: p['issn']=_norm_issn(issn)
        data=self._json(urljoin(self.base_url,'article/identifiers/'),p)
        return data.get('objects') or [], (data.get('meta') or {}).get('total')
    def article(self,item,collection):
        data=self._json(urljoin(self.base_url,'article/'),{'collection':item.get('collection') or collection,'code':item.get('code')})
        a=data.get('article') or {}; title=data.get('title') or {}
        lang=_first(_list(a,'v40'))
        names=[]
        for au in _list(a,'v10'):
            if isinstance(au,dict):
                n=', '.join(x for x in (au.get('s'),au.get('n')) if x)
                if n:names.append(n)
        kws=[]
        for x in _list(a,'v85'):
            if isinstance(x,dict) and x.get('k') and x['k'] not in kws:kws.append(x['k'])
        issn=re.sub(r'[^0-9Xx]','',str(title.get('code') or ''))
        issn=(issn[:4]+'-'+issn[4:]) if len(issn)==8 else ''
        other=[]
        for x in title.get('issns') or []:
            z=re.sub(r'[^0-9Xx]','',str(x))
            if len(z)==8 and z!=re.sub(r'[^0-9Xx]','',str(title.get('code') or '')): other.append(z[:4]+'-'+z[4:])
        doi=(item or {}).get('doi') or ' '.join(str(x.get('_','')) for x in _list(a,'v237') if isinstance(x,dict))
        dom=DOMAINS.get(collection)
        code=data.get('code') or item.get('code')
        return {'code':code,'collection':collection,'country':COLLECTIONS.get(collection,''),'title':_first(_list(a,'v12')) or '',
          'authors':'; '.join(names),'year':str(data.get('publication_year') or _year_from_pid(code) or ''),
          'journal':_first(_list(title,'v100')) or _first(_list(a,'v30')) or '',
          'abstract':_first(_list(a,'v83'),'a') or '', 'keywords':'; '.join(kws),'doi':_doi(doi),
          'issn':issn,'eissn':other[0] if other else '', 'language':lang or '',
          'document_type':data.get('document_type') or '',
          'url':f'https://{dom}/scielo.php?script=sci_arttext&pid={code}' if dom and code else '',
          'search_query':'','metadata_source':'SciELO ArticleMeta'}
    def search_articles(self,equation,collections=None,issn=None,year_from=None,year_to=None,
                        max_results=100,max_scan=3000,max_seconds=600,progress=None):
        predicate=compile_equation(equation)
        collections=collections or list(COLLECTIONS)
        found=[]; scanned_total=0; stats=[]; seen=set()
        for col in collections:
            started=time.monotonic(); offset=0; scanned=0; matched=0; total=None
            while scanned<max_scan and len(found)<max_results and time.monotonic()-started<max_seconds:
                batch,total_now=self.identifiers_page(col,offset,100,issn)
                if total is None: total=total_now
                if not batch: break
                total_batch=len(batch)
                for item in batch:
                    scanned+=1; scanned_total+=1
                    code=item.get('code')
                    if not code: continue
                    py=_year_from_pid(code)
                    # Solo se omite por año si el PID lo codifica inequívocamente.
                    if py and ((year_from and py<year_from) or (year_to and py>year_to)): continue
                    rec=self.article(item,col)
                    try: year=int(rec['year']) if rec['year'] else None
                    except ValueError: year=None
                    if year_from and year is not None and year<year_from: continue
                    if year_to and year is not None and year>year_to: continue
                    if issn and _norm_issn(issn) not in {_norm_issn(rec['issn']),_norm_issn(rec['eissn'])}: continue
                    hay=' '.join(str(rec.get(k) or '') for k in ('title','abstract','keywords'))
                    if predicate(hay):
                        key=rec['doi'] or (re.sub(r'[^a-z0-9]','',rec['title'].lower()),rec['year'],rec['issn'])
                        if key not in seen:
                            seen.add(key); rec['search_query']=equation; found.append(rec); matched+=1
                    if progress: progress({'collection':col,'scanned':scanned,'matched':matched,'total':total,'found':len(found)})
                    if len(found)>=max_results: break
                    if scanned>=max_scan or time.monotonic()-started>=max_seconds: break
                offset+=total_batch
                if (isinstance(total,int) and offset>=total) or total_batch==0: break
            stats.append({'collection':col,'scanned':scanned,'matched':matched,'reported_total':total,
                          'stopped_by':'max_results' if len(found)>=max_results else 'max_scan' if scanned>=max_scan else 'max_seconds' if time.monotonic()-started>=max_seconds else 'end_of_records'})
            if len(found)>=max_results: break
        self.last_stats=stats
        return found
    def get_article_xml(self,code,xml_format='xmlrsps',collection=None):
        if xml_format not in {'xmlrsps','xmlwos'}: raise ValueError('Formato XML no válido.')
        params={'code':code,'format':xml_format}
        if collection: params['collection']=collection
        r=self._get(urljoin(self.base_url,'article'),params,timeout=90)
        if not r.content.strip() or b'<html' in r.content[:1000].lower(): raise ArticleMetaError(f'La respuesta de {code} no es XML válido.')
        return r.text
