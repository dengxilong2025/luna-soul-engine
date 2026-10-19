import httpx
import pytest

from luna.config import load_config
from luna.context_builder import build_context_bundle
from luna.notion_reader import classify_notion_error


def test_pure_unit_paths_do_not_touch_network(monkeypatch, tmp_path):
    def boom(*args, **kwargs):
        raise RuntimeError("network touched")

    monkeypatch.setattr(httpx, "Client", boom)

    config_path = tmp_path / "sources.yaml"
    config_path.write_text("pages: []\n", encoding="utf-8")
    load_config(config_path)
    build_context_bundle([], manifest_report={"status": "OK", "configured": 0, "read": 0, "failures": []})
    assert classify_notion_error(ValueError("boom")) == "other"


def test_cli_fake_reader_path_never_constructs_httpx(monkeypatch, tmp_path, capsys):
    def boom(*args, **kwargs):
        raise RuntimeError("httpx.Client constructed")

    monkeypatch.setattr("luna.notion_reader.httpx.Client", boom)

    class OkReader:
        def __init__(self, token):
            self.token = token

        def fetch_page(self, page_id):
            return ("Ok", "body")

    config = tmp_path / "sources.yaml"
    config.write_text('pages:\n  - id: "page-a"\n    expected_title: "Ok"\n', encoding="utf-8")
    monkeypatch.setenv("NOTION_TOKEN", "test-token-not-a-real-secret")
    monkeypatch.setattr("luna.cli.NotionReader", OkReader)
    monkeypatch.chdir(tmp_path)
    import sys
    monkeypatch.setattr(sys, "argv", ["luna", "bootstrap", "--config", str(config)])

    from luna.cli import main

    main()
    out = capsys.readouterr().out
    assert "Manifest status: OK" in out
