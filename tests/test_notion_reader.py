import httpx
import pytest

from luna.notion_reader import NotionPaginationError, NotionReader


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code
        self.request = httpx.Request("GET", "https://api.notion.com/v1/test")

    def raise_for_status(self):
        if self.status_code >= 400:
            response = httpx.Response(self.status_code, request=self.request)
            raise httpx.HTTPStatusError("HTTP error", request=self.request, response=response)

    def json(self):
        return self._payload


class FakeClient:
    def __init__(self, responses, **kwargs):
        self.responses = list(responses)
        self.calls = []

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def get(self, url, params=None):
        self.calls.append((url, params or {}))
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def page_response(title="Bootstrap"):
    return FakeResponse({"properties": {"title": {"type": "title", "title": [{"plain_text": title}]}}})


def block(text, kind="paragraph", *, has_children=False, block_id=None):
    payload = {"type": kind, kind: {"rich_text": [{"plain_text": text}]}}
    if has_children:
        payload["has_children"] = True
    if block_id is not None:
        payload["id"] = block_id
    return payload


def empty_block(kind="divider", *, has_children=False, block_id=None):
    payload = {"type": kind, kind: {}, "has_children": bool(has_children)}
    if block_id is not None:
        payload["id"] = block_id
    return payload


def test_fetches_page_and_content(monkeypatch):
    fake = FakeClient([
        page_response(),
        FakeResponse({"results": [block("Hello"), block("Point", "bulleted_list_item")], "has_more": False}),
    ])
    monkeypatch.setattr("luna.notion_reader.httpx.Client", lambda **kwargs: fake)

    title, content, _ = NotionReader("test-token").fetch_page("page-1")

    assert title == "Bootstrap"
    assert content == "Hello\n- Point"
    assert len(fake.calls) == 2


def test_follows_next_cursor(monkeypatch):
    fake = FakeClient([
        page_response(),
        FakeResponse({"results": [block("First")], "has_more": True, "next_cursor": "cursor-2"}),
        FakeResponse({"results": [block("Second")], "has_more": False, "next_cursor": None}),
    ])
    monkeypatch.setattr("luna.notion_reader.httpx.Client", lambda **kwargs: fake)

    _, content, _ = NotionReader("test-token").fetch_page("page-1")

    assert content == "First\nSecond"
    assert fake.calls[2][1]["start_cursor"] == "cursor-2"


def test_fails_if_more_pages_have_no_cursor(monkeypatch):
    fake = FakeClient([
        page_response(),
        FakeResponse({"results": [block("Partial")], "has_more": True, "next_cursor": None}),
    ])
    monkeypatch.setattr("luna.notion_reader.httpx.Client", lambda **kwargs: fake)

    with pytest.raises(NotionPaginationError, match="without next_cursor"):
        NotionReader("test-token").fetch_page("page-1")


def test_propagates_permission_error(monkeypatch):
    fake = FakeClient([page_response(), FakeResponse({"message": "Forbidden"}, status_code=403)])
    monkeypatch.setattr("luna.notion_reader.httpx.Client", lambda **kwargs: fake)

    with pytest.raises(httpx.HTTPStatusError):
        NotionReader("test-token").fetch_page("page-1")


def test_propagates_network_error(monkeypatch):
    fake = FakeClient([page_response(), httpx.ConnectError("offline")])
    monkeypatch.setattr("luna.notion_reader.httpx.Client", lambda **kwargs: fake)

    with pytest.raises(httpx.ConnectError):
        NotionReader("test-token").fetch_page("page-1")


def test_numbered_list_is_sequential():
    items = [block("Alpha", "numbered_list_item"), block("Beta", "numbered_list_item"), block("Other")]
    assert NotionReader._block_text(items[0], 1) == "1. Alpha"
    assert NotionReader._block_text(items[1], 2) == "2. Beta"


