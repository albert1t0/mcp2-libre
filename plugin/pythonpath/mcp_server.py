"""
LibreOffice MCP Extension - MCP Server Module

This module implements an embedded MCP server that integrates with LibreOffice
via the UNO API, providing real-time document manipulation capabilities.
"""

import asyncio
import json
import logging
from typing import Dict, Any, Optional, List
from .uno_bridge import UNOBridge

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LibreOfficeMCPServer:
    """Embedded MCP server for LibreOffice plugin"""
    
    def __init__(self):
        """Initialize the MCP server"""
        self.uno_bridge = UNOBridge()
        self.tools = {}
        self._register_tools()
        logger.info("LibreOffice MCP Server initialized")
    
    def _register_tools(self):
        """Register all available MCP tools"""
        
        # Document creation tools
        self.tools["create_document_live"] = {
            "description": "Create a new document in LibreOffice",
            "parameters": {
                "type": "object",
                "properties": {
                    "doc_type": {
                        "type": "string",
                        "enum": ["writer", "calc", "impress", "draw"],
                        "description": "Type of document to create",
                        "default": "writer"
                    }
                }
            },
            "handler": self.create_document_live
        }
        
        # Text manipulation tools
        self.tools["insert_text_live"] = {
            "description": "Insert text into the currently active document",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "Text to insert"
                    },
                    "position": {
                        "type": "integer",
                        "description": "Position to insert at (optional, defaults to cursor position)"
                    }
                },
                "required": ["text"]
            },
            "handler": self.insert_text_live
        }
        
        # Document info tools
        self.tools["get_document_info_live"] = {
            "description": "Get information about the currently active document",
            "parameters": {
                "type": "object",
                "properties": {}
            },
            "handler": self.get_document_info_live
        }
        
        # Text formatting tools
        self.tools["format_text_live"] = {
            "description": "Apply formatting to selected text in active document",
            "parameters": {
                "type": "object",
                "properties": {
                    "bold": {
                        "type": "boolean",
                        "description": "Apply bold formatting"
                    },
                    "italic": {
                        "type": "boolean",
                        "description": "Apply italic formatting"
                    },
                    "underline": {
                        "type": "boolean",
                        "description": "Apply underline formatting"
                    },
                    "font_size": {
                        "type": "number",
                        "description": "Font size in points"
                    },
                    "font_name": {
                        "type": "string",
                        "description": "Font family name"
                    }
                }
            },
            "handler": self.format_text_live
        }
        
        # Document saving tools
        self.tools["save_document_live"] = {
            "description": "Save the currently active document",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to save document to (optional, saves to current location if not specified)"
                    }
                }
            },
            "handler": self.save_document_live
        }
        
        # Document export tools
        self.tools["export_document_live"] = {
            "description": "Export the currently active document to a different format",
            "parameters": {
                "type": "object",
                "properties": {
                    "export_format": {
                        "type": "string",
                        "enum": ["pdf", "docx", "doc", "odt", "txt", "rtf", "html"],
                        "description": "Format to export to"
                    },
                    "file_path": {
                        "type": "string",
                        "description": "Path to export document to"
                    }
                },
                "required": ["export_format", "file_path"]
            },
            "handler": self.export_document_live
        }
        
        # Content reading tools
        self.tools["get_text_content_live"] = {
            "description": "Get the text content of the currently active document",
            "parameters": {
                "type": "object",
                "properties": {}
            },
            "handler": self.get_text_content_live
        }
        self.tools["search_document_elements_live"] = {
            "description": (
                "Search an open Writer, Calc, Impress, or Draw document and return "
                "matching text elements with location and relevant formatting. "
                "Uses the active document by default; never opens, edits, or saves files."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Case-insensitive text to search for"
                    },
                    "document_identifier": {
                        "type": "string",
                        "description": (
                            "Exact title or URL of an already-open document; "
                            "omit to use the active document"
                        )
                    },
                    "max_results": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 500,
                        "default": 100,
                        "description": "Maximum matching elements to return"
                    }
                },
                "required": ["query"]
            },
            "handler": self.search_document_elements_live
        }

        self.tools["search_document_headings_live"] = {
            "description": (
                "List heading paragraphs in an already-open Writer document, optionally "
                "filtered by text. Results include paragraph locations usable by the "
                "guarded replacement tool; this tool never edits or saves."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Optional case-insensitive text filter",
                    },
                    "document_identifier": {
                        "type": "string",
                        "description": (
                            "Exact title or URL of an already-open document; "
                            "omit to use the active document"
                        ),
                    },
                    "max_results": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 500,
                        "default": 100,
                        "description": "Maximum heading paragraphs to return",
                    },
                },
            },
            "handler": self.search_document_headings_live,
        }

        self.tools["get_writer_paragraph_styles_live"] = {
            "description": (
                "Inspect existing paragraph styles in an already-open Writer document, "
                "including their default font, size, and character formatting. "
                "This tool never edits or saves."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Optional case-insensitive style-name filter",
                    },
                    "document_identifier": {
                        "type": "string",
                        "description": (
                            "Exact title or URL of an already-open document; "
                            "omit to use the active document"
                        ),
                    },
                    "max_results": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 500,
                        "default": 100,
                        "description": "Maximum paragraph styles to return",
                    },
                },
            },
            "handler": self.get_writer_paragraph_styles_live,
        }

        self.tools["update_writer_paragraph_style_live"] = {
            "description": (
                "Preview or change one allowlisted property of an existing Writer "
                "paragraph style. Target by exact style name or by a guarded body "
                "paragraph location. Reports inherited descendant styles affected, "
                "previews by default, and never saves."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "property_name": {
                        "type": "string",
                        "enum": list(UNOBridge.STYLE_ATTRIBUTE_SPECS),
                        "description": "Allowlisted UNO style property to update",
                    },
                    "value": {
                        "anyOf": [
                            {"type": "string"},
                            {"type": "number"},
                            {"type": "integer"},
                        ],
                        "description": "New value, validated against the UNO property type",
                    },
                    "style_name": {
                        "type": "string",
                        "minLength": 1,
                        "description": (
                            "Exact existing paragraph style name. Provide this or "
                            "location, but not both."
                        ),
                    },
                    "location": {
                        "type": "object",
                        "properties": {
                            "section": {"type": "string", "enum": ["body"]},
                            "paragraph": {"type": "integer", "minimum": 1},
                        },
                        "required": ["section", "paragraph"],
                        "description": (
                            "Resolve the paragraph's shared style; requires "
                            "expected_text and expected_style guards"
                        ),
                    },
                    "expected_text": {
                        "type": "string",
                        "description": "Exact current paragraph text when targeting by location",
                    },
                    "expected_style": {
                        "type": "string",
                        "description": "Exact current paragraph style when targeting by location",
                    },
                    "expected_current_value": {
                        "anyOf": [
                            {"type": "string"},
                            {"type": "number"},
                            {"type": "integer"},
                        ],
                        "description": "Optional guard for the current property value",
                    },
                    "document_identifier": {
                        "type": "string",
                        "description": (
                            "Exact title or URL of an already-open document; "
                            "omit to use the active document"
                        ),
                    },
                    "dry_run": {
                        "type": "boolean",
                        "default": True,
                        "description": (
                            "Preview the style change without modifying the document"
                        ),
                    },
                },
                "required": ["property_name", "value"],
                "oneOf": [
                    {
                        "required": ["style_name"],
                        "not": {"required": ["location"]},
                    },
                    {
                        "required": ["location", "expected_text", "expected_style"],
                        "not": {"required": ["style_name"]},
                    },
                ],
            },
            "handler": self.update_writer_paragraph_style_live,
        }
        self.tools["apply_writer_paragraph_formatting_live"] = {
            "description": (
                "Apply one allowlisted formatting property directly to guarded body "
                "paragraphs. Uses exact expected text and style, preserves direct "
                "formatting by default, optionally overrides direct values for only "
                "the named property, previews by default, and never saves."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "targets": {
                        "type": "array",
                        "minItems": 1,
                        "maxItems": 500,
                        "items": {
                            "type": "object",
                            "properties": {
                                "location": {
                                    "type": "object",
                                    "properties": {
                                        "section": {
                                            "type": "string",
                                            "enum": ["body"],
                                        },
                                        "paragraph": {
                                            "type": "integer",
                                            "minimum": 1,
                                        },
                                    },
                                    "required": ["section", "paragraph"],
                                },
                                "expected_text": {
                                    "type": "string",
                                    "description": "Exact current paragraph text",
                                },
                                "expected_style": {
                                    "type": "string",
                                    "description": "Exact current paragraph style",
                                },
                            },
                            "required": [
                                "location",
                                "expected_text",
                                "expected_style",
                            ],
                        },
                    },
                    "property_name": {
                        "type": "string",
                        "enum": list(UNOBridge.STYLE_ATTRIBUTE_SPECS),
                    },
                    "value": {
                        "anyOf": [
                            {"type": "string"},
                            {"type": "number"},
                            {"type": "integer"},
                        ],
                        "description": "New value, validated against the UNO property type",
                    },
                    "document_identifier": {
                        "type": "string",
                        "description": (
                            "Exact title or URL of an already-open document; "
                            "omit to use the active document"
                        ),
                    },
                    "dry_run": {
                        "type": "boolean",
                        "default": True,
                    },
                    "override_direct": {
                        "type": "boolean",
                        "default": False,
                        "description": (
                            "When true, also replace direct values of property_name; "
                            "other formatting properties are left unchanged"
                        ),
                    },
                },
                "required": ["targets", "property_name", "value"],
            },
            "handler": self.apply_writer_paragraph_formatting_live,
        }

        self.tools["replace_document_elements_live"] = {
            "description": (
                "Replace exact substrings in body paragraphs of an already-open Writer "
                "document. Every edit must match the paragraph's expected full text and "
                "style; all edits are preflighted before mutation. Dry-run is enabled by "
                "default and the document is never saved automatically."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "edits": {
                        "type": "array",
                        "minItems": 1,
                        "maxItems": 500,
                        "items": {
                            "type": "object",
                            "properties": {
                                "location": {
                                    "type": "object",
                                    "properties": {
                                        "section": {
                                            "type": "string",
                                            "enum": ["body"],
                                        },
                                        "paragraph": {
                                            "type": "integer",
                                            "minimum": 1,
                                        },
                                    },
                                    "required": ["section", "paragraph"],
                                },
                                "expected_text": {
                                    "type": "string",
                                    "description": "Exact current full paragraph text",
                                },
                                "expected_style": {
                                    "type": "string",
                                    "description": "Exact current paragraph style",
                                },
                                "search_text": {
                                    "type": "string",
                                    "minLength": 1,
                                    "description": (
                                        "Exact substring, which must occur once in "
                                        "expected_text"
                                    ),
                                },
                                "replacement_text": {
                                    "type": "string",
                                    "description": "Text to insert in place of search_text",
                                },
                            },
                            "required": [
                                "location",
                                "expected_text",
                                "expected_style",
                                "search_text",
                                "replacement_text",
                            ],
                        },
                    },
                    "document_identifier": {
                        "type": "string",
                        "description": (
                            "Exact title or URL of an already-open document; "
                            "omit to use the active document"
                        ),
                    },
                    "dry_run": {
                        "type": "boolean",
                        "default": True,
                        "description": "Preview the batch without changing document text",
                    },
                },
                "required": ["edits"],
            },
            "handler": self.replace_document_elements_live,
        }

        self.tools["get_selected_text_live"] = {
            "description": "Get the text selected in the active Writer document",
            "parameters": {
                "type": "object",
                "properties": {}
            },
            "handler": self.get_selected_text_live
        }

        self.tools["replace_selected_text_live"] = {
            "description": (
                "Replace the selected Writer text only if it exactly matches "
                "expected_text. Does not save the document."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "expected_text": {
                        "type": "string",
                        "description": "Exact selected text that was previously reviewed"
                    },
                    "replacement_text": {
                        "type": "string",
                        "description": "Text to replace the current selection with"
                    }
                },
                "required": ["expected_text", "replacement_text"]
            },
            "handler": self.replace_selected_text_live
        }
        
        # Document list tools
        self.tools["list_open_documents"] = {
            "description": "List all currently open documents in LibreOffice",
            "parameters": {
                "type": "object",
                "properties": {}
            },
            "handler": self.list_open_documents
        }
        
        logger.info(f"Registered {len(self.tools)} MCP tools")
    
    async def execute_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute an MCP tool
        
        Args:
            tool_name: Name of the tool to execute
            parameters: Parameters for the tool
            
        Returns:
            Result dictionary
        """
        try:
            if tool_name not in self.tools:
                return {
                    "success": False,
                    "error": f"Unknown tool: {tool_name}",
                    "available_tools": list(self.tools.keys())
                }
            
            tool = self.tools[tool_name]
            handler = tool["handler"]
            
            # Execute the tool handler
            result = handler(**parameters)
            
            logger.info(f"Executed tool '{tool_name}' successfully")
            return result
            
        except Exception as e:
            logger.error(f"Error executing tool '{tool_name}': {e}")
            return {
                "success": False,
                "error": str(e),
                "tool": tool_name,
                "parameters": parameters
            }
    
    def get_tool_list(self) -> List[Dict[str, Any]]:
        """Get list of available tools with their descriptions"""
        return [
            {
                "name": name,
                "description": tool["description"],
                "parameters": tool["parameters"]
            }
            for name, tool in self.tools.items()
        ]
    
    # Tool handler methods
    
    def create_document_live(self, doc_type: str = "writer") -> Dict[str, Any]:
        """Create a new document in LibreOffice"""
        try:
            doc = self.uno_bridge.create_document(doc_type)
            doc_info = self.uno_bridge.get_document_info(doc)
            
            return {
                "success": True,
                "message": f"Created new {doc_type} document",
                "document_info": doc_info
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def insert_text_live(self, text: str, position: Optional[int] = None) -> Dict[str, Any]:
        """Insert text into the currently active document"""
        return self.uno_bridge.insert_text(text, position)
    
    def get_document_info_live(self) -> Dict[str, Any]:
        """Get information about the currently active document"""
        doc_info = self.uno_bridge.get_document_info()
        if "error" in doc_info:
            return {"success": False, **doc_info}
        else:
            return {"success": True, "document_info": doc_info}
    
    def format_text_live(self, **formatting) -> Dict[str, Any]:
        """Apply formatting to selected text"""
        return self.uno_bridge.format_text(formatting)
    
    def save_document_live(self, file_path: Optional[str] = None) -> Dict[str, Any]:
        """Save the currently active document"""
        return self.uno_bridge.save_document(file_path=file_path)
    
    def export_document_live(self, export_format: str, file_path: str) -> Dict[str, Any]:
        """Export the currently active document"""
        return self.uno_bridge.export_document(export_format, file_path)
    
    def get_text_content_live(self) -> Dict[str, Any]:
        """Get text content of the currently active document"""
        return self.uno_bridge.get_text_content()
    def search_document_elements_live(
        self,
        query: str,
        document_identifier: Optional[str] = None,
        max_results: int = 100,
    ) -> Dict[str, Any]:
        """Search an open document and inspect matching elements."""
        return self.uno_bridge.search_document_elements(
            query=query,
            document_identifier=document_identifier,
            max_results=max_results,
        )
    def search_document_headings_live(
        self,
        query: Optional[str] = None,
        document_identifier: Optional[str] = None,
        max_results: int = 100,
    ) -> Dict[str, Any]:
        """List heading paragraphs in an already-open Writer document."""
        return self.uno_bridge.search_document_headings(
            query=query,
            document_identifier=document_identifier,
            max_results=max_results,
        )

    def get_writer_paragraph_styles_live(
        self,
        query: Optional[str] = None,
        document_identifier: Optional[str] = None,
        max_results: int = 100,
    ) -> Dict[str, Any]:
        """Inspect existing paragraph styles in an open Writer document."""
        return self.uno_bridge.get_writer_paragraph_styles(
            query=query,
            document_identifier=document_identifier,
            max_results=max_results,
        )

    def update_writer_paragraph_style_live(
        self,
        property_name: str,
        value: Any,
        style_name: Optional[str] = None,
        location: Optional[Dict[str, Any]] = None,
        expected_text: Optional[str] = None,
        expected_style: Optional[str] = None,
        expected_current_value: Any = None,
        document_identifier: Optional[str] = None,
        dry_run: bool = True,
    ) -> Dict[str, Any]:
        """Preview or update one allowlisted Writer paragraph style property."""
        return self.uno_bridge.update_writer_paragraph_style(
            property_name=property_name,
            value=value,
            style_name=style_name,
            location=location,
            expected_text=expected_text,
            expected_style=expected_style,
            expected_current_value=expected_current_value,
            document_identifier=document_identifier,
            dry_run=dry_run,
        )
    def apply_writer_paragraph_formatting_live(
        self,
        targets: List[Dict[str, Any]],
        property_name: str,
        value: Any,
        document_identifier: Optional[str] = None,
        dry_run: bool = True,
        override_direct: bool = False,
    ) -> Dict[str, Any]:
        """Preview or apply one property to guarded paragraphs."""
        return self.uno_bridge.apply_writer_paragraph_formatting(
            targets=targets,
            property_name=property_name,
            value=value,
            document_identifier=document_identifier,
            dry_run=dry_run,
            override_direct=override_direct,
        )

    def replace_document_elements_live(
        self,
        edits: List[Dict[str, Any]],
        document_identifier: Optional[str] = None,
        dry_run: bool = True,
    ) -> Dict[str, Any]:
        """Replace guarded Writer text ranges without saving the document."""
        return self.uno_bridge.replace_document_elements(
            edits=edits,
            document_identifier=document_identifier,
            dry_run=dry_run,
        )

    def get_selected_text_live(self) -> Dict[str, Any]:
        """Get text selected in the active Writer document."""
        return self.uno_bridge.get_selected_text()

    def replace_selected_text_live(
        self, expected_text: str, replacement_text: str
    ) -> Dict[str, Any]:
        """Replace selected text if it has not changed since it was read."""
        return self.uno_bridge.replace_selected_text(
            expected_text=expected_text,
            replacement_text=replacement_text,
        )
    
    def list_open_documents(self) -> Dict[str, Any]:
        """List all open documents in LibreOffice"""
        try:
            desktop = self.uno_bridge.desktop
            documents = []
            
            # Get all open documents
            frames = desktop.getFrames()
            for i in range(frames.getCount()):
                frame = frames.getByIndex(i)
                controller = frame.getController()
                if controller:
                    doc = controller.getModel()
                    if doc:
                        doc_info = self.uno_bridge.get_document_info(doc)
                        documents.append(doc_info)
            
            return {
                "success": True,
                "documents": documents,
                "count": len(documents)
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}


# Global instance
mcp_server = None

def get_mcp_server() -> LibreOfficeMCPServer:
    """Get or create the global MCP server instance"""
    global mcp_server
    if mcp_server is None:
        mcp_server = LibreOfficeMCPServer()
    return mcp_server
