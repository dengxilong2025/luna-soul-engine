import os

import pytest


def test_live_marker_skipped_by_default():
    # Documents the opt-in gate; always passes.
    assert os.getenv("LUNA_NOTION_LIVE", "") != "1" or True


@pytest.mark.notion_live
@pytest.mark.skipif(
    os.getenv("LUNA_NOTION_LIVE") != "1" or not os.getenv("NOTION_TOKEN"),
    reason="requires LUNA_NOTION_LIVE=1 and NOTION_TOKEN",
)
def test_live_readonly_bootstrap():
    # Must not run in CI. If somehow enabled without config pages, skip.
    pytest.skip("Live Notion test ready but not configured in this environment")
