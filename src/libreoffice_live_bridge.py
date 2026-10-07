"""Expose the LibreOffice extension's local REST tools over MCP stdio."""

import os
from typing import Any, Literal

import httpx
from mcp.server import MCPServer


BASE_URL = os.environ.get("LIBREOFFICE_MCP_URL", "http://localhost:8765").rstrip("/")
REQUEST_TIMEOUT = 10.0

mcp = MCPServer(
    "LibreOffice Live MCP",
    instructions=(
        "These tools operate on documents currently open in LibreOffice. "
        "The LibreOffice MCP extension must be running locally."
    ),
)


def _execute_tool(tool_name: str, parameters: dict[str, Any]) -> dict[str, Any]:
    """Forward a tool call to the REST API exposed by the LibreOffice extension."""
    try:
        response = httpx.post(
            f"{BASE_URL}/tools/{tool_name}",
            json=parameters,
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        return response.json()
    except httpx.HTTPError as exc:
        raise RuntimeError(
            f"Could not call LibreOffice at {BASE_URL}. "
            "Start the MCP extension in LibreOffice and check its status."
        ) from exc


@mcp.tool(description="Create a new Writer, Calc, Impress, or Draw document in LibreOffice.")
def create_document_live(
    doc_type: Literal["writer", "calc", "impress", "draw"] = "writer",
) -> dict[str, Any]:
    return _execute_tool("create_document_live", {"doc_type": doc_type})


@mcp.tool(description="Insert text into the currently active Writer document.")
def insert_text_live(text: str, position: int | None = None) -> dict[str, Any]:
    parameters: dict[str, Any] = {"text": text}
    if position is not None:
        parameters["position"] = position
    return _execute_tool("insert_text_live", parameters)


@mcp.tool(description="Get information about the currently active LibreOffice document.")
def get_document_info_live() -> dict[str, Any]:
    return _execute_tool("get_document_info_live", {})


@mcp.tool(description="Format the selected text in the active Writer document.")
def format_text_live(
    bold: bool | None = None,
    italic: bool | None = None,
    underline: bool | None = None,
    font_size: float | None = None,
    font_name: str | None = None,
) -> dict[str, Any]:
    parameters = {
        key: value
        for key, value in {
            "bold": bold,
            "italic": italic,
            "underline": underline,
            "font_size": font_size,
            "font_name": font_name,
        }.items()
        if value is not None
    }
    return _execute_tool("format_text_live", parameters)


@mcp.tool(description="Save the currently active LibreOffice document.")
def save_document_live(file_path: str | None = None) -> dict[str, Any]:
    parameters = {"file_path": file_path} if file_path is not None else {}
    return _execute_tool("save_document_live", parameters)


@mcp.tool(description="Export the currently active document to another format.")
def export_document_live(
    export_format: Literal["pdf", "docx", "doc", "odt", "txt", "rtf", "html"],
    file_path: str,
) -> dict[str, Any]:
    return _execute_tool(
        "export_document_live",
        {"export_format": export_format, "file_path": file_path},
    )


@mcp.tool(description="Read the text content of the currently active LibreOffice document.")
def get_text_content_live() -> dict[str, Any]:
    return _execute_tool("get_text_content_live", {})

@mcp.tool(
    description=(
        "Search an open Writer, Calc, Impress, or Draw document and return matching "
        "text elements with their locations and relevant formatting. Uses the active "
        "document by default and never opens, edits, or saves files."
    )
)
def search_document_elements_live(
    query: str,
    document_identifier: str | None = None,
    max_results: int = 100,
) -> dict[str, Any]:
    parameters: dict[str, Any] = {"query": query, "max_results": max_results}
    if document_identifier is not None:
        parameters["document_identifier"] = document_identifier
    return _execute_tool("search_document_elements_live", parameters)

@mcp.tool(
    description=(
        "List heading paragraphs in an already-open Writer document, optionally "
        "filtered by text. Returns body paragraph locations usable by the guarded "
        "replacement tool; does not edit or save."
    )
)
def search_document_headings_live(
    query: str | None = None,
    document_identifier: str | None = None,
    max_results: int = 100,
) -> dict[str, Any]:
    parameters: dict[str, Any] = {"max_results": max_results}
    if query is not None:
        parameters["query"] = query
    if document_identifier is not None:
        parameters["document_identifier"] = document_identifier
    return _execute_tool("search_document_headings_live", parameters)


@mcp.tool(
    description=(
        "Inspect exact paragraph style names and their default font and formatting "
        "in an already-open Writer document. Does not edit or save."
    )
)
def get_writer_paragraph_styles_live(
    query: str | None = None,
    document_identifier: str | None = None,
    max_results: int = 100,
) -> dict[str, Any]:
    parameters: dict[str, Any] = {"max_results": max_results}
    if query is not None:
        parameters["query"] = query
    if document_identifier is not None:
        parameters["document_identifier"] = document_identifier
    return _execute_tool("get_writer_paragraph_styles_live", parameters)


@mcp.tool(
    description=(
        "Preview or change one allowlisted property of an existing Writer paragraph "
        "style. Supports guarded style-name or paragraph-location targets, previews "
        "by default, and never saves."
    )
)
def update_writer_paragraph_style_live(
    property_name: Literal[
        "CharFontName",
        "CharHeight",
        "CharWeight",
        "CharPosture",
        "CharColor",
        "CharUnderline",
        "ParaAdjust",
        "ParaFirstLineIndent",
        "ParaLeftMargin",
        "ParaRightMargin",
        "ParaTopMargin",
        "ParaBottomMargin",
    ],
    value: str | float | int,
    style_name: str | None = None,
    location: dict[str, Any] | None = None,
    expected_text: str | None = None,
    expected_style: str | None = None,
    expected_current_value: str | float | int | None = None,
    document_identifier: str | None = None,
    dry_run: bool = True,
) -> dict[str, Any]:
    parameters: dict[str, Any] = {
        "property_name": property_name,
        "value": value,
        "dry_run": dry_run,
    }
    for key, option in {
        "style_name": style_name,
        "location": location,
        "expected_text": expected_text,
        "expected_style": expected_style,
        "expected_current_value": expected_current_value,
    }.items():
        if option is not None:
            parameters[key] = option
    if document_identifier is not None:
        parameters["document_identifier"] = document_identifier
    return _execute_tool("update_writer_paragraph_style_live", parameters)

@mcp.tool(
    description=(
        "Apply one allowlisted formatting property directly to guarded Writer body "
        "paragraphs. Preserves direct values by default; override_direct can replace "
        "direct values of only the selected property. Previews by default and never saves."
    )
)
def apply_writer_paragraph_formatting_live(
    targets: list[dict[str, Any]],
    property_name: Literal[
        "CharFontName",
        "CharHeight",
        "CharWeight",
        "CharPosture",
        "CharColor",
        "CharUnderline",
        "ParaAdjust",
        "ParaFirstLineIndent",
        "ParaLeftMargin",
        "ParaRightMargin",
        "ParaTopMargin",
        "ParaBottomMargin",
    ],
    value: str | float | int,
    document_identifier: str | None = None,
    dry_run: bool = True,
    override_direct: bool = False,
) -> dict[str, Any]:
    parameters: dict[str, Any] = {
        "targets": targets,
        "property_name": property_name,
        "value": value,
        "dry_run": dry_run,
    }
    if document_identifier is not None:
        parameters["document_identifier"] = document_identifier
    if override_direct:
        parameters["override_direct"] = True
    return _execute_tool("apply_writer_paragraph_formatting_live", parameters)


@mcp.tool(
    description=(
        "Replace exact substrings in open Writer body paragraphs after checking "
        "expected paragraph text and style. Previews by default and never saves."
    )
)
def replace_document_elements_live(
    edits: list[dict[str, Any]],
    document_identifier: str | None = None,
    dry_run: bool = True,
) -> dict[str, Any]:
    parameters: dict[str, Any] = {"edits": edits, "dry_run": dry_run}
    if document_identifier is not None:
        parameters["document_identifier"] = document_identifier
    return _execute_tool("replace_document_elements_live", parameters)


@mcp.tool(description="Read the text currently selected in the active Writer document.")
def get_selected_text_live() -> dict[str, Any]:
    return _execute_tool("get_selected_text_live", {})


@mcp.tool(
    description=(
        "Replace selected Writer text only if it exactly matches expected_text. "
        "Does not save the document."
    )
)
def replace_selected_text_live(
    expected_text: str,
    replacement_text: str,
) -> dict[str, Any]:
    return _execute_tool(
        "replace_selected_text_live",
        {
            "expected_text": expected_text,
            "replacement_text": replacement_text,
        },
    )


@mcp.tool(description="List the documents currently open in LibreOffice.")
def list_open_documents() -> dict[str, Any]:
    return _execute_tool("list_open_documents", {})


if __name__ == "__main__":
    mcp.run()
