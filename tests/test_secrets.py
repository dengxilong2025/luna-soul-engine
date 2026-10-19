import os

from luna.cli import _read_manifest
from luna.context_builder import build_context_bundle
from luna.notion_reader import classify_notion_error, NotionReader


FAKE_TOKEN = "secret_TEST_FAKE_TOKEN_XYZ"
FAKE_TOKEN2 = "ntn_FAKE"


def test_secret_absent_from_bundle():
    pages = [{"title": "Bootstrap", "content": "hello", "page_id": "page-a"}]
    report = {"status": "OK", "configured": 1, "read": 1, "required_failures": 0,
              "optional_failures": 0, "failures": []}
    bundle = build_context_bundle(pages, manifest_report=report)
    assert FAKE_TOKEN not in bundle
    assert FAKE_TOKEN2 not in bundle


def test_secret_absent_from_classify_output():
    exc = Exception(f"boom {FAKE_TOKEN} {FAKE_TOKEN2}")
    result = classify_notion_error(exc)
    assert FAKE_TOKEN not in result
    assert FAKE_TOKEN2 not in result


def test_secret_absent_from_markers():
    marker = NotionReader._unexpanded_children_marker(
        {"type": "toggle", "id": FAKE_TOKEN, "has_children": True}
    )
    assert FAKE_TOKEN not in marker
    assert "<redacted>" in marker


def test_secret_absent_from_manifest_failures():
    class FakeReader:
        def fetch_page(self, page_id):
            raise RuntimeError(f"failed {FAKE_TOKEN} {FAKE_TOKEN2}")

    pages, report = _read_manifest(FakeReader(), [{"id": "a"}])
    joined = "\n".join(report["failures"])
    assert FAKE_TOKEN not in joined
    assert FAKE_TOKEN2 not in joined
    assert classify_notion_error(RuntimeError(FAKE_TOKEN)) == "other"
    assert FAKE_TOKEN not in classify_notion_error(RuntimeError(FAKE_TOKEN))


def test_secret_absent_from_bundle_after_failed_read():
    class FakeReader:
        def fetch_page(self, page_id):
            raise RuntimeError(f"failed {FAKE_TOKEN} {FAKE_TOKEN2}")

    pages, report = _read_manifest(FakeReader(), [{"id": "a"}])
    bundle = build_context_bundle(pages, manifest_report=report)
    assert FAKE_TOKEN not in bundle
    assert FAKE_TOKEN2 not in bundle


def test_secret_absent_from_bundle_when_page_id_is_token():
    pages = [{"title": "Bootstrap", "content": "hello", "page_id": FAKE_TOKEN}]
    report = {"status": "OK", "configured": 1, "read": 1, "required_failures": 0,
              "optional_failures": 0, "failures": []}
    bundle = build_context_bundle(pages, manifest_report=report)
    assert FAKE_TOKEN not in bundle
