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
            "search_document_elements_live",
            "search_document_headings_live",
            "get_writer_paragraph_styles_live",
            "update_writer_paragraph_style_live",
            "apply_writer_paragraph_formatting_live",
            "replace_document_elements_live",
            "get_selected_text_live",
            "replace_selected_text_live",
            "list_open_documents",
        } <= names

        result = await client.call_tool(
            "insert_text_live", {"text": "Hello", "position": 0}
        )
        await client.call_tool("get_selected_text_live", {})
        await client.call_tool(
            "replace_selected_text_live",
            {"expected_text": "old", "replacement_text": "new"},
        )
        await client.call_tool(
            "search_document_headings_live",
            {
                "query": "Agenda",
                "document_identifier": "file:///target",
                "max_results": 8,
            },
        )
        edits = [
            {
                "location": {"section": "body", "paragraph": 3},
                "expected_text": "🎯 Agenda",
                "expected_style": "Heading 1",
                "search_text": "🎯 ",
                "replacement_text": "",
            }
        ]
        await client.call_tool(
            "replace_document_elements_live",
            {"edits": edits, "document_identifier": "file:///target", "dry_run": False},
        )
        await client.call_tool(
            "get_writer_paragraph_styles_live",
            {
                "query": "normal",
                "document_identifier": "file:///target",
                "max_results": 9,
            },
        )
        await client.call_tool(
            "update_writer_paragraph_style_live",
            {
                "style_name": "normal",
                "property_name": "CharFontName",
                "value": "Calibri",
                "expected_current_value": "Liberation Serif",
                "document_identifier": "file:///target",
                "dry_run": False,
            },
        )
        targets = [
            {
                "location": {"section": "body", "paragraph": 3},
                "expected_text": "Guarded paragraph",
                "expected_style": "Body Text",
            }
        ]
        await client.call_tool(
            "apply_writer_paragraph_formatting_live",
            {
                "targets": targets,
                "property_name": "CharFontName",
                "value": "Calibri",
                "document_identifier": "file:///target",
                "dry_run": False,
                "override_direct": True,
            },
        )

    assert not result.is_error
    assert requests == [
        (
            "http://localhost:8765/tools/insert_text_live",
            {"text": "Hello", "position": 0},
            bridge.REQUEST_TIMEOUT,
        ),
        (
            "http://localhost:8765/tools/get_selected_text_live",
            {},
            bridge.REQUEST_TIMEOUT,
        ),
        (
            "http://localhost:8765/tools/replace_selected_text_live",
            {"expected_text": "old", "replacement_text": "new"},
            bridge.REQUEST_TIMEOUT,
        ),
        (
            "http://localhost:8765/tools/search_document_headings_live",
            {
                "max_results": 8,
                "query": "Agenda",
                "document_identifier": "file:///target",
            },
            bridge.REQUEST_TIMEOUT,
        ),
        (
            "http://localhost:8765/tools/replace_document_elements_live",
            {
                "edits": edits,
                "dry_run": False,
                "document_identifier": "file:///target",
            },
            bridge.REQUEST_TIMEOUT,
        ),
        (
            "http://localhost:8765/tools/get_writer_paragraph_styles_live",
            {
                "max_results": 9,
                "query": "normal",
                "document_identifier": "file:///target",
            },
            bridge.REQUEST_TIMEOUT,
        ),
        (
            "http://localhost:8765/tools/update_writer_paragraph_style_live",
            {
                "style_name": "normal",
                "property_name": "CharFontName",
                "value": "Calibri",
                "dry_run": False,
                "expected_current_value": "Liberation Serif",
                "document_identifier": "file:///target",
            },
            bridge.REQUEST_TIMEOUT,
        ),
        (
            "http://localhost:8765/tools/apply_writer_paragraph_formatting_live",
            {
                "targets": targets,
                "property_name": "CharFontName",
                "value": "Calibri",
                "dry_run": False,
                "document_identifier": "file:///target",
                "override_direct": True,
            },
            bridge.REQUEST_TIMEOUT,
        ),
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


@pytest.mark.asyncio
async def test_search_document_elements_forwards_optional_target(monkeypatch):
    requests = []

    def fake_post(url, json, timeout):
        requests.append((url, json, timeout))
        return FakeResponse()

    monkeypatch.setattr(bridge.httpx, "post", fake_post)

    async with Client(bridge.mcp) as client:
        result = await client.call_tool(
            "search_document_elements_live",
            {
                "query": "heading",
                "document_identifier": "file:///target",
                "max_results": 12,
            },
        )

    assert not result.is_error
    assert requests == [
        (
            "http://localhost:8765/tools/search_document_elements_live",
            {
                "query": "heading",
                "max_results": 12,
                "document_identifier": "file:///target",
            },
            bridge.REQUEST_TIMEOUT,
        )
    ]
