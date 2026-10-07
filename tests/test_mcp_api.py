"""MCP 2.x protocol regression tests without a LibreOffice installation."""

import sys
from pathlib import Path

import pytest
from mcp import Client
from mcp.server import MCPServer

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import libremcp


@pytest.mark.asyncio
async def test_tools_and_structured_results(tmp_path):
    assert isinstance(libremcp.mcp, MCPServer)
    document = tmp_path / "sample.odt"
    document.write_text("test")

    async with Client(libremcp.mcp) as client:
        tools = await client.list_tools()
        assert "get_document_info" in {tool.name for tool in tools.tools}
        result = await client.call_tool("get_document_info", {"path": str(document)})
        assert not result.is_error
        assert result.structured_content["filename"] == "sample.odt"
        assert result.structured_content["exists"] is True


@pytest.mark.asyncio
async def test_document_resource_with_nested_path(monkeypatch):
    def read_text(path):
        assert path == "/tmp/nested/sample.odt"
        return libremcp.TextContent(
            content="Hello world", word_count=2, char_count=11, page_count=None
        )

    monkeypatch.setattr(libremcp, "read_document_text", read_text)
    async with Client(libremcp.mcp) as client:
        resources = await client.list_resources()
        assert "documents://" in {resource.uri for resource in resources.resources}
        result = await client.read_resource("document://tmp/nested/sample.odt")
        assert "Hello world" in result.contents[0].text
