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
        self.inherited_properties = formatting.pop("_inherited_properties", {}).copy()
        for name, value in formatting.items():
            setattr(self, name, value)

    def getString(self):
        return self.text
    def getPropertyState(self, name):
        if not hasattr(self, name):
            return "UNAVAILABLE"
        if (
            name in self.inherited_properties
            and getattr(self, name) == self.inherited_properties[name]
        ):
            return "DEFAULT_VALUE"
        return "DIRECT_VALUE"

    def setPropertyToDefault(self, name):
        if name in self.inherited_properties:
            setattr(self, name, self.inherited_properties[name])
        elif hasattr(self, name):
            delattr(self, name)


class FakeParagraph(FakeContainer):
    def __init__(self, text, runs=(), **formatting):
        super().__init__(runs)
        self.text = text
        self.inherited_properties = formatting.pop("_inherited_properties", {}).copy()
        for name, value in formatting.items():
            setattr(self, name, value)

    def getString(self):
        return self.text

    def getText(self):
        return self

    def getStart(self):
        return self

    def createTextCursorByRange(self, text_range):
        return FakeTextCursor(self)
    def getPropertyState(self, name):
        if not hasattr(self, name):
            return "UNAVAILABLE"
        if (
            name in self.inherited_properties
            and getattr(self, name) == self.inherited_properties[name]
        ):
            return "DEFAULT_VALUE"
        return "DIRECT_VALUE"

    def setPropertyToDefault(self, name):
        if name in self.inherited_properties:
            setattr(self, name, self.inherited_properties[name])
        elif hasattr(self, name):
            delattr(self, name)


class FakeTextCursor:
    def __init__(self, paragraph):
        self.paragraph = paragraph
        self.position = 0
        self.anchor = None

    def _unit_to_index(self, units):
        return units if 0 <= units <= len(self.paragraph.text) else None

    def goRight(self, count, expand):
        target = self.position + count
        if self._unit_to_index(target) is None:
            return False
        if expand:
            if self.anchor is None:
                self.anchor = self.position
        else:
            self.anchor = None
        self.position = target
        return True

    def getString(self):
        if self.anchor is None:
            return ""
        start = self._unit_to_index(min(self.anchor, self.position))
        end = self._unit_to_index(max(self.anchor, self.position))
        return self.paragraph.text[start:end]

    def setString(self, value):
        start = self._unit_to_index(min(self.anchor, self.position))
        end = self._unit_to_index(max(self.anchor, self.position))
        self.paragraph.text = self.paragraph.text[:start] + value + self.paragraph.text[end:]
        self.position = self.anchor + len(value)
        self.anchor = None


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

class FakePropertySetInfo:
    PROPERTY_TYPES = {
        "CharFontName": "string",
        "CharHeight": "float",
        "CharWeight": "float",
        "CharPosture": "com.sun.star.awt.FontSlant",
        "CharColor": "long",
        "CharUnderline": "short",
        "ParaAdjust": "short",
        "ParaFirstLineIndent": "long",
        "ParaLeftMargin": "long",
        "ParaRightMargin": "long",
        "ParaTopMargin": "long",
        "ParaBottomMargin": "long",
    }

    def getPropertyByName(self, name):
        return SimpleNamespace(
            Type=SimpleNamespace(typeName=self.PROPERTY_TYPES[name])
        )


class FakeStyle:
    def __init__(self, **properties):
        self.inherited_properties = properties.pop("_inherited_properties", {}).copy()
        for name, value in properties.items():
            setattr(self, name, value)
    def getPropertySetInfo(self):
        return FakePropertySetInfo()

    def getPropertyState(self, name):
        if not hasattr(self, name):
            return "UNAVAILABLE"
        if (
            name in self.inherited_properties
            and getattr(self, name) == self.inherited_properties[name]
        ):
            return "DEFAULT_VALUE"
        return "DIRECT_VALUE"

    def setPropertyToDefault(self, name):
        if name in self.inherited_properties:
            setattr(self, name, self.inherited_properties[name])
        elif hasattr(self, name):
            delattr(self, name)


