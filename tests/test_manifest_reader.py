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


def test_required_unexpanded_is_degraded():
    reader = FakeReader({"a": ("Title", "body [Unexpanded nested content: x]")})
    pages, report = _read_manifest(reader, [{"id": "a"}])
    assert report["status"] == "DEGRADED"
    assert report["unexpanded_required"] is True


def test_required_unexpanded_via_meta():
    reader = FakeReader({"a": ("Title", "body", {"has_unexpanded": True})})
    pages, report = _read_manifest(reader, [{"id": "a"}])
    assert report["status"] == "DEGRADED"


def test_roles_reported_by_role_not_raw_id():
    raw_id = "0123456789abcdef0123456789abcdef"
    reader = FakeReader({raw_id: ("Ok", "body")})
    pages, report = _read_manifest(reader, [{"id": raw_id, "role": "bootstrap_protocol"}])
    assert "bootstrap_protocol" in report["roles"]
    assert raw_id not in report["roles"]
    from luna.context_builder import build_context_bundle
    bundle = build_context_bundle(pages, manifest_report=report)
    assert raw_id not in bundle


def test_required_unsupported_placeholder_is_degraded():
    reader = FakeReader({"a": ("Title", "[Unsupported/nested block: child_page; contents not expanded in v0.3.0]")})
    pages, report = _read_manifest(reader, [{"id": "a"}])
    assert report["status"] == "DEGRADED"
    assert report["unexpanded_required"] is True
