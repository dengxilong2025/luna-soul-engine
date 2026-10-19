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
    assert report["status"] == "FAILED"
    assert report["required_failures"] == 1
    assert "title mismatch" in report["failures"][0]


def test_empty_manifest_is_failed():
    pages, report = _read_manifest(FakeReader({}), [])
    assert pages == []
    assert report["status"] == "FAILED"
    assert report["configured"] == 0
    assert report["read"] == 0
    assert "no pages configured" in report["failures"][0]


def test_all_optional_failures_with_zero_reads_is_failed():
    reader = FakeReader({"a": RuntimeError("missing"), "b": RuntimeError("missing")})
    pages, report = _read_manifest(reader, [
        {"id": "a", "required": False},
        {"id": "b", "required": False},
    ])
    assert pages == []
    assert report["status"] == "FAILED"
    assert report["optional_failures"] == 2
    assert report["required_failures"] == 0


def test_success_with_optional_failure_is_degraded():
    reader = FakeReader({"a": ("Ok", "body"), "b": RuntimeError("missing")})
    pages, report = _read_manifest(reader, [
        {"id": "a"},
        {"id": "b", "required": False},
    ])
    assert len(pages) == 1
    assert report["status"] == "DEGRADED"


def test_all_success_is_ok():
    reader = FakeReader({"a": ("Ok", "body")})
    pages, report = _read_manifest(reader, [{"id": "a", "expected_title": "Ok"}])
    assert len(pages) == 1
    assert report["status"] == "OK"
    assert report["failures"] == []