class FakeStyleFamily:
    def __init__(self, styles):
        self.styles = dict(styles)

    def getElementNames(self):
        return tuple(self.styles)

    def getByName(self, name):
        return self.styles[name]


class FakeStyleFamilies:
    def __init__(self, paragraph_styles):
        self.paragraph_styles = FakeStyleFamily(paragraph_styles)

    def getByName(self, name):
        if name != "ParagraphStyles":
            raise KeyError(name)
        return self.paragraph_styles


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
        paragraph_styles=None,
    ):
        self.doc_type = doc_type
        self.Title = title
        self.url = url
        self.text = text
        self.sheets = sheets
        self.pages = pages
        self.paragraph_styles = paragraph_styles or {}
        self.modified = False

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
    def getStyleFamilies(self):
        return FakeStyleFamilies(self.paragraph_styles)
    def setModified(self, modified):
        self.modified = modified

    def isModified(self):
        return self.modified


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

def test_paragraph_style_inspection_lists_exact_names_and_filters(monkeypatch):
    document = FakeDocument(
        "writer",
        paragraph_styles={
            "normal": FakeStyle(
                CharFontName="Liberation Serif",
                CharHeight=12.0,
                CharWeight=100.0,
                CharPosture=0,
                ParaAdjust="LEFT",
            ),
            "Text body": FakeStyle(
                CharFontName="Avenir",
                CharHeight=11.0,
                CharWeight=150.0,
                CharPosture=2,
                ParentStyle="Default Paragraph Style",
            ),
            "Heading 1": FakeStyle(CharFontName="Liberation Sans"),
        },
    )
    bridge = make_bridge(monkeypatch, [document], document)

    all_styles = bridge.get_writer_paragraph_styles()
    filtered = bridge.get_writer_paragraph_styles(query="BODY")
    limited = bridge.get_writer_paragraph_styles(max_results=2)

    assert all_styles["success"] is True
    assert [style["name"] for style in all_styles["styles"]] == [
        "normal",
        "Text body",
        "Heading 1",
    ]
    assert all_styles["styles"][0]["font_name"] == "Liberation Serif"
    assert all_styles["styles"][0]["alignment"] == "LEFT"
    assert all_styles["styles"][1]["character_defaults"]["italic"] is True
    assert all_styles["styles"][1]["parent_style"] == "Default Paragraph Style"
    assert [style["name"] for style in filtered["styles"]] == ["Text body"]
    assert limited["count"] == 2
    assert limited["truncated"] is True


def test_paragraph_style_update_previews_guards_and_preserves_direct_format(monkeypatch):
    style = FakeStyle(CharFontName="Liberation Serif")
    paragraph = FakeParagraph(
        "Directly formatted text",
        CharFontName="Avenir",
        ParaStyleName="normal",
    )
    document = FakeDocument(
        "writer",
        text=FakeContainer([paragraph]),
        paragraph_styles={"normal": style},
    )
    bridge = make_bridge(monkeypatch, [document], document)

    preview = bridge.update_writer_paragraph_style(
        property_name="CharFontName",
        value="Calibri",
        style_name="normal",
        expected_current_value="Liberation Serif",
    )
    stale = bridge.update_writer_paragraph_style(
        property_name="CharFontName",
        value="Calibri",
        style_name="normal",
        expected_current_value="Avenir",
        dry_run=False,
    )
    missing = bridge.update_writer_paragraph_style(
        property_name="CharFontName",
        value="Calibri",
        style_name="Normal",
        dry_run=False,
    )

    assert preview["success"] is True
    assert preview["dry_run"] is True
    assert preview["before"] == "Liberation Serif"
    assert preview["after"] == "Calibri"
    assert preview["property_name"] == "CharFontName"
    assert preview["property_state_before"] == "DIRECT_VALUE"
    assert style.CharFontName == "Liberation Serif"
    assert stale["success"] is False
    assert "no changes made" in stale["error"]
    assert missing["success"] is False
    assert "exact names" in missing["error"]

    applied = bridge.update_writer_paragraph_style(
        property_name="CharFontName",
        value="Calibri",
        style_name="normal",
        expected_current_value="Liberation Serif",
        dry_run=False,
    )

    assert applied["success"] is True
    assert applied["before"] == "Liberation Serif"
    assert applied["after"] == "Calibri"
    assert applied["status"] == "updated"
    assert applied["saved"] is False
    assert style.CharFontName == "Calibri"
    assert paragraph.CharFontName == "Avenir"
    assert document.isModified() is True


