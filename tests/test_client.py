from dumparticle.client import compile_equation, tokenize, ArticleMetaClient

def test_boolean_and_or_not_phrase_truncation():
    p=compile_equation('("inteligencia artificial" OR "artificial intelligence") AND educ* NOT medicina')
    assert p('La inteligencia artificial en educación superior')
    assert p('Artificial intelligence for educational practice')
    assert not p('inteligencia artificial en medicina y educación')
    assert not p('inteligencia artificial en salud')

def test_implicit_and_and_accent_normalization():
    p=compile_equation('educ* aprendizagem')
    assert p('Educação e aprendizagem')
    assert not p('Educação a distância')

def test_curly_quotes():
    assert compile_equation('“educação”')('Educação superior')

def test_empty_or_invalid_equation():
    for q in ('', '(educacao AND', 'educacao OR'):
        try: compile_equation(q); assert False
        except ValueError: pass

def test_articlemeta_client_has_no_search_scielo_dependency():
    class S:
        headers={}
    c=ArticleMetaClient(session=S())
    assert c.base_url.startswith('https://articlemeta.scielo.org/api/v1/')
