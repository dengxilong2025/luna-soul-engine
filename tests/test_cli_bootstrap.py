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


class OkReader:
    def __init__(self, token):
        self.token = token

    def fetch_page(self, page_id):
        return ("Ok", "body")


def test_bootstrap_success_exits_0(monkeypatch, tmp_path, capsys):
    config = tmp_path / "sources.yaml"
    config.write_text('pages:\n  - id: "page-a"\n    expected_title: "Ok"\n', encoding="utf-8")
    monkeypatch.setenv("NOTION_TOKEN", "test-token-not-a-real-secret")
    monkeypatch.setattr("luna.cli.NotionReader", OkReader)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("sys.argv", ["luna", "bootstrap", "--config", str(config)])

    from luna.cli import main

    main()
    out = capsys.readouterr().out
    assert "Manifest status: OK" in out


class DegradedReader:
    def __init__(self, token):
        self.token = token
        self.calls = 0

    def fetch_page(self, page_id):
        if page_id == "page-b":
            raise RuntimeError("missing")
        return ("Ok", "body")


def test_bootstrap_degraded_optional_exits_0(monkeypatch, tmp_path, capsys):
    config = tmp_path / "sources.yaml"
    config.write_text(
        'pages:\n  - id: "page-a"\n    expected_title: "Ok"\n  - id: "page-b"\n    required: false\n',
        encoding="utf-8",
    )
    monkeypatch.setenv("NOTION_TOKEN", "test-token-not-a-real-secret")
    monkeypatch.setattr("luna.cli.NotionReader", DegradedReader)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("sys.argv", ["luna", "bootstrap", "--config", str(config)])

    from luna.cli import main

    main()
    out = capsys.readouterr().out
    assert "Manifest status: DEGRADED" in out


def test_bootstrap_does_not_print_fake_token(monkeypatch, tmp_path, capsys):
    FAKE = "secret_TEST_FAKE_TOKEN_XYZ"
    config = tmp_path / "sources.yaml"
    config.write_text('pages:\n  - id: "page-a"\n', encoding="utf-8")

    class TokenReader:
        def __init__(self, token):
            self.token = token

        def fetch_page(self, page_id):
            raise RuntimeError(f"failed {FAKE}")

    monkeypatch.setenv("NOTION_TOKEN", "test-token-not-a-real-secret")
    monkeypatch.setattr("luna.cli.NotionReader", TokenReader)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("sys.argv", ["luna", "bootstrap", "--config", str(config)])

    from luna.cli import main

    with pytest.raises(SystemExit):
        main()
    captured = capsys.readouterr()
    combined = captured.out + captured.err
    assert FAKE not in combined