def test_heading_with_children_keeps_text_and_flags_nested(monkeypatch):
    nested = block(
        "Section",
        "heading_2",
        has_children=True,
        block_id="aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
    )
    fake = FakeClient([
        page_response(),
        FakeResponse({"results": [nested], "has_more": False}),
    ])
    monkeypatch.setattr("luna.notion_reader.httpx.Client", lambda **kwargs: fake)

    _, content, _ = NotionReader("test-token").fetch_page("page-1")

    assert "## Section" in content
    assert "Unexpanded nested content" in content
    assert "type=heading_2" in content
    assert "aaaaaaaa" in content
    assert "eeee" in content
    assert "secret_" not in content
    assert content.count("Unexpanded nested content") == 1


def test_empty_block_with_children_is_not_silently_dropped(monkeypatch):
    # divider has no rich text and previously returned "" — children must be flagged.
    nested = empty_block(
        "divider",
        has_children=True,
        block_id="11111111-2222-3333-4444-555555555555",
    )
    fake = FakeClient([
        page_response(),
        FakeResponse({"results": [nested], "has_more": False}),
    ])
    monkeypatch.setattr("luna.notion_reader.httpx.Client", lambda **kwargs: fake)

    _, content, _ = NotionReader("test-token").fetch_page("page-1")

    assert content.strip() != ""
    assert "Unexpanded nested content" in content
    assert "type=divider" in content
    assert "11111111" in content


def test_normal_block_without_children_has_no_nested_warning(monkeypatch):
    fake = FakeClient([
        page_response(),
        FakeResponse({"results": [block("Plain", block_id="plain-block-1")], "has_more": False}),
    ])
    monkeypatch.setattr("luna.notion_reader.httpx.Client", lambda **kwargs: fake)

    _, content, _ = NotionReader("test-token").fetch_page("page-1")

    assert content == "Plain"
    assert "Unexpanded nested content" not in content


def test_no_duplicate_nested_warning_for_same_block(monkeypatch):
    nested = block(
        "Parent",
        "paragraph",
        has_children=True,
        block_id="abcdef01-2345-6789-abcd-ef0123456789",
    )
    fake = FakeClient([
        page_response(),
        FakeResponse({"results": [nested, nested], "has_more": False}),
    ])
    monkeypatch.setattr("luna.notion_reader.httpx.Client", lambda **kwargs: fake)

    _, content, _ = NotionReader("test-token").fetch_page("page-1")

    assert content.count("Parent") == 2
    assert content.count("Unexpanded nested content") == 1
    assert content.count("type=paragraph") == 1


def test_mask_redacts_token_like_block_ids():
    marker = NotionReader._unexpanded_children_marker(
        {"type": "toggle", "id": "secret_should_not_leak", "has_children": True}
    )
    assert "secret_should_not_leak" not in marker
    assert "<redacted>" in marker
    assert "type=toggle" in marker


def test_missing_results_raises(monkeypatch):
    fake = FakeClient([page_response(), FakeResponse({})])
    monkeypatch.setattr("luna.notion_reader.httpx.Client", lambda **kwargs: fake)
    with pytest.raises(NotionPaginationError):
        NotionReader("test-token").fetch_page("page-1")

    fake = FakeClient([page_response(), FakeResponse({"has_more": False})])
    monkeypatch.setattr("luna.notion_reader.httpx.Client", lambda **kwargs: fake)
    with pytest.raises(NotionPaginationError):
        NotionReader("test-token").fetch_page("page-1")


def test_results_not_list_raises(monkeypatch):
    fake = FakeClient([page_response(), FakeResponse({"results": {}})])
    monkeypatch.setattr("luna.notion_reader.httpx.Client", lambda **kwargs: fake)
    with pytest.raises(NotionPaginationError):
        NotionReader("test-token").fetch_page("page-1")


def test_missing_block_id_unexpanded_flagged(monkeypatch):
    b1 = {"type": "paragraph", "paragraph": {"rich_text": [{"plain_text": "A"}]}, "has_children": True}
    b2 = {"type": "paragraph", "paragraph": {"rich_text": [{"plain_text": "B"}]}, "has_children": True}
    fake = FakeClient([page_response(), FakeResponse({"results": [b1, b2], "has_more": False})])
    monkeypatch.setattr("luna.notion_reader.httpx.Client", lambda **kwargs: fake)

    _, content, meta = NotionReader("test-token").fetch_page("page-1")

    assert content.count("Unexpanded nested content") == 2
    assert meta["has_unexpanded"] is True


