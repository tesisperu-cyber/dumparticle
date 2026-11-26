from dumparticle.client import ArticleMetaClient


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload
        self.text = "<article/>"

    def raise_for_status(self):
        pass

    def json(self):
        return self.payload


class FakeSession:
    def __init__(self):
        self.headers = {}
        self.calls = []

    def get(self, url, params=None, timeout=None):
        self.calls.append((url, params, timeout))
        return FakeResponse({"objects": [
            {"collection": "scl", "code": "S0102-12342024000100001"},
            {"collection": "spa", "code": "S2222-33332024000100001"},
        ]})


def test_iter_identifiers_filters_collection():
    session = FakeSession()
    client = ArticleMetaClient(session=session, page_size=1000)
    rows = client.iter_identifiers(collection="scl", limit=1)
    assert len(rows) == 1
    assert rows[0]["collection"] == "scl"
    assert rows[0]["code"].startswith("S0102")


def test_get_article_xml():
    client = ArticleMetaClient(session=FakeSession())
    assert client.get_article_xml("abc").startswith("<article")
