"""Tests for the stdio bridge to the LibreOffice extension REST API."""

import sys
from pathlib import Path

import pytest
from mcp import Client

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src import libreoffice_live_bridge as bridge


class FakeResponse:
    def raise_for_status(self):
        pass

    def json(self):
        return {"success": True, "content": "Hello from LibreOffice"}


@pytest.mark.asyncio
async def test_tools_are_registered_and_forward_calls(monkeypatch):
    requests = []

    def fake_post(url, json, timeout):
        requests.append((url, json, timeout))
        return FakeResponse()

    monkeypatch.setattr(bridge.httpx, "post", fake_post)

    async with Client(bridge.mcp) as client:
        tools = await client.list_tools()
        names = {tool.name for tool in tools.tools}
        assert {
            "create_document_live",
            "insert_text_live",
            "get_document_info_live",
            "format_text_live",
            "save_document_live",
            "export_document_live",
            "get_text_content_live",
            "list_open_documents",
        } <= names

        result = await client.call_tool(
            "insert_text_live", {"text": "Hello", "position": 0}
        )

    assert not result.is_error
    assert requests == [
        (
            "http://localhost:8765/tools/insert_text_live",
            {"text": "Hello", "position": 0},
            bridge.REQUEST_TIMEOUT,
        )
    ]


@pytest.mark.asyncio
async def test_optional_formatting_values_are_omitted(monkeypatch):
    requests = []

    def fake_post(url, json, timeout):
        requests.append(json)
        return FakeResponse()

    monkeypatch.setattr(bridge.httpx, "post", fake_post)

    async with Client(bridge.mcp) as client:
        result = await client.call_tool("format_text_live", {"bold": False})

    assert not result.is_error
    assert requests == [{"bold": False}]


def test_unavailable_extension_returns_actionable_error(monkeypatch):
    def fail_post(*args, **kwargs):
        raise bridge.httpx.ConnectError("connection refused")

    monkeypatch.setattr(bridge.httpx, "post", fail_post)

    with pytest.raises(RuntimeError, match="Start the MCP extension in LibreOffice"):
        bridge.get_document_info_live()