def test_direct_paragraph_format_preserves_direct_runs_and_updates_inherited_runs(
    monkeypatch,
):
    direct_run = FakeRun("Direct", CharFontName="Avenir")
    inherited_run = FakeRun(
        " inherited",
        CharFontName="Liberation Serif",
        _inherited_properties={"CharFontName": "Liberation Serif"},
    )
    paragraph = FakeParagraph(
        "Direct inherited",
        runs=[direct_run, inherited_run],
        ParaStyleName="normal",
    )
    document = FakeDocument("writer", text=FakeContainer([paragraph]))
    bridge = make_bridge(monkeypatch, [document], document)
    targets = [
        {
            "location": {"section": "body", "paragraph": 1},
            "expected_text": "Direct inherited",
            "expected_style": "normal",
        }
    ]

    result = bridge.apply_writer_paragraph_formatting(
        targets=targets,
        property_name="CharFontName",
        value="Calibri",
        dry_run=False,
    )

    assert result["success"] is True
    assert result["dry_run"] is False
    assert result["saved"] is False
    assert result["updated_portions"] == 1
    assert result["changes"][0]["updated_portions"] == 1
    assert result["changes"][0]["preserved_direct_portions"] == 1
    assert direct_run.CharFontName == "Avenir"
    assert inherited_run.CharFontName == "Calibri"
    assert inherited_run.getPropertyState("CharFontName") == "DIRECT_VALUE"
    assert document.isModified() is True


def test_paragraph_style_tools_validate_writer_type_and_limits(monkeypatch):
    writer = FakeDocument("writer")
    calc = FakeDocument("calc")
    bridge = make_bridge(monkeypatch, [writer, calc], writer)

    invalid_query = bridge.get_writer_paragraph_styles(query="")
    invalid_limit = bridge.get_writer_paragraph_styles(max_results=501)
    bridge.desktop.active = calc
    unsupported_list = bridge.get_writer_paragraph_styles()
    unsupported_update = bridge.update_writer_paragraph_style(
        property_name="CharFontName",
        value="Calibri",
        style_name="normal",
    )

    assert invalid_query["success"] is False
    assert invalid_limit["success"] is False
    assert unsupported_list["success"] is False
    assert "only supported for Writer" in unsupported_list["error"]
    assert unsupported_update["success"] is False
    assert "only supported for Writer" in unsupported_update["error"]


def test_heading_search_finds_styles_and_outline_levels(monkeypatch):
    document = FakeDocument(
        "writer",
        text=FakeContainer(
            [
                FakeParagraph("Preamble"),
                FakeParagraph("Overview", ParaStyleName="Heading 1", OutlineLevel=0),
                FakeParagraph("Details", ParaStyleName="Custom section", OutlineLevel=2),
                FakeParagraph("Not a heading", ParaStyleName="Text Body", OutlineLevel=0),
                FakeParagraph("Title", ParaStyleName="Title", OutlineLevel=0),
            ]
        ),
    )
    bridge = make_bridge(monkeypatch, [document], document)

    result = bridge.search_document_headings()
    filtered = bridge.search_document_headings(query="DETAIL")

    assert result["success"] is True
    assert [match["text"] for match in result["matches"]] == [
        "Overview",
        "Details",
        "Title",
    ]
    assert [match["location"]["paragraph"] for match in result["matches"]] == [
        2,
        3,
        5,
    ]
    assert result["matches"][0]["formatting"]["style"] == "Heading 1"
    assert filtered["count"] == 1
    assert filtered["matches"][0]["text"] == "Details"


