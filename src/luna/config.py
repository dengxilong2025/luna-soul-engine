from pathlib import Path
from typing import Any

import yaml


def load_config(path: str | Path = "config/sources.yaml") -> dict[str, Any]:
    config_path = Path(path)
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")
    with config_path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise ValueError("Config must be a YAML object.")
    pages = data.get("pages", [])
    if not isinstance(pages, list):
        raise ValueError("'pages' must be a list.")
    for index, page in enumerate(pages):
        if not isinstance(page, dict) or not isinstance(page.get("id"), str) or not page["id"].strip():
            raise ValueError(f"pages[{index}] must be an object with a non-empty string 'id'.")
        if "title" in page and not isinstance(page["title"], str):
            raise ValueError(f"pages[{index}].title must be a string.")
    data["pages"] = pages
    return data
