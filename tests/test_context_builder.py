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


def test_empty_pages_are_explicit():
    bundle = build_context_bundle([], generated_at=datetime(2026, 1, 2, tzinfo=timezone.utc))
    assert "No pages configured" in bundle
