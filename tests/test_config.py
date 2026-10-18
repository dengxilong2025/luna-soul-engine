import pytest

from luna.config import load_config


def test_loads_empty_page_list(tmp_path):
    path = tmp_path / "sources.yaml"
    path.write_text("pages: []\n", encoding="utf-8")
    assert load_config(path)["pages"] == []


def test_rejects_invalid_page_entry(tmp_path):
    path = tmp_path / "sources.yaml"
    path.write_text("pages:\n  - title: Missing ID\n", encoding="utf-8")
    with pytest.raises(ValueError):
        load_config(path)
