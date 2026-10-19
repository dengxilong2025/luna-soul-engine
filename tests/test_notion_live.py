import os

import pytest

from luna.cli import _read_manifest
from luna.config import load_config
from luna.notion_reader import NotionReader


@pytest.mark.notion_live
@pytest.mark.skipif(
    os.getenv("LUNA_NOTION_LIVE") != "1" or not os.getenv("NOTION_TOKEN"),
    reason="requires LUNA_NOTION_LIVE=1 and NOTION_TOKEN",
)
def test_live_notion_readonly():
    config = load_config("config/sources.yaml")
    entries = config.get("pages", [])
    assert isinstance(entries, list)
    assert len(entries) >= 1

    reader = NotionReader(os.environ["NOTION_TOKEN"])
    page_results = []
    for entry in entries:
        result = reader.fetch_page(entry["id"])
        assert isinstance(result, tuple)
        assert len(result) == 3
        title, content, meta = result
        expected_title = entry.get("expected_title")
        title_match = True
        if expected_title:
            title_match = str(title).strip() == str(expected_title).strip()
            assert title_match
        assert meta.get("page_fetch_count", 0) >= 1
        assert meta.get("block_count", 0) >= 0
        unexpanded_count = len(meta.get("unexpanded") or [])
        masked_id = str(entry["id"])[-4:]
        role = entry.get("role") or ""
        page_status = "DEGRADED" if (meta.get("has_unexpanded") or meta.get("unexpanded")) else "OK"
        print(
            f"id_last4={masked_id} role={role} status={page_status} "
            f"title_match={title_match} block_count={meta.get('block_count', 0)} "
            f"fetch_count={meta.get('page_fetch_count', 0)} unexpanded_count={unexpanded_count}"
        )
        page_results.append((entry, meta))

    pages, report = _read_manifest(reader, entries)
    # Authorized live config must read every configured page; FAILED is a real failure.
    assert report["required_failures"] == 0, report
    assert report["configured"] == report["read"], report
    assert report["status"] in {"OK", "DEGRADED"}, report
    print(
        f"manifest_status={report['status']} configured={report['configured']} "
        f"read={report['read']} unexpanded_required={report.get('unexpanded_required')}"
    )
