"""Isolated test for the typed live-search proxy."""

import importlib.util
import sys
import types
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BRIDGE_PATH = ROOT / "src/libreoffice_live_bridge.py"


class FakeMCPServer:
    def __init__(self, *args, **kwargs):
        self.tools = {}

    def tool(self, description=""):
        def register(function):
            self.tools[function.__name__] = function
            return function

        return register


def load_bridge(monkeypatch):
    mcp_module = types.ModuleType("mcp")
    mcp_module.__path__ = []
    server_module = types.ModuleType("mcp.server")
    server_module.MCPServer = FakeMCPServer
    monkeypatch.setitem(sys.modules, "mcp", mcp_module)
    monkeypatch.setitem(sys.modules, "mcp.server", server_module)

    module_name = "_libreoffice_live_search_bridge_test"
    spec = importlib.util.spec_from_file_location(module_name, BRIDGE_PATH)
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, module_name, module)
    spec.loader.exec_module(module)
    return module


def test_search_proxy_forwards_query_and_optional_document(monkeypatch):
    bridge = load_bridge(monkeypatch)
    calls = []

    def fake_execute_tool(tool_name, parameters):
        calls.append((tool_name, parameters))
        return {"success": True}

    monkeypatch.setattr(bridge, "_execute_tool", fake_execute_tool)

    result = bridge.search_document_elements_live(
        "heading",
        document_identifier="file:///target",
        max_results=12,
    )

    assert result == {"success": True}
    assert calls == [
        (
            "search_document_elements_live",
            {
                "query": "heading",
                "max_results": 12,
                "document_identifier": "file:///target",
            },
        )
    ]
    assert "search_document_elements_live" in bridge.mcp.tools