def test_heading_search_limit_and_writer_only_validation(monkeypatch):
    document = FakeDocument(
        "writer",
        text=FakeContainer(
            [
                FakeParagraph("First", ParaStyleName="Heading 1"),
                FakeParagraph("Second", ParaStyleName="Heading 2"),
            ]
        ),
    )
    calc = FakeDocument("calc", url="file:///calc")
    bridge = make_bridge(monkeypatch, [document, calc], document)

    limited = bridge.search_document_headings(max_results=1)
    unsupported = bridge.search_document_headings(document_identifier=calc.url)

    assert limited["count"] == 1
    assert limited["truncated"] is True
    assert unsupported["success"] is False
    assert "only supported for Writer" in unsupported["error"]


def make_edit(paragraph, paragraph_number, search_text, replacement_text):
    return {
        "location": {"section": "body", "paragraph": paragraph_number},
        "expected_text": paragraph.getString(),
        "expected_style": paragraph.ParaStyleName,
        "search_text": search_text,
        "replacement_text": replacement_text,
    }


def test_batch_replacement_dry_run_does_not_mutate(monkeypatch):
    heading = FakeParagraph(
        "🎯 Agenda sugerida",
        ParaStyleName="Heading 1",
        OutlineLevel=0,
    )
    document = FakeDocument("writer", text=FakeContainer([heading]))
    bridge = make_bridge(monkeypatch, [document], document)

    result = bridge.replace_document_elements(
        [make_edit(heading, 1, "🎯 ", "")]
    )

    assert result["success"] is True
    assert result["dry_run"] is True
    assert result["saved"] is False
    assert result["changes"][0]["after"] == "Agenda sugerida"
    assert result["changes"][0]["status"] == "preview"
    assert heading.getString() == "🎯 Agenda sugerida"


def test_batch_replacement_applies_verified_ranges_in_unicode_text(monkeypatch):
    first = FakeParagraph("🎯 Agenda sugerida", ParaStyleName="Heading 1")
    second = FakeParagraph("Proyectos 🚀 DIAD", ParaStyleName="Heading 2")
    document = FakeDocument("writer", text=FakeContainer([first, second]))
    bridge = make_bridge(monkeypatch, [document], document)

    result = bridge.replace_document_elements(
        [
            make_edit(first, 1, "🎯 ", ""),
            make_edit(second, 2, "🚀 ", ""),
        ],
        dry_run=False,
    )

    assert result["success"] is True
    assert result["dry_run"] is False
    assert result["saved"] is False
    assert first.getString() == "Agenda sugerida"
    assert second.getString() == "Proyectos DIAD"
    assert [change["status"] for change in result["changes"]] == [
        "applied",
        "applied",
    ]


def test_batch_preflight_rejects_stale_or_wrong_style_without_partial_edit(monkeypatch):
    stale = FakeParagraph("Changed heading", ParaStyleName="Heading 1")
    wrong_style = FakeParagraph("Changed style", ParaStyleName="Heading 2")
    valid = FakeParagraph("🎯 Agenda", ParaStyleName="Heading 3")
    document = FakeDocument("writer", text=FakeContainer([stale, wrong_style, valid]))
    bridge = make_bridge(monkeypatch, [document], document)
    stale_edit = make_edit(stale, 1, "heading", "")
    stale_edit["expected_text"] = "Old heading"
    style_edit = make_edit(wrong_style, 2, "Changed", "")
    style_edit["expected_style"] = "Heading 1"

    result = bridge.replace_document_elements(
        [stale_edit, style_edit, make_edit(valid, 3, "🎯 ", "")],
        dry_run=False,
    )

    assert result["success"] is False
    assert "no changes made" in result["error"]
    assert stale.getString() == "Changed heading"
    assert wrong_style.getString() == "Changed style"
    assert valid.getString() == "🎯 Agenda"


