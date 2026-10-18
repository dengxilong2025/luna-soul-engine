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


def block(text, kind="paragraph"):
    return {"type": kind, kind: {"rich_text": [{"plain_text": text}]}}


def test_fetches_page_and_content(monkeypatch):
    fake = FakeClient([
        page_response(),
        FakeResponse({"results": [block("Hello"), block("Point", "bulleted_list_item")], "has_more": False}),
    ])
    monkeypatch.setattr("luna.notion_reader.httpx.Client", lambda **kwargs: fake)

    title, content = NotionReader("test-token").fetch_page("page-1")

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

    _, content = NotionReader("test-token").fetch_page("page-1")

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