def test_classify_rate_limit_401_403_404():
    from luna.notion_reader import classify_notion_error

    cases = [(429, "rate_limit"), (401, "auth_failure"), (403, "permission_denied"), (404, "not_found")]
    for status, expected in cases:
        request = httpx.Request("GET", "https://api.notion.com/v1/test")
        response = FakeResponse({}, status_code=status)
        response.request = request
        exc = httpx.HTTPStatusError("HTTP error", request=request, response=response)
        assert classify_notion_error(exc) == expected

    request = httpx.Request("GET", "https://api.notion.com/v1/test")
    response = FakeResponse({"code": "object_not_found"}, status_code=404)
    response.request = request
    exc = httpx.HTTPStatusError("HTTP error", request=request, response=response)
    assert classify_notion_error(exc) == "not_found"


def test_fetch_page_returns_meta_tuple(monkeypatch):
    fake = FakeClient([page_response(), FakeResponse({"results": [block("Hello")], "has_more": False})])
    monkeypatch.setattr("luna.notion_reader.httpx.Client", lambda **kwargs: fake)

    title, content, meta = NotionReader("test-token").fetch_page("page-1")

    assert title == "Bootstrap"
    assert meta["has_unexpanded"] is False
    assert meta["block_count"] >= 1


def test_child_page_block_sets_unexpanded(monkeypatch):
    b = {"type": "child_page", "child_page": {"title": "Child"}, "id": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"}
    fake = FakeClient([page_response(), FakeResponse({"results": [b], "has_more": False})])
    monkeypatch.setattr("luna.notion_reader.httpx.Client", lambda **kwargs: fake)

    _, content, meta = NotionReader("test-token").fetch_page("page-1")

    assert meta["has_unexpanded"] is True
    assert "contents not expanded" in content


def test_repeated_next_cursor_raises(monkeypatch):
    fake = FakeClient([
        page_response(),
        FakeResponse({"results": [block("First")], "has_more": True, "next_cursor": "c1"}),
        FakeResponse({"results": [block("Second")], "has_more": True, "next_cursor": "c1"}),
    ])
    monkeypatch.setattr("luna.notion_reader.httpx.Client", lambda **kwargs: fake)

    from luna.notion_reader import NotionPaginationError, classify_notion_error

    with pytest.raises(NotionPaginationError, match=r"Repeated|loop") as exc_info:
        NotionReader("test-token").fetch_page("page-1")
    assert classify_notion_error(exc_info.value) == "pagination_error"


def test_exceeded_block_page_cap_raises(monkeypatch):
    monkeypatch.setattr("luna.notion_reader.MAX_BLOCK_PAGES", 2)
    monkeypatch.setattr(NotionReader, "MAX_BLOCK_PAGES", 2, raising=False)

    fake = FakeClient([
        page_response(),
        FakeResponse({"results": [block("P1")], "has_more": True, "next_cursor": "c2"}),
        FakeResponse({"results": [block("P2")], "has_more": True, "next_cursor": "c3"}),
        FakeResponse({"results": [block("P3")], "has_more": True, "next_cursor": "c4"}),
    ])
    monkeypatch.setattr("luna.notion_reader.httpx.Client", lambda **kwargs: fake)

    from luna.notion_reader import NotionPaginationError

    with pytest.raises(NotionPaginationError, match=r"Exceeded|MAX_BLOCK_PAGES"):
        NotionReader("test-token").fetch_page("page-1")


def test_normal_multipage_under_cap_ok(monkeypatch):
    fake = FakeClient([
        page_response(),
        FakeResponse({"results": [block("First")], "has_more": True, "next_cursor": "c2"}),
        FakeResponse({"results": [block("Second")], "has_more": False}),
    ])
    monkeypatch.setattr("luna.notion_reader.httpx.Client", lambda **kwargs: fake)

    title, content, meta = NotionReader("test-token").fetch_page("page-1")

    assert content == "First\nSecond"
    assert meta["page_fetch_count"] == 2
