import pytest
from core.normalizer import normalize_text, tokenize
from core.boolean_engine import compile_query, BooleanSyntaxError

EQ = ('("inteligencia artificial" OR "inteligência artificial" OR "artificial intelligence") AND '
      '(educ* OR ensino OR enseñanza OR teaching OR learning OR aprendizaje OR aprendizagem)')


def m(eq, text):
    return compile_query(eq).matches(text)


def test_normalizacion():
    assert normalize_text("  Inteligência ARTIFICIAL, Educação! ") == "inteligencia artificial educacao"
    assert tokenize("e-learning") == ["e", "learning"]
    assert normalize_text(None) == ""


def test_and_or_not():
    assert m("a AND b", "a y b") and not m("a AND b", "a")
    assert m("a OR b", "solo b") and not m("a OR b", "c")
    assert m("a NOT b", "a c") and not m("a NOT b", "a b")
    assert m("NOT b", "a") and not m("NOT b", "b")


def test_precedencia_y_parentesis():
    assert m("a OR b AND c", "a")            # AND antes que OR
    assert not m("(a OR b) AND c", "a")
    assert m("(a OR b) AND c", "b c")
    assert m("((a))", "a")


def test_frases():
    assert m('"inteligencia artificial"', "La Inteligencia Artificial avanza")
    assert not m('"inteligencia artificial"', "artificial inteligencia")
    assert not m('"inteligencia artificial"', "inteligencia . artificial".replace(".", "x"))


def test_tildes_mayusculas():
    assert m("educacion", "EDUCACIÓN superior")
    assert m('"inteligência artificial"', "inteligencia artificial")


def test_truncamiento():
    assert m("educ*", "la educación") and m("educ*", "educational") and m("educ*", "educar")
    assert not m("educ*", "ensino")
    assert m('"inteligencia artifi*"', "inteligencia artificial")
    assert not m("educ", "educación")  # sin truncamiento es exacto


def test_ecuacion_proyecto():
    assert m(EQ, "Uso de inteligencia artificial en la educación")
    assert m(EQ, "Artificial intelligence and learning")
    assert m(EQ, "Inteligência artificial no ensino superior")
    assert not m(EQ, "Inteligencia artificial en medicina clínica")
    assert not m(EQ, "Educación sin tecnología")


def test_campos_no_cruzan_frase():
    q = compile_query('"inteligencia artificial"')
    assert not q.matches("fin inteligencia", "artificial inicio")


@pytest.mark.parametrize("bad", ["", "a b", "(a AND b", "a AND b)", "a AND", "AND a", '"abc', "a*b", '""', "()"])
def test_errores_sintaxis(bad):
    with pytest.raises(BooleanSyntaxError):
        compile_query(bad)


def test_sin_eval():
    # Una ecuación maliciosa es solo texto: nunca se ejecuta
    q = compile_query('"__import__(os).system(x)"')
    assert not q.matches("hola")
