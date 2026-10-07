"""Tests for read-only live document search using mocked UNO objects."""

import importlib.util
import sys
import types
from pathlib import Path
from types import SimpleNamespace
from urllib.request import Request, urlopen
import json

import pytest


ROOT = Path(__file__).resolve().parents[1]
PLUGIN_PYTHONPATH = ROOT / "plugin/pythonpath"


class FakeEnumeration:
    def __init__(self, items):
        self.items = list(items)
        self.index = 0

    def hasMoreElements(self):
        return self.index < len(self.items)

    def nextElement(self):
        item = self.items[self.index]
        self.index += 1
        return item


class FakeContainer:
    def __init__(self, items):
        self.items = list(items)

    def createEnumeration(self):
        return FakeEnumeration(self.items)


class FakeRun:
    def __init__(self, text, **formatting):
        self.text = text
        for name, value in formatting.items():
            setattr(self, name, value)

    def getString(self):
        return self.text


class FakeParagraph(FakeContainer):
    def __init__(self, text, runs=(), **formatting):
        super().__init__(runs)
        self.text = text
        for name, value in formatting.items():
            setattr(self, name, value)

    def getString(self):
        return self.text


class FakeTable:
    def __init__(self, name, cells):
        self.Name = name
        self.cells = cells

    def getCellNames(self):
        return list(self.cells)

    def getCellByName(self, name):
        return self.cells[name]


class FakeTableCell:
    def __init__(self, text):
        self.text = FakeContainer([text])

    def getText(self):
        return self.text


class FakeCell:
    def __init__(self, text="", formula="", **formatting):
        self.text = text
        self.formula = formula
        for name, value in formatting.items():
            setattr(self, name, value)

    def getString(self):
        return self.text

    def getFormula(self):
        return self.formula or self.text


class FakeCalcCursor:
    def __init__(self, address):
        self.address = address

    def gotoStartOfUsedArea(self, expand):
        pass

    def gotoEndOfUsedArea(self, expand):
        pass

    def getRangeAddress(self):
        return self.address


class FakeSheet:
    def __init__(self, name, address, cells):
        self.name = name
        self.address = address
        self.cells = cells

    def getName(self):
        return self.name

    def createCursor(self):
        return FakeCalcCursor(self.address)

    def getCellByPosition(self, column, row):
        return self.cells.get((column, row), FakeCell())


class FakeIndexContainer:
    def __init__(self, items):
        self.items = list(items)

    def getCount(self):
        return len(self.items)

    def getByIndex(self, index):
        return self.items[index]


class FakeShape(FakeRun):
    def __init__(self, text, shape_type="com.sun.star.drawing.TextShape", **props):
        super().__init__(text, **props)
        self.shape_type = shape_type

    def getShapeType(self):
        return self.shape_type


class FakeDocument:
    SERVICES = {
        "writer": {"com.sun.star.text.TextDocument"},
        "calc": {"com.sun.star.sheet.SpreadsheetDocument"},
        "impress": {"com.sun.star.presentation.PresentationDocument"},
        "draw": {"com.sun.star.drawing.DrawingDocument"},
        "unknown": set(),
    }

    def __init__(
        self,
        doc_type,
        title="Example",
        url="file:///example",
        text=None,
        sheets=None,
        pages=None,
    ):
        self.doc_type = doc_type
        self.Title = title
        self.url = url
        self.text = text
        self.sheets = sheets
        self.pages = pages

    def supportsService(self, service):
        return service in self.SERVICES[self.doc_type]

    def getURL(self):
        return self.url

    def getText(self):
        return self.text

    def getSheets(self):
        return FakeIndexContainer(self.sheets)

    def getDrawPages(self):
        return FakeIndexContainer(self.pages)


class FakeDesktop:
    def __init__(self, documents, active=None):
        self.documents = list(documents)
        self.active = active

    def getCurrentComponent(self):
        return self.active

    def getComponents(self):
        return FakeContainer(self.documents)


def load_uno_bridge(monkeypatch):
    package_name = "_plugin_document_search_uno_test"
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


def make_bridge(monkeypatch, documents, active=None):
    module = load_uno_bridge(monkeypatch)
    bridge = module.UNOBridge.__new__(module.UNOBridge)
    bridge.desktop = FakeDesktop(documents, active)
    return bridge


