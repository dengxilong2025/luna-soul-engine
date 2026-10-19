from datetime import datetime, timezone

from luna.context_builder import build_context_bundle


def test_builds_bundle_with_page_content():
    bundle = build_context_bundle(
        [{"title": "Bootstrap", "content": "Start here."}],
        generated_at=datetime(2026, 1, 2, tzinfo=timezone.utc),
    )
    assert "# Luna Session Restoration Bundle" in bundle
    assert "### Bootstrap" in bundle
    assert "Start here." in bundle
    assert "v0.3.0" in bundle


def test_empty_pages_are_explicit():
    bundle = build_context_bundle([], generated_at=datetime(2026, 1, 2, tzinfo=timezone.utc))
    assert "No pages were successfully read" in bundle


def test_bundle_includes_full_manifest_report():
    report = {
        "status": "FAILED",
        "configured": 2,
        "read": 1,
        "required_failures": 1,
        "optional_failures": 0,
        "failures": ["pages[1] 'Required': RuntimeError: missing"],
    }
    bundle = build_context_bundle(
        [{"title": "Kept", "content": "still here"}],
        generated_at=datetime(2026, 1, 2, tzinfo=timezone.utc),
        manifest_report=report,
    )
    assert "- Manifest: FAILED" in bundle
    assert "- Pages configured: 2" in bundle
    assert "- Pages read: 1" in bundle
    assert "- Required failures: 1" in bundle
    assert "- Optional failures: 0" in bundle
    assert "## Manifest issues" in bundle
    assert "pages[1] 'Required': RuntimeError: missing" in bundle
    assert "### Kept" in bundle


def test_bundle_has_required_sections_and_digest():
    report = {"status": "OK", "configured": 1, "read": 1, "required_failures": 0,
              "optional_failures": 0, "failures": [], "roles": {}}
    pages = [{"title": "Bootstrap", "content": "Start here.", "page_id": "page-a"}]
    bundle1 = build_context_bundle(pages, generated_at=datetime(2026, 1, 2, tzinfo=timezone.utc), manifest_report=report)
    bundle2 = build_context_bundle(pages, generated_at=datetime(2026, 1, 2, tzinfo=timezone.utc), manifest_report=report)
    for heading in ["## Startup instructions", "## Required page read status", "## Key page contents",
                    "## Missing items", "## Unexpanded nested content", "## Limits and notes"]:
        assert heading in bundle1
    import re
    m = re.search(r"Integrity-SHA256: ([0-9a-f]{64})", bundle1)
    assert m
    assert "ChatGPT" in bundle1
    d1 = re.search(r"Integrity-SHA256: ([0-9a-f]{64})", bundle1).group(1)
    d2 = re.search(r"Integrity-SHA256: ([0-9a-f]{64})", bundle2).group(1)
    assert d1 == d2


def test_partial_bundle_never_ok_status():
    report = {"status": "FAILED", "configured": 1, "read": 0, "required_failures": 1,
              "optional_failures": 0, "failures": ["x"]}
    bundle = build_context_bundle([], generated_at=datetime(2026, 1, 2, tzinfo=timezone.utc), manifest_report=report)
    assert "- Status: FAILED" in bundle
    assert "- Status: OK" not in bundle


def test_unexpanded_section_not_none_for_placeholder():
    report = {"status": "DEGRADED", "configured": 1, "read": 1, "required_failures": 0,
              "optional_failures": 0, "failures": [], "roles": {}}
    pages = [{"title": "Page", "content": "[Unsupported/nested block: child_page; contents not expanded in v0.3.0]", "page_id": "page-a"}]
    bundle = build_context_bundle(pages, manifest_report=report)
    assert "## Unexpanded nested content" in bundle
    # The unexpanded section should not be just "- None"
    import re
    section = bundle.split("## Unexpanded nested content", 1)[1].split("## Limits", 1)[0]
    assert "- None" not in section


def test_digest_differs_for_different_failures():
    pages = [{"title": "Bootstrap", "content": "Start here.", "page_id": "page-a"}]
    report1 = {"status": "OK", "configured": 1, "read": 1, "required_failures": 0,
               "optional_failures": 0, "failures": [], "roles": {}}
    report2 = {"status": "OK", "configured": 1, "read": 1, "required_failures": 0,
               "optional_failures": 0, "failures": ["boom"], "roles": {}}
    b1 = build_context_bundle(pages, manifest_report=report1)
    b2 = build_context_bundle(pages, manifest_report=report2)
    import re
    d1 = re.search(r"Integrity-SHA256: ([0-9a-f]{64})", b1).group(1)
    d2 = re.search(r"Integrity-SHA256: ([0-9a-f]{64})", b2).group(1)
    assert d1 != d2
