from dumparticle.exporter import dump_articles
from zipfile import ZipFile


class FakeClient:
    def get_article_xml(self, code, xml_format="xmlrsps"):
        if code == "BAD":
            raise RuntimeError("registro no disponible")
        return f"<article><code>{code}</code></article>"


def test_dump_articles_creates_zip_and_manifest(tmp_path):
    output = tmp_path / "sample.zip"
    records = [
        {"collection": "scl", "issn": "1234-5678", "code": "GOOD"},
        {"collection": "scl", "issn": "1234-5678", "code": "BAD"},
    ]
    report = dump_articles(FakeClient(), records, output)
    assert report["total"] == 2
    assert report["downloaded"] == 1
    assert report["failed"] == 1
    with ZipFile(output) as archive:
        names = archive.namelist()
        assert any(name.endswith("GOOD.xml") for name in names)
        assert "manifest.csv" in names
        assert "README.txt" in names