def test_writer_returns_paragraph_style_and_formatted_runs(monkeypatch):
    paragraph = FakeParagraph(
        "A searchable heading",
        runs=[
            FakeRun(
                "searchable",
                CharFontName="Liberation Serif",
                CharHeight=16.0,
                CharWeight=150.0,
                CharPosture=2,
            )
        ],
        ParaStyleName="Heading 1",
        OutlineLevel=1,
        ParaAdjust="CENTER",
    )
    document = FakeDocument(
        "writer",
        text=FakeContainer([FakeParagraph("Unrelated"), paragraph]),
    )
    bridge = make_bridge(monkeypatch, [document], document)

    result = bridge.search_document_elements("SEARCHABLE")

    assert result["success"] is True
    assert result["document"]["type"] == "writer"
    assert result["count"] == 1
    assert result["matches"][0]["location"] == {
        "section": "body",
        "paragraph": 2,
    }
    assert result["matches"][0]["formatting"]["style"] == "Heading 1"
    assert result["matches"][0]["formatting"]["outline_level"] == 1
    assert result["matches"][0]["runs"][0]["formatting"] == {
        "font_name": "Liberation Serif",
        "font_size": 16.0,
        "font_weight": 150.0,
        "bold": True,
        "font_posture": 2,
        "italic": True,
    }


def test_writer_search_includes_table_cells(monkeypatch):
    table = FakeTable(
        "Table1",
        {"B2": FakeTableCell(FakeParagraph("Needle in table"))},
    )
    document = FakeDocument("writer", text=FakeContainer([table]))
    bridge = make_bridge(monkeypatch, [document], document)

    result = bridge.search_document_elements("needle")

    assert result["count"] == 1
    assert result["matches"][0]["location"] == {
        "section": "table",
        "table": "Table1",
        "cell": "B2",
        "paragraph": 1,
    }


def test_calc_returns_cell_location_value_formula_and_formatting(monkeypatch):
    sheet = FakeSheet(
        "Data",
        SimpleNamespace(StartColumn=0, EndColumn=1, StartRow=0, EndRow=1),
        {
            (1, 1): FakeCell(
                "Total: 42",
                '=CONCATENATE("Total: ",42)',
                CellStyle="Result",
                NumberFormat=5,
                CharFontName="Liberation Sans",
                CharHeight=11.0,
                CharWeight=100.0,
                CharPosture=0,
                CellBackColor=16777215,
            )
        },
    )
    document = FakeDocument("calc", sheets=[sheet])
    bridge = make_bridge(monkeypatch, [document], document)

    result = bridge.search_document_elements("total")

    assert result["success"] is True
    assert result["cells_scanned"] == 4
    assert result["matches"][0]["location"] == {
        "sheet": "Data",
        "cell": "B2",
        "sheet_index": 1,
    }
    assert result["matches"][0]["formula"] == '=CONCATENATE("Total: ",42)'
    assert result["matches"][0]["formatting"]["style"] == "Result"
    assert result["matches"][0]["formatting"]["number_format"] == 5


def test_calc_column_names_cover_multi_letter_columns(monkeypatch):
    bridge = make_bridge(monkeypatch, [])

    assert bridge._calc_column_name(0) == "A"
    assert bridge._calc_column_name(25) == "Z"
    assert bridge._calc_column_name(26) == "AA"
    assert bridge._calc_column_name(701) == "ZZ"


@pytest.mark.parametrize("doc_type", ["impress", "draw"])
def test_draw_and_impress_return_text_shape_location_and_style(monkeypatch, doc_type):
    shape = FakeShape(
        "A searchable slide label",
        Name="Title",
        CharFontName="Liberation Sans",
        CharHeight=22.0,
        CharWeight=150.0,
        CharPosture=0,
        FillColor=255,
    )
    document = FakeDocument(
        doc_type,
        pages=[FakeIndexContainer([FakeShape("unrelated"), shape])],
    )
    bridge = make_bridge(monkeypatch, [document], document)

    result = bridge.search_document_elements("SLIDE")

    assert result["success"] is True
    assert result["document"]["type"] == doc_type
    assert result["matches"][0]["location"] == {
        "page": 1,
        "shape": "Title",
        "shape_index": "2",
    }
    assert result["matches"][0]["shape_type"] == "com.sun.star.drawing.TextShape"
    assert result["matches"][0]["formatting"]["font_size"] == 22.0
    assert result["matches"][0]["formatting"]["fill_color"] == 255


def test_document_can_be_selected_by_exact_url(monkeypatch):
    active = FakeDocument(
        "writer", title="Active", url="file:///active", text=FakeContainer([])
    )
    target = FakeDocument(
        "writer",
        title="Target",
        url="file:///target",
        text=FakeContainer([FakeParagraph("Find this target")]),
    )
    bridge = make_bridge(monkeypatch, [active, target], active)

    result = bridge.search_document_elements(
        "target", document_identifier="file:///target"
    )

    assert result["success"] is True
    assert result["document"]["title"] == "Target"


