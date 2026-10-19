import pytest

from luna.config import load_config


def test_manifest_defaults_required_to_true(tmp_path):
    path = tmp_path / "sources.yaml"
    path.write_text('pages:\n  - id: "abc"\n    expected_title: "Bootstrap"\n', encoding="utf-8")
    config = load_config(path)
    assert config["pages"][0]["required"] is True


def test_manifest_accepts_optional_page(tmp_path):
    path = tmp_path / "sources.yaml"
    path.write_text('pages:\n  - id: "abc"\n    required: false\n', encoding="utf-8")
    assert load_config(path)["pages"][0]["required"] is False


def test_manifest_rejects_duplicate_ids(tmp_path):
    path = tmp_path / "sources.yaml"
    path.write_text('pages:\n  - id: "abc"\n  - id: "abc"\n', encoding="utf-8")
    with pytest.raises(ValueError, match="duplicates"):
        load_config(path)


def test_manifest_rejects_non_boolean_required(tmp_path):
    path = tmp_path / "sources.yaml"
    path.write_text('pages:\n  - id: "abc"\n    required: "yes"\n', encoding="utf-8")
    with pytest.raises(ValueError, match="required"):
        load_config(path)


def test_manifest_accepts_valid_role(tmp_path):
    path = tmp_path / "sources.yaml"
    path.write_text('pages:\n  - id: "abc"\n    role: bootstrap_protocol\n', encoding="utf-8")
    config = load_config(path)
    assert config["pages"][0]["role"] == "bootstrap_protocol"


def test_manifest_rejects_empty_role_string(tmp_path):
    path = tmp_path / "sources.yaml"
    path.write_text('pages:\n  - id: "abc"\n    role: "   "\n', encoding="utf-8")
    with pytest.raises(ValueError, match="role"):
        load_config(path)
