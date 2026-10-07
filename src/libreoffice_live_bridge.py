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


@mcp.tool(description="List the documents currently open in LibreOffice.")
def list_open_documents() -> dict[str, Any]:
    return _execute_tool("list_open_documents", {})


if __name__ == "__main__":
    mcp.run()
