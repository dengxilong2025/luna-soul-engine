import sys
from pathlib import Path

import pytest

from luna.cli import main


class FakeReader:
    def __init__(self, token: str):
        self.token = token

    def fetch_page(self, page_id: str):
        raise RuntimeError(f"simulated missing page {page_id}")


def test_bootstrap_empty_manifest_exits_nonzero(monkeypatch, tmp_path, capsys):
    config = tmp_path / "sources.yaml"
    config.write_text("pages: []\n", encoding="utf-8")
    monkeypatch.setenv("NOTION_TOKEN", "test-token-not-a-real-secret")
    monkeypatch.setattr("luna.cli.NotionReader", FakeReader)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["luna", "bootstrap", "--config", str(config)])

    with pytest.raises(SystemExit) as exc:
        main()

    assert exc.value.code == 1
    out = capsys.readouterr().out
    assert "Manifest status: FAILED" in out
    bundles = list((tmp_path / "output").glob("luna-context-*.md"))
    assert len(bundles) == 1
    content = bundles[0].read_text(encoding="utf-8")
    assert "- Manifest: FAILED" in content
    assert "- Pages configured: 0" in content
    assert "- Pages read: 0" in content
    assert "no pages configured" in content


def test_bootstrap_required_failure_exits_1_and_writes_report(monkeypatch, tmp_path, capsys):
    config = tmp_path / "sources.yaml"
    config.write_text(
        'pages:\n  - id: "page-a"\n    title: "Required Page"\n',
        encoding="utf-8",
    )
    monkeypatch.setenv("NOTION_TOKEN", "test-token-not-a-real-secret")
    monkeypatch.setattr("luna.cli.NotionReader", FakeReader)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["luna", "bootstrap", "--config", str(config)])

    with pytest.raises(SystemExit) as exc:
        main()

    assert exc.value.code == 1
    out = capsys.readouterr().out
    assert "Manifest status: FAILED" in out
    assert "Required failures: 1" in out
    bundles = list((tmp_path / "output").glob("luna-context-*.md"))
    assert len(bundles) == 1
    content = bundles[0].read_text(encoding="utf-8")
    assert "- Manifest: FAILED" in content
    assert "- Pages configured: 1" in content
    assert "- Pages read: 0" in content
    assert "- Required failures: 1" in content
    assert "- Optional failures: 0" in content
    assert "simulated missing page" in content
    assert "## Manifest issues" in content
