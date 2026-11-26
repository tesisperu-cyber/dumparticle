from dumparticle.client import ArticleMetaClient, _extract_documents, _normalize_search_doc


class FakeResponse:
    def __init__(self, payload=None, text="<article/>"):
        self.payload, self.text = payload, text
        self.headers = {}
    def raise_for_status(self): pass
    def json(self): return self.payload


class FakeSession:
    def __init__(self, payload):
        self.headers, self.calls, self.payload = {}, [], payload
    def get(self, url, params=None, timeout=None):
        self.calls.append((url, params, timeout))
        return FakeResponse(self.payload)


def test_search_articles_normalizes_results():
    payload = {"response": {"docs": [{
        "pid": "S0102-12342024000100001",
        "title": {"pt": "IA na educação"},
        "authors": ["Ana Silva"],
        "journal_title": "Revista Exemplo",
        "publication_year": "2024",
        "doi": "10.1234/exemplo",
        "issn": "0102-1234",
        "collection": "scl",
        "la": "pt"
    }]}}
    session = FakeSession(payload)
    client = ArticleMetaClient(session=session)
    rows = client.search_articles("inteligência artificial", collection="scl", limit=10)
    assert len(rows) == 1
    assert rows[0]["code"] == "S0102-12342024000100001"
    assert rows[0]["title"] == "IA na educação"
    assert rows[0]["year"] == "2024"
    assert session.calls[0][1]["q"] == "inteligência artificial"


def test_search_articles_rejects_empty_query():
    client = ArticleMetaClient(session=FakeSession({"docs": []}))
    try:
        client.search_articles(" ")
        assert False, "Expected ValueError"
    except ValueError:
        pass


def test_search_articles_fails_closed_on_unknown_json_shape():
    client = ArticleMetaClient(session=FakeSession({"unexpected": []}))
    try:
        client.search_articles("clima")
        assert False, "Expected ArticleMetaError"
    except Exception as exc:
        assert "no contiene una lista reconocible" in str(exc)


def test_get_article_xml():
    client = ArticleMetaClient(session=FakeSession({}))
    assert client.get_article_xml("abc").startswith("<article")
