"""Tests for selected-text operations without requiring LibreOffice."""

import importlib.util
import json
import sys
import types
from pathlib import Path
from urllib.request import Request, urlopen

import pytest


ROOT = Path(__file__).resolve().parents[1]
PLUGIN_PYTHONPATH = ROOT / "plugin/pythonpath"


class FakeTextRange:
    def __init__(self, text):
        self.text = text

    def getString(self):
        return self.text

    def setString(self, text):
        self.text = text


class FakeSelectionCollection:
    def __init__(self, ranges):
        self.ranges = ranges

    def getCount(self):
        return len(self.ranges)

    def getByIndex(self, index):
        return self.ranges[index]


class FakeDocument:
    def __init__(self, selection, doc_type="writer"):
        self.selection = selection
        self.doc_type = doc_type

    def supportsService(self, service_name):
        return (
            self.doc_type == "writer"
            and service_name == "com.sun.star.text.TextDocument"
        )

    def getCurrentController(self):
        return self

    def getSelection(self):
        return self.selection


def load_uno_bridge(monkeypatch):
    package_name = "_plugin_selected_text_uno_test"

    for module_name in ("com", "com.sun", "com.sun.star"):
        package = types.ModuleType(module_name)
        package.__path__ = []
        monkeypatch.setitem(sys.modules, module_name, package)

    for module_name, interface_name in (
        ("com.sun.star.beans", "PropertyValue"),
        ("com.sun.star.document", "XDocumentEventListener"),
        ("com.sun.star.awt", "XActionListener"),
    ):
        module = types.ModuleType(module_name)
        setattr(module, interface_name, type(interface_name, (), {}))
        monkeypatch.setitem(sys.modules, module_name, module)

    monkeypatch.setitem(sys.modules, "uno", types.ModuleType("uno"))
    monkeypatch.setitem(sys.modules, "unohelper", types.ModuleType("unohelper"))

    package = types.ModuleType(package_name)
    package.__path__ = [str(PLUGIN_PYTHONPATH)]
    monkeypatch.setitem(sys.modules, package_name, package)

    module_name = f"{package_name}.uno_bridge"
    spec = importlib.util.spec_from_file_location(
        module_name, PLUGIN_PYTHONPATH / "uno_bridge.py"
    )
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, module_name, module)
    spec.loader.exec_module(module)
    return module


def test_reads_direct_writer_text_range(monkeypatch):
    module = load_uno_bridge(monkeypatch)
    selected_range = FakeTextRange("selected words")
    bridge = module.UNOBridge.__new__(module.UNOBridge)

    result = bridge.get_selected_text(FakeDocument(selected_range))

    assert result == {"success": True, "text": "selected words"}


def test_reads_single_range_from_selection_collection(monkeypatch):
    module = load_uno_bridge(monkeypatch)
    selected_range = FakeTextRange("selected words")
    bridge = module.UNOBridge.__new__(module.UNOBridge)

    result = bridge.get_selected_text(
        FakeDocument(FakeSelectionCollection([selected_range]))
    )

    assert result == {"success": True, "text": "selected words"}


@pytest.mark.parametrize(
    "doc,expected_error",
    [
        (FakeDocument(FakeSelectionCollection([])), "No text is selected"),
        (
            FakeDocument(FakeSelectionCollection([FakeTextRange("a"), FakeTextRange("b")])),
            "Select exactly one text range",
        ),
        (FakeDocument(object()), "not a text range"),
        (
            FakeDocument(FakeTextRange("selected words"), doc_type="calc"),
            "No active Writer document",
        ),
    ],
)
def test_rejects_missing_ambiguous_or_non_writer_selection(
    monkeypatch, doc, expected_error
):
    module = load_uno_bridge(monkeypatch)
    bridge = module.UNOBridge.__new__(module.UNOBridge)

    result = bridge.get_selected_text(doc)

    assert result["success"] is False
    assert expected_error in result["error"]


def test_replaces_only_matching_selection(monkeypatch):
    module = load_uno_bridge(monkeypatch)
    selected_range = FakeTextRange("old text")
    bridge = module.UNOBridge.__new__(module.UNOBridge)

    result = bridge.replace_selected_text(
        "old text", "corrected text", FakeDocument(selected_range)
    )

    assert result == {
        "success": True,
        "replaced_characters": 8,
        "inserted_characters": 14,
    }
    assert selected_range.text == "corrected text"


def test_mismatched_expected_text_does_not_change_selection(monkeypatch):
    module = load_uno_bridge(monkeypatch)
    selected_range = FakeTextRange("changed after review")
    bridge = module.UNOBridge.__new__(module.UNOBridge)

    result = bridge.replace_selected_text(
        "text seen earlier", "replacement", FakeDocument(selected_range)
    )

    assert result["success"] is False
    assert "no changes made" in result["error"]
    assert selected_range.text == "changed after review"


def load_plugin_server(monkeypatch):
    package_name = "_plugin_selected_text_server_test"
    package = types.ModuleType(package_name)
    package.__path__ = [str(PLUGIN_PYTHONPATH)]
    monkeypatch.setitem(sys.modules, package_name, package)

    bridge_module = types.ModuleType(f"{package_name}.uno_bridge")

    class FakeUNOBridge:
        STYLE_ATTRIBUTE_SPECS = {"CharFontName": {}}
        def get_selected_text(self):
            return {"success": True, "text": "selected"}

        def replace_selected_text(self, expected_text, replacement_text):
            return {
                "success": expected_text == "selected",
                "replacement_text": replacement_text,
            }

    bridge_module.UNOBridge = FakeUNOBridge
    monkeypatch.setitem(sys.modules, bridge_module.__name__, bridge_module)

    module_name = f"{package_name}.mcp_server"
    spec = importlib.util.spec_from_file_location(
        module_name, PLUGIN_PYTHONPATH / "mcp_server.py"
    )
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, module_name, module)
    spec.loader.exec_module(module)
    module.mcp_server = module.LibreOfficeMCPServer()

    ai_module_name = f"{package_name}.ai_interface"
    ai_spec = importlib.util.spec_from_file_location(
        ai_module_name, PLUGIN_PYTHONPATH / "ai_interface.py"
    )
    ai_module = importlib.util.module_from_spec(ai_spec)
    monkeypatch.setitem(sys.modules, ai_module_name, ai_module)
    ai_spec.loader.exec_module(ai_module)
    return module, ai_module


def test_rest_lists_and_executes_selected_text_tools(monkeypatch):
    server_module, ai_module = load_plugin_server(monkeypatch)
    interface = ai_module.AIInterface(port=0, host="127.0.0.1")
    interface.start()
    base_url = f"http://127.0.0.1:{interface.server.server_address[1]}"

    try:
        with urlopen(f"{base_url}/tools", timeout=2) as response:
            tools = json.load(response)["tools"]
        tool_names = {tool["name"] for tool in tools}
        assert "get_selected_text_live" in tool_names
        assert "replace_selected_text_live" in tool_names

        request = Request(
            f"{base_url}/tools/replace_selected_text_live",
            data=json.dumps({
                "expected_text": "selected",
                "replacement_text": "revised",
            }).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(request, timeout=2) as response:
            result = json.load(response)

        assert result == {"success": True, "replacement_text": "revised"}
    finally:
        interface.stop()
