import sys

from luna.config import load_config


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
    except (OSError, ValueError) as exc:
        problems.append(f"Configuration error: {exc}")
    return problems