def test_missing_or_ambiguous_document_target_is_rejected(monkeypatch):
    first = FakeDocument("writer", title="Same", url="file:///one")
    second = FakeDocument("writer", title="Same", url="file:///two")
    bridge = make_bridge(monkeypatch, [first, second], first)

    missing = bridge.search_document_elements(
        "text", document_identifier="file:///not-open"
    )
    ambiguous = bridge.search_document_elements("text", document_identifier="Same")

    assert missing["success"] is False
    assert "files are not opened" in missing["error"]
    assert ambiguous["success"] is False
    assert "multiple open documents" in ambiguous["error"]


def test_no_match_unsupported_type_and_input_limits(monkeypatch):
    writer = FakeDocument("writer", text=FakeContainer([FakeParagraph("other")]))
    unknown = FakeDocument("unknown")
    bridge = make_bridge(monkeypatch, [writer], writer)

    no_match = bridge.search_document_elements("missing")
    invalid_query = bridge.search_document_elements("")
    invalid_limit = bridge.search_document_elements("other", max_results=501)
    bridge.desktop.active = unknown
    unsupported = bridge.search_document_elements("text")

    assert no_match["success"] is True
    assert no_match["matches"] == []
    assert no_match["truncated"] is False
    assert invalid_query["success"] is False
    assert invalid_limit["success"] is False
    assert unsupported["success"] is False
    assert "not supported" in unsupported["error"]


def test_search_result_limit_sets_truncated(monkeypatch):
    document = FakeDocument(
        "writer",
        text=FakeContainer([FakeParagraph("needle one"), FakeParagraph("needle two")]),
    )
    bridge = make_bridge(monkeypatch, [document], document)

    result = bridge.search_document_elements("needle", max_results=1)

    assert result["count"] == 1
    assert result["truncated"] is True


def test_calc_scan_budget_sets_truncated(monkeypatch):
    sheet = FakeSheet(
        "Large",
        SimpleNamespace(StartColumn=0, EndColumn=1, StartRow=0, EndRow=1),
        {},
    )
    document = FakeDocument("calc", sheets=[sheet])
    bridge = make_bridge(monkeypatch, [document], document)
    bridge.MAX_CALC_CELLS_TO_SCAN = 1

    result = bridge.search_document_elements("not found")

    assert result["success"] is True
    assert result["cells_scanned"] == 1
    assert result["truncated"] is True


def test_plugin_rest_registers_and_executes_live_search(monkeypatch):
    package_name = "_plugin_document_search_server_test"
    package = types.ModuleType(package_name)
    package.__path__ = [str(PLUGIN_PYTHONPATH)]
    monkeypatch.setitem(sys.modules, package_name, package)

    bridge_module = types.ModuleType(f"{package_name}.uno_bridge")

    class FakeUNOBridge:
        def search_document_elements(self, query, document_identifier=None, max_results=100):
            return {
                "success": True,
                "query": query,
                "document_identifier": document_identifier,
                "max_results": max_results,
            }

    bridge_module.UNOBridge = FakeUNOBridge
    monkeypatch.setitem(sys.modules, bridge_module.__name__, bridge_module)

    server_name = f"{package_name}.mcp_server"
    server_spec = importlib.util.spec_from_file_location(
        server_name, PLUGIN_PYTHONPATH / "mcp_server.py"
    )
    server_module = importlib.util.module_from_spec(server_spec)
    monkeypatch.setitem(sys.modules, server_name, server_module)
    server_spec.loader.exec_module(server_module)
    server_module.mcp_server = server_module.LibreOfficeMCPServer()

    interface_name = f"{package_name}.ai_interface"
    interface_spec = importlib.util.spec_from_file_location(
        interface_name, PLUGIN_PYTHONPATH / "ai_interface.py"
    )
    interface_module = importlib.util.module_from_spec(interface_spec)
    monkeypatch.setitem(sys.modules, interface_name, interface_module)
    interface_spec.loader.exec_module(interface_module)

    interface = interface_module.AIInterface(port=0, host="127.0.0.1")
    interface.start()
    base_url = f"http://127.0.0.1:{interface.server.server_address[1]}"
    try:
        with urlopen(f"{base_url}/tools", timeout=2) as response:
            tools = json.load(response)["tools"]
        tool = next(
            tool for tool in tools if tool["name"] == "search_document_elements_live"
        )
        assert tool["parameters"]["required"] == ["query"]

        request = Request(
            f"{base_url}/tools/search_document_elements_live",
            data=json.dumps(
                {
                    "query": "heading",
                    "document_identifier": "file:///target",
                    "max_results": 7,
                }
            ).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(request, timeout=2) as response:
            result = json.load(response)

        assert result == {
            "success": True,
            "query": "heading",
            "document_identifier": "file:///target",
            "max_results": 7,
        }
    finally:
        interface.stop()
