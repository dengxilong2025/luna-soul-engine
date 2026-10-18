from __future__ import annotations

import httpx

NOTION_API_BASE = "https://api.notion.com/v1"
NOTION_API_VERSION = "2022-06-28"


class NotionReader:
    def __init__(self, token: str, timeout: float = 20.0):
        if not token.strip():
            raise ValueError("Notion token is empty.")
        self._headers = {
            "Authorization": f"Bearer {token}",
            "Notion-Version": NOTION_API_VERSION,
            "Content-Type": "application/json",
        }
        self._timeout = timeout

    def get_page_title(self, page: dict) -> str:
        properties = page.get("properties", {})
        for prop in properties.values():
            if isinstance(prop, dict) and prop.get("type") == "title":
                chunks = prop.get("title", [])
                title = "".join(item.get("plain_text", "") for item in chunks)
                if title:
                    return title
        return "Untitled Notion page"

    def fetch_page(self, page_id: str) -> tuple[str, str]:
        with httpx.Client(headers=self._headers, timeout=self._timeout) as client:
            page_response = client.get(f"{NOTION_API_BASE}/pages/{page_id}")
            page_response.raise_for_status()
            page = page_response.json()
            title = self.get_page_title(page)

            lines: list[str] = []
            next_cursor = None
            while True:
                params = {"page_size": 100}
                if next_cursor:
                    params["start_cursor"] = next_cursor
                response = client.get(
                    f"{NOTION_API_BASE}/blocks/{page_id}/children",
                    params=params,
                )
                response.raise_for_status()
                payload = response.json()
                for block in payload.get("results", []):
                    text = self._block_text(block)
                    if text:
                        lines.append(text)
                if not payload.get("has_more"):
                    break
                next_cursor = payload.get("next_cursor")
                if not next_cursor:
                    break
        return title, "\n".join(lines).strip()

    @staticmethod
    def _block_text(block: dict) -> str:
        block_type = block.get("type", "")
        content = block.get(block_type, {})
        rich_text = content.get("rich_text", []) if isinstance(content, dict) else []
        text = "".join(part.get("plain_text", "") for part in rich_text)
        if text:
            if block_type.startswith("heading_"):
                return f"{'#' * int(block_type[-1])} {text}"
            if block_type == "bulleted_list_item":
                return f"- {text}"
            if block_type == "numbered_list_item":
                return f"1. {text}"
            if block_type == "to_do":
                checked = content.get("checked", False)
                return f"- [{'x' if checked else ' '}] {text}"
            return text
        if block_type in {"child_page", "child_database", "table", "column_list", "synced_block"}:
            return f"[Unsupported/nested block: {block_type}; contents not expanded in v0.1]"
        return ""
