from __future__ import annotations

import httpx

NOTION_API_BASE = "https://api.notion.com/v1"
NOTION_API_VERSION = "2022-06-28"

MAX_BLOCK_PAGES = 50


class NotionPaginationError(RuntimeError):
    """Raised when Notion signals more results but gives no cursor to continue."""


def classify_notion_error(exc: Exception) -> str:
    """Map an exception to a stable, secret-free error category."""
    if isinstance(exc, NotionPaginationError):
        message = str(exc).lower()
        if "without next_cursor" in message:
            return "pagination_error"
        if "incomplete" in message or "results" in message:
            return "incomplete_response"
        return "pagination_error"

    if isinstance(exc, (httpx.ConnectError, httpx.TimeoutException, httpx.NetworkError)):
        return "network_error"

    response = getattr(exc, "response", None)
    status_code = getattr(response, "status_code", None)
    notion_code = None
    if response is not None:
        try:
            payload = response.json()
            if isinstance(payload, dict):
                notion_code = payload.get("code")
        except Exception:
            notion_code = None

    if status_code == 429 or notion_code == "rate_limited":
        return "rate_limit"
    if status_code == 401:
        return "auth_failure"
    if status_code == 403:
        return "permission_denied"
    if status_code == 404 or notion_code == "object_not_found":
        return "not_found"

    message = str(exc).lower()
    if "title mismatch" in message:
        return "title_mismatch"
    if "incomplete" in message:
        return "incomplete_response"

    if isinstance(exc, httpx.HTTPError):
        return "other"
    return "other"


class NotionReader:
    MAX_BLOCK_PAGES = MAX_BLOCK_PAGES
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

    def fetch_page(self, page_id: str) -> tuple[str, str, dict]:
        with httpx.Client(headers=self._headers, timeout=self._timeout) as client:
            page_response = client.get(f"{NOTION_API_BASE}/pages/{page_id}")
            page_response.raise_for_status()
            page = page_response.json()
            title = self.get_page_title(page)

            lines: list[str] = []
            next_cursor = None
            previous_block_type = None
            numbered_list_index = 0
            warned_nested_ids: set[str] = set()
            seen_unexpanded: set[str] = set()
            unexpanded: list[dict[str, str]] = []
            block_count = 0
            page_fetch_count = 0
            seen_cursors: set[str] = set()
            module_cap = globals().get("MAX_BLOCK_PAGES", 50)
            if module_cap != 50:
                max_pages = module_cap
            elif "MAX_BLOCK_PAGES" in self.__class__.__dict__:
                max_pages = self.__class__.MAX_BLOCK_PAGES
            else:
                max_pages = module_cap
            while True:
                if page_fetch_count >= max_pages:
                    raise NotionPaginationError(
                        f"Exceeded MAX_BLOCK_PAGES ({max_pages}) block page fetches."
                    )
                params = {"page_size": 100}
                if next_cursor:
                    params["start_cursor"] = next_cursor
                response = client.get(
                    f"{NOTION_API_BASE}/blocks/{page_id}/children",
                    params=params,
                )
                response.raise_for_status()
                payload = response.json()
                if not isinstance(payload, dict) or not isinstance(payload.get("results"), list):
                    raise NotionPaginationError(
                        "Notion response missing or invalid 'results' list (incomplete response)."
                    )
                page_fetch_count += 1
                for block in payload["results"]:
                    block_count += 1
                    block_type = block.get("type", "")
                    if block_type == "numbered_list_item":
                        numbered_list_index = numbered_list_index + 1 if previous_block_type == block_type else 1
                    else:
                        numbered_list_index = 0
                    text = self._block_text(block, numbered_list_index or 1)
                    if text:
                        lines.append(text)
                    unsupported_placeholder = bool(text and text.startswith("[Unsupported/nested block:"))
                    has_nested = bool(block.get("has_children")) or unsupported_placeholder
                    if has_nested:
                        warning_key = str(block.get("id") or f"{block_type}:{block_count}")
                        if warning_key not in warned_nested_ids:
                            warned_nested_ids.add(warning_key)
                            masked_id = self._mask_block_id(str(block.get("id") or ""))
                            dedup_key = masked_id if block.get("id") else f"synthetic:{warning_key}"
                            if dedup_key not in seen_unexpanded:
                                seen_unexpanded.add(dedup_key)
                                unexpanded.append({"type": block_type, "masked_id": masked_id})
                            already_flagged = bool(
                                text
                                and (
                                    "contents not expanded" in text
                                    or "Unexpanded nested content" in text
                                    or "children not read" in text
                                )
                            ) or unsupported_placeholder
                            if block.get("has_children") and not already_flagged:
                                lines.append(self._unexpanded_children_marker(block))
                    previous_block_type = block_type
                if not payload.get("has_more"):
                    break
                new_cursor = payload.get("next_cursor")
                if not new_cursor:
                    raise NotionPaginationError(
                        "Notion returned has_more=true without next_cursor; refusing to return incomplete page content."
                    )
                if new_cursor in seen_cursors:
                    raise NotionPaginationError(
                        "Repeated next_cursor detected; pagination loop."
                    )
                seen_cursors.add(new_cursor)
                next_cursor = new_cursor
        meta = {
            "unexpanded": unexpanded,
            "block_count": block_count,
            "page_fetch_count": page_fetch_count,
            "has_unexpanded": bool(unexpanded),
        }
        return title, "\n".join(lines).strip(), meta

    @staticmethod
    def _mask_block_id(block_id: str) -> str:
        """Mask token-like values; abbreviate long Notion-style ids in markers."""
        value = (block_id or "").strip()
        if not value:
            return "unknown"
        lowered = value.lower()
        if (
            lowered.startswith(("secret_", "ntn_", "bearer "))
            or "token" in lowered
            or lowered.startswith("sk-")
        ):
            return "<redacted>"
        compact = value.replace("-", "")
        if len(compact) >= 16 and all(ch in "0123456789abcdefABCDEF" for ch in compact):
            return f"{value[:8]}…{value[-4:]}"
        if len(value) > 16:
            return f"{value[:6]}…{value[-4:]}"
        return value

    @classmethod
    def _unexpanded_children_marker(cls, block: dict) -> str:
        block_type = block.get("type") or "unknown"
        masked_id = cls._mask_block_id(str(block.get("id") or ""))
        return (
            f"[Unexpanded nested content: type={block_type}; id={masked_id}; "
            "children not read in v0.3.0]"
        )

    @staticmethod
    def _block_text(block: dict, numbered_list_index: int = 1) -> str:
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
                return f"{numbered_list_index}. {text}"
            if block_type == "to_do":
                checked = content.get("checked", False)
                return f"- [{'x' if checked else ' '}] {text}"
            return text
        if block_type in {"child_page", "child_database", "table", "column_list", "synced_block"}:
            return f"[Unsupported/nested block: {block_type}; contents not expanded in v0.3.0]"
        return ""