def test_batch_replacement_rejects_ambiguous_and_duplicate_targets(monkeypatch):
    paragraph = FakeParagraph(
        "Icon 🎯 and 🎯",
        ParaStyleName="Heading 1",
    )
    document = FakeDocument("writer", text=FakeContainer([paragraph]))
    bridge = make_bridge(monkeypatch, [document], document)
    ambiguous = make_edit(paragraph, 1, "🎯", "")
    duplicate = make_edit(paragraph, 1, "Icon", "")

    ambiguous_result = bridge.replace_document_elements([ambiguous], dry_run=False)
    duplicate_result = bridge.replace_document_elements(
        [duplicate, duplicate], dry_run=False
    )

    assert ambiguous_result["success"] is False
    assert "exactly once" in ambiguous_result["errors"][0]["error"]
    assert duplicate_result["success"] is False
    assert "one edit per paragraph" in duplicate_result["errors"][0]["error"]
    assert paragraph.getString() == "Icon 🎯 and 🎯"


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
        STYLE_ATTRIBUTE_SPECS = {"CharFontName": {}, "CharHeight": {}}
        def search_document_elements(self, query, document_identifier=None, max_results=100):
            return {
                "success": True,
                "query": query,
                "document_identifier": document_identifier,
                "max_results": max_results,
            }
        def search_document_headings(
            self, query=None, document_identifier=None, max_results=100
        ):
            return {
                "success": True,
                "query": query,
                "document_identifier": document_identifier,
                "max_results": max_results,
                "matches": [],
            }

        def get_writer_paragraph_styles(
            self, query=None, document_identifier=None, max_results=100
        ):
            return {
                "success": True,
                "query": query,
                "document_identifier": document_identifier,
                "max_results": max_results,
                "styles": [{"name": "normal", "font_name": "Liberation Serif"}],
            }

        def update_writer_paragraph_style(
            self,
            property_name,
            value,
            style_name=None,
            location=None,
            expected_text=None,
            expected_style=None,
            expected_current_value=None,
            document_identifier=None,
            dry_run=True,
        ):
            return {
                "success": True,
                "property_name": property_name,
                "value": value,
                "style_name": style_name,
                "location": location,
                "expected_text": expected_text,
                "expected_style": expected_style,
                "expected_current_value": expected_current_value,
                "document_identifier": document_identifier,
                "dry_run": dry_run,
                "saved": False,
            }
        def apply_writer_paragraph_formatting(
            self,
            targets,
            property_name,
            value,
            document_identifier=None,
            dry_run=True,
        ):
            return {
                "success": True,
                "targets": targets,
                "property_name": property_name,
                "value": value,
                "document_identifier": document_identifier,
                "dry_run": dry_run,
                "saved": False,
            }

        def replace_document_elements(
            self, edits, document_identifier=None, dry_run=True
        ):
            return {
                "success": True,
                "edits": edits,
                "document_identifier": document_identifier,
                "dry_run": dry_run,
                "saved": False,
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
        assert "property_name" not in tool["parameters"]["properties"]
        assert "value" not in tool["parameters"]["properties"]
        heading_tool = next(
            tool for tool in tools if tool["name"] == "search_document_headings_live"
        )
        assert "query" not in heading_tool["parameters"].get("required", [])
        replacement_tool = next(
            tool for tool in tools if tool["name"] == "replace_document_elements_live"
        )
        assert replacement_tool["parameters"]["properties"]["dry_run"]["default"] is True
        styles_tool = next(
            tool for tool in tools if tool["name"] == "get_writer_paragraph_styles_live"
        )
        assert "query" not in styles_tool["parameters"].get("required", [])
        update_style_tool = next(
            tool
            for tool in tools
            if tool["name"] == "update_writer_paragraph_style_live"
        )
        assert update_style_tool["parameters"]["required"] == [
            "property_name",
            "value",
        ]
        assert update_style_tool["parameters"]["properties"]["property_name"]["enum"] == [
            "CharFontName",
            "CharHeight",
        ]
        assert update_style_tool["parameters"]["properties"]["dry_run"]["default"] is True
        apply_format_tool = next(
            tool
            for tool in tools
            if tool["name"] == "apply_writer_paragraph_formatting_live"
        )
        assert apply_format_tool["parameters"]["required"] == [
            "targets",
            "property_name",
            "value",
        ]
        assert apply_format_tool["parameters"]["properties"]["dry_run"]["default"] is True

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
        heading_request = Request(
            f"{base_url}/tools/search_document_headings_live",
            data=json.dumps(
                {
                    "query": "Agenda",
                    "document_identifier": "file:///target",
                    "max_results": 4,
                }
            ).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(heading_request, timeout=2) as response:
            heading_result = json.load(response)
        styles_request = Request(
            f"{base_url}/tools/get_writer_paragraph_styles_live",
            data=json.dumps(
                {
                    "query": "normal",
                    "document_identifier": "file:///target",
                    "max_results": 9,
                }
            ).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(styles_request, timeout=2) as response:
            styles_result = json.load(response)
        update_style_request = Request(
            f"{base_url}/tools/update_writer_paragraph_style_live",
            data=json.dumps(
                {
                    "style_name": "normal",
                    "property_name": "CharFontName",
                    "value": "Calibri",
                    "expected_current_value": "Liberation Serif",
                    "document_identifier": "file:///target",
                    "dry_run": False,
                }
            ).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(update_style_request, timeout=2) as response:
            update_style_result = json.load(response)
        targets = [
            {
                "location": {"section": "body", "paragraph": 2},
                "expected_text": "Guarded paragraph",
                "expected_style": "Body Text",
            }
        ]
        apply_format_request = Request(
            f"{base_url}/tools/apply_writer_paragraph_formatting_live",
            data=json.dumps(
                {
                    "targets": targets,
                    "property_name": "CharFontName",
                    "value": "Calibri",
                    "document_identifier": "file:///target",
                    "dry_run": False,
                }
            ).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(apply_format_request, timeout=2) as response:
            apply_format_result = json.load(response)

        edits = [
            {
                "location": {"section": "body", "paragraph": 3},
                "expected_text": "🎯 Agenda",
                "expected_style": "Heading 1",
                "search_text": "🎯 ",
                "replacement_text": "",
            }
        ]
        replacement_request = Request(
            f"{base_url}/tools/replace_document_elements_live",
            data=json.dumps({"edits": edits, "dry_run": False}).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(replacement_request, timeout=2) as response:
            replacement_result = json.load(response)

        assert result == {
            "success": True,
            "query": "heading",
            "document_identifier": "file:///target",
            "max_results": 7,
        }
        assert heading_result == {
            "success": True,
            "query": "Agenda",
            "document_identifier": "file:///target",
            "max_results": 4,
            "matches": [],
        }
        assert styles_result == {
            "success": True,
            "query": "normal",
            "document_identifier": "file:///target",
            "max_results": 9,
            "styles": [{"name": "normal", "font_name": "Liberation Serif"}],
        }
        assert update_style_result == {
            "success": True,
            "property_name": "CharFontName",
            "value": "Calibri",
            "style_name": "normal",
            "location": None,
            "expected_text": None,
            "expected_style": None,
            "expected_current_value": "Liberation Serif",
            "document_identifier": "file:///target",
            "dry_run": False,
            "saved": False,
        }
        assert apply_format_result == {
            "success": True,
            "targets": targets,
            "property_name": "CharFontName",
            "value": "Calibri",
            "document_identifier": "file:///target",
            "dry_run": False,
            "saved": False,
        }
        assert replacement_result == {
            "success": True,
            "edits": edits,
            "document_identifier": None,
            "dry_run": False,
            "saved": False,
        }
    finally:
        interface.stop()
