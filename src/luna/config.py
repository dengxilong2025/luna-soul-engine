from pathlib import Path
from typing import Any

import yaml


def load_config(path: str | Path = "config/sources.yaml") -> dict[str, Any]:
    """Load and validate the backwards-compatible source manifest.

    Page entries support:
      id: Notion page ID (required)
      title: display-title fallback (optional)
      required: whether a read/title check failure aborts bootstrap (default true)
      expected_title: exact title expected from Notion (optional)
      role: optional role label (non-empty string)
    """
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
    seen_ids: set[str] = set()
    seen_roles: set[str] = set()
    for index, page in enumerate(pages):
        if not isinstance(page, dict) or not isinstance(page.get("id"), str) or not page["id"].strip():
            raise ValueError(f"pages[{index}] must be an object with a non-empty string 'id'.")
        page_id = page["id"].strip()
        if page_id in seen_ids:
            raise ValueError(f"pages[{index}] duplicates a page ID already listed.")
        seen_ids.add(page_id)
        if "title" in page and not isinstance(page["title"], str):
            raise ValueError(f"pages[{index}].title must be a string.")
        if "expected_title" in page and not isinstance(page["expected_title"], str):
            raise ValueError(f"pages[{index}].expected_title must be a string.")
        if "required" in page and not isinstance(page["required"], bool):
            raise ValueError(f"pages[{index}].required must be true or false.")
        if "role" in page:
            if not isinstance(page["role"], str) or not page["role"].strip():
                raise ValueError(f"pages[{index}].role must be a non-empty string.")
            page["role"] = page["role"].strip()
            if page["role"] in seen_roles:
                raise ValueError(f"duplicate role '{page['role']}' at pages[{index}]")
            seen_roles.add(page["role"])
        page["id"] = page_id
        page.setdefault("required", True)
    data["pages"] = pages
    return data
