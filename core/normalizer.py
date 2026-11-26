"""Normalización lingüística: minúsculas, sin tildes/diacríticos, sin puntuación.
Decisión: ñ->n y ç->c (consistente en consulta y texto). Los plurales/derivaciones se
cubren con truncamiento (educ*), no con stemming, para mantener resultados predecibles."""
import re
import unicodedata

_NON_ALNUM = re.compile(r"[^0-9a-z]+")


def strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))


def normalize_text(s: str | None) -> str:
    if not s:
        return ""
    s = strip_accents(s.casefold())
    return _NON_ALNUM.sub(" ", s).strip()


def tokenize(s: str | None) -> list[str]:
    n = normalize_text(s)
    return n.split() if n else []
