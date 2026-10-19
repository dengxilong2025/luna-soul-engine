from luna.cli import _read_manifest


class FakeReader:
    def __init__(self, results):
        self.results = results

    def fetch_page(self, page_id):
        value = self.results[page_id]
        if isinstance(value, Exception):
            raise value
        return value


def test_required_page_failure_marks_manifest_failed():
    reader = FakeReader({"a": RuntimeError("missing")})
    pages, report = _read_manifest(reader, [{"id": "a"}])
    assert pages == []
    assert report["status"] == "FAILED"
    assert report["required_failures"] == 1


def test_optional_page_failure_degrades_but_keeps_other_pages():
    reader = FakeReader({"a": ("Bootstrap", "start"), "b": RuntimeError("missing")})
    pages, report = _read_manifest(reader, [
        {"id": "a", "expected_title": "Bootstrap"},
        {"id": "b", "required": False, "title": "Optional"},
    ])
    assert len(pages) == 1
    assert report["status"] == "DEGRADED"
    assert report["optional_failures"] == 1


def test_title_mismatch_is_reported_as_failure():
    reader = FakeReader({"a": ("Unexpected", "content")})
    pages, report = _read_manifest(reader, [{"id": "a", "expected_title": "Bootstrap"}])
    assert pages == []
    assert report["required_failures"] == 1
    assert "title mismatch" in report["failures"][0]
