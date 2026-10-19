import sys

import yaml

from luna.config import load_config


def _sanitize_error_text(text: str) -> str:
    lowered = text.lower()
    if any(tok in lowered for tok in ("secret_", "ntn_", "token", "sk-", "bearer ", "authorization")):
        return "<redacted>"
    return text


def diagnose(config_path: str = "config/sources.yaml", token: str | None = None) -> list[str]:
    problems: list[str] = []
    if sys.version_info < (3, 11):
        problems.append("Python 3.11 or newer is required.")
    if not token:
        problems.append("NOTION_TOKEN is not set.")
    try:
        config = load_config(config_path)
        if not config["pages"]:
            problems.append("No Notion pages configured yet.")
    except (OSError, ValueError, yaml.YAMLError) as exc:
        problems.append(f"Configuration error: {_sanitize_error_text(str(exc))}")
    return problems
