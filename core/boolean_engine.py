"""Evaluador booleano propio (sin eval). Gramática:
    or_expr  := and_expr ('OR' and_expr)*
    and_expr := unary (('AND' | 'NOT') unary)*      # 'A NOT B' == 'A AND NOT B'
    unary    := 'NOT' unary | primary
    primary  := '(' or_expr ')' | "frase" | palabra | prefijo*
Operadores en MAYÚSCULAS (evita confundir con palabras). Precedencia: NOT > AND > OR.
Términos adyacentes sin operador son un error explícito (no se asume AND)."""
from __future__ import annotations
import re
from dataclasses import dataclass
from .normalizer import tokenize


class BooleanSyntaxError(ValueError):
    pass


@dataclass(frozen=True)
class Term:
    tokens: tuple
    prefix: bool = False


@dataclass(frozen=True)
class And:
    left: object
    right: object


@dataclass(frozen=True)
class Or:
    left: object
    right: object


@dataclass(frozen=True)
class Not:
    operand: object


_LEX = re.compile(r'(?P<lp>\()|(?P<rp>\))|"(?P<phrase>[^"]*)"|(?P<word>[^\s()"]+)')
_OPS = {"AND", "OR", "NOT"}


def _lex(text: str):
    text = text.replace("\u201c", '"').replace("\u201d", '"').replace("\u00ab", '"').replace("\u00bb", '"')
    pos, n, out = 0, len(text), []
    while pos < n:
        if text[pos].isspace():
            pos += 1
            continue
        m = _LEX.match(text, pos)
        if not m:
            raise BooleanSyntaxError(f"Carácter o comilla sin cerrar en la posición {pos}: {text[pos:pos+15]!r}")
        pos = m.end()
        if m.group("lp"):
            out.append(("LP", "("))
        elif m.group("rp"):
            out.append(("RP", ")"))
        elif m.group("phrase") is not None:
            raw = m.group("phrase")
            toks = tuple(tokenize(raw))
            if not toks:
                raise BooleanSyntaxError("Frase vacía entre comillas")
            out.append(("TERM", Term(toks, raw.rstrip().endswith("*"))))
        else:
            w = m.group("word")
            if w in _OPS:
                out.append((w, w))
            else:
                core = w[:-1] if w.endswith("*") else w
                if "*" in core:
                    raise BooleanSyntaxError(f"Truncamiento solo permitido al final: {w!r}")
                toks = tuple(tokenize(core))
                if not toks:
                    raise BooleanSyntaxError(f"Término vacío tras normalizar: {w!r}")
                out.append(("TERM", Term(toks, w.endswith("*"))))
    return out


class _Parser:
    def __init__(self, toks):
        self.t, self.i = toks, 0

    def peek(self):
        return self.t[self.i][0] if self.i < len(self.t) else None

    def take(self):
        tok = self.t[self.i]
        self.i += 1
        return tok

    def parse(self):
        if not self.t:
            raise BooleanSyntaxError("Ecuación vacía")
        node = self.or_expr()
        if self.i < len(self.t):
            kind = self.peek()
            if kind == "RP":
                raise BooleanSyntaxError("Paréntesis de cierre sin apertura")
            raise BooleanSyntaxError("Falta un operador (AND/OR/NOT) entre términos")
        return node

    def or_expr(self):
        node = self.and_expr()
        while self.peek() == "OR":
            self.take()
            node = Or(node, self.and_expr())
        return node

    def and_expr(self):
        node = self.unary()
        while self.peek() in ("AND", "NOT"):
            op = self.take()[0]
            right = self.unary()
            node = And(node, right if op == "AND" else Not(right))
        return node

    def unary(self):
        if self.peek() == "NOT":
            self.take()
            return Not(self.unary())
        return self.primary()

    def primary(self):
        k = self.peek()
        if k == "LP":
            self.take()
            node = self.or_expr()
            if self.peek() != "RP":
                raise BooleanSyntaxError("Paréntesis sin cerrar")
            self.take()
            return node
        if k == "TERM":
            return self.take()[1]
        raise BooleanSyntaxError("Se esperaba un término o '(' " + (f"y se encontró {k}" if k else "al final de la ecuación"))


def _term_match(term: Term, toks: list, tokset: set) -> bool:
    ts = term.tokens
    if len(ts) == 1:
        if term.prefix:
            return any(t.startswith(ts[0]) for t in tokset)
        return ts[0] in tokset
    n = len(ts)
    for i in range(len(toks) - n + 1):
        ok = all(toks[i + j] == ts[j] for j in range(n - 1))
        if not ok:
            continue
        last = toks[i + n - 1]
        if (last.startswith(ts[-1]) if term.prefix else last == ts[-1]):
            return True
    return False


def _eval(node, toks, tokset) -> bool:
    if isinstance(node, Term):
        return _term_match(node, toks, tokset)
    if isinstance(node, And):
        return _eval(node.left, toks, tokset) and _eval(node.right, toks, tokset)
    if isinstance(node, Or):
        return _eval(node.left, toks, tokset) or _eval(node.right, toks, tokset)
    if isinstance(node, Not):
        return not _eval(node.operand, toks, tokset)
    raise TypeError(node)


class Query:
    def __init__(self, equation: str):
        self.equation = equation
        self.ast = _Parser(_lex(equation)).parse()

    def matches(self, *texts: str | None) -> bool:
        """Evalúa sobre la unión de los textos (título + resumen + palabras clave)."""
        toks = tokenize(" qqfieldsepqq ".join(t for t in texts if t))
        return _eval(self.ast, toks, set(toks))


def compile_query(equation: str) -> Query:
    return Query(equation)
