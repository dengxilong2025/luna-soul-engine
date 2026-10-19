from datetime import datetime, timezone

from luna.context_builder import build_context_bundle


def test_builds_bundle_with_page_content():
    bundle = build_context_bundle(
        [{"title": "Bootstrap", "content": "Start here."}],
        generated_at=datetime(2026, 1, 2, tzinfo=timezone.utc),
    )
    assert "# Luna Session Restoration Bundle" in bundle
    assert "## Bootstrap" in bundle
    assert "Start here." in bundle
    assert "v0.2.0" in bundle


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
    assert "## Kept" in bundle
