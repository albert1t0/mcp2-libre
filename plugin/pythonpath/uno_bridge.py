"""
LibreOffice MCP Extension - UNO Bridge Module

This module provides a bridge between MCP operations and LibreOffice UNO API,
enabling direct manipulation of LibreOffice documents.
"""

import uno
import unohelper
from com.sun.star.beans import PropertyValue
from com.sun.star.document import XDocumentEventListener
from com.sun.star.awt import XActionListener
from typing import Any, Optional, Dict, List
import logging
import traceback

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class UNOBridge:
    """Bridge between MCP operations and LibreOffice UNO API"""
    MAX_CALC_CELLS_TO_SCAN = 100000
    MAX_SEARCH_RESULTS = 500
    
    def __init__(self):
        """Initialize the UNO bridge"""
        try:
            self.ctx = uno.getComponentContext()
            self.smgr = self.ctx.ServiceManager
            self.desktop = self.smgr.createInstanceWithContext(
                "com.sun.star.frame.Desktop", self.ctx)
            logger.info("UNO Bridge initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize UNO Bridge: {e}")
            raise
    
    def create_document(self, doc_type: str = "writer") -> Any:
        """
        Create new document using UNO API
        
        Args:
            doc_type: Type of document ('writer', 'calc', 'impress', 'draw')
            
        Returns:
            Document object
        """
        try:
            url_map = {
                "writer": "private:factory/swriter",
                "calc": "private:factory/scalc", 
                "impress": "private:factory/simpress",
                "draw": "private:factory/sdraw"
            }
            
            url = url_map.get(doc_type, "private:factory/swriter")
            doc = self.desktop.loadComponentFromURL(url, "_blank", 0, ())
            logger.info(f"Created new {doc_type} document")
            return doc
            
        except Exception as e:
            logger.error(f"Failed to create document: {e}")
            raise
    
    def get_active_document(self) -> Optional[Any]:
        """Get currently active document"""
        try:
            doc = self.desktop.getCurrentComponent()
            if doc:
                logger.info("Retrieved active document")
            return doc
        except Exception as e:
            logger.error(f"Failed to get active document: {e}")
            return None
    
    def get_document_info(self, doc: Any = None) -> Dict[str, Any]:
        """Get information about a document"""
        try:
            if doc is None:
                doc = self.get_active_document()
            
            if not doc:
                return {"error": "No document available"}
            
            info = {
                "title": getattr(doc, 'Title', 'Unknown') if hasattr(doc, 'Title') else "Unknown",
                "url": doc.getURL() if hasattr(doc, 'getURL') else "",
                "modified": doc.isModified() if hasattr(doc, 'isModified') else False,
                "type": self._get_document_type(doc),
                "has_selection": self._has_selection(doc)
            }
            
            # Add document-specific information
            if doc.supportsService("com.sun.star.text.TextDocument"):
                text = doc.getText()
                info["word_count"] = len(text.getString().split())
                info["character_count"] = len(text.getString())
            elif doc.supportsService("com.sun.star.sheet.SpreadsheetDocument"):
                sheets = doc.getSheets()
                info["sheet_count"] = sheets.getCount()
                info["sheet_names"] = [sheets.getByIndex(i).getName() 
                                     for i in range(sheets.getCount())]
            
            return info
            
        except Exception as e:
            logger.error(f"Failed to get document info: {e}")
            return {"error": str(e)}
    
    def insert_text(self, text: str, position: Optional[int] = None, doc: Any = None) -> Dict[str, Any]:
        """
        Insert text into a document
        
        Args:
            text: Text to insert
            position: Position to insert at (None for current cursor position)
            doc: Document to insert into (None for active document)
            
        Returns:
            Result dictionary
        """
        try:
            if doc is None:
                doc = self.get_active_document()
            
            if not doc:
                return {"success": False, "error": "No active document"}
            
            # Handle Writer documents
            if doc.supportsService("com.sun.star.text.TextDocument"):
                text_obj = doc.getText()
                
                if position is None:
                    # Insert at current cursor position
                    cursor = doc.getCurrentController().getViewCursor()
                else:
                    # Insert at specific position
                    cursor = text_obj.createTextCursor()
                    cursor.gotoStart(False)
                    cursor.goRight(position, False)
                
                text_obj.insertString(cursor, text, False)
                logger.info(f"Inserted {len(text)} characters into Writer document")
                return {"success": True, "message": f"Inserted {len(text)} characters"}
            
            # Handle other document types
            else:
                return {"success": False, "error": f"Text insertion not supported for {self._get_document_type(doc)}"}
                
        except Exception as e:
            logger.error(f"Failed to insert text: {e}")
            return {"success": False, "error": str(e)}
    
    def format_text(self, formatting: Dict[str, Any], doc: Any = None) -> Dict[str, Any]:
        """
        Apply formatting to selected text
        
        Args:
            formatting: Dictionary of formatting options
            doc: Document to format (None for active document)
            
        Returns:
            Result dictionary
        """
        try:
            if doc is None:
                doc = self.get_active_document()
            
            if not doc or not doc.supportsService("com.sun.star.text.TextDocument"):
                return {"success": False, "error": "No Writer document available"}
            
            # Get current selection
            selection = doc.getCurrentController().getSelection()
            if selection.getCount() == 0:
                return {"success": False, "error": "No text selected"}
            
            # Apply formatting to selection
            text_range = selection.getByIndex(0)
            
            # Apply various formatting options
            if "bold" in formatting:
                text_range.CharWeight = 150.0 if formatting["bold"] else 100.0
            
            if "italic" in formatting:
                text_range.CharPosture = 2 if formatting["italic"] else 0
            
            if "underline" in formatting:
                text_range.CharUnderline = 1 if formatting["underline"] else 0
            
            if "font_size" in formatting:
                text_range.CharHeight = formatting["font_size"]
            
            if "font_name" in formatting:
                text_range.CharFontName = formatting["font_name"]
            
            logger.info("Applied formatting to selected text")
            return {"success": True, "message": "Formatting applied successfully"}
            
        except Exception as e:
            logger.error(f"Failed to format text: {e}")
            return {"success": False, "error": str(e)}
    
    def save_document(self, doc: Any = None, file_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Save a document
        
        Args:
            doc: Document to save (None for active document)
            file_path: Path to save to (None to save to current location)
            
        Returns:
            Result dictionary
        """
        try:
            if doc is None:
                doc = self.get_active_document()
            
            if not doc:
                return {"success": False, "error": "No document to save"}
            
            if file_path:
                # Save as new file
                url = uno.systemPathToFileUrl(file_path)
                doc.storeAsURL(url, ())
                logger.info(f"Saved document to {file_path}")
                return {"success": True, "message": f"Document saved to {file_path}"}
            else:
                # Save to current location
                if doc.hasLocation():
                    doc.store()
                    logger.info("Saved document to current location")
                    return {"success": True, "message": "Document saved"}
                else:
                    return {"success": False, "error": "Document has no location, specify file_path"}
                    
        except Exception as e:
            logger.error(f"Failed to save document: {e}")
            return {"success": False, "error": str(e)}
    
    def export_document(self, export_format: str, file_path: str, doc: Any = None) -> Dict[str, Any]:
        """
        Export document to different format
        
        Args:
            export_format: Target format ('pdf', 'docx', 'odt', 'txt', etc.)
            file_path: Path to export to
            doc: Document to export (None for active document)
            
        Returns:
            Result dictionary
        """
        try:
            if doc is None:
                doc = self.get_active_document()
            
            if not doc:
                return {"success": False, "error": "No document to export"}
            
            # Filter map for different formats
            filter_map = {
                'pdf': 'writer_pdf_Export',
                'docx': 'MS Word 2007 XML',
                'doc': 'MS Word 97',
                'odt': 'writer8',
                'txt': 'Text',
                'rtf': 'Rich Text Format',
                'html': 'HTML (StarWriter)'
            }
            
            filter_name = filter_map.get(export_format.lower())
            if not filter_name:
                return {"success": False, "error": f"Unsupported export format: {export_format}"}
            
            # Prepare export properties
            properties = (
                PropertyValue("FilterName", 0, filter_name, 0),
                PropertyValue("Overwrite", 0, True, 0),
            )
            
            # Export document
            url = uno.systemPathToFileUrl(file_path)
            doc.storeToURL(url, properties)
            
            logger.info(f"Exported document to {file_path} as {export_format}")
            return {"success": True, "message": f"Document exported to {file_path}"}
            
        except Exception as e:
            logger.error(f"Failed to export document: {e}")
            return {"success": False, "error": str(e)}

    def _get_selected_text_range(self, doc: Any = None) -> tuple[Any, str]:
        """Return the sole non-empty Writer text selection."""
        if doc is None:
            doc = self.get_active_document()

        if not doc or not doc.supportsService("com.sun.star.text.TextDocument"):
            raise ValueError("No active Writer document")

        selection = doc.getCurrentController().getSelection()
        if callable(getattr(selection, "getString", None)):
            text_range = selection
        elif (
            callable(getattr(selection, "getCount", None))
            and callable(getattr(selection, "getByIndex", None))
        ):
            selection_count = selection.getCount()
            if selection_count == 0:
                raise ValueError("No text is selected")
            if selection_count != 1:
                raise ValueError("Select exactly one text range")
            text_range = selection.getByIndex(0)
        else:
            raise ValueError("The current selection is not a text range")

        get_string = getattr(text_range, "getString", None)
        if not callable(get_string):
            raise ValueError("The current selection is not a text range")

        selected_text = get_string()
        if not isinstance(selected_text, str) or selected_text == "":
            raise ValueError("No text is selected")

        return text_range, selected_text

    def get_selected_text(self, doc: Any = None) -> Dict[str, Any]:
        """Get the text currently selected in the active Writer document."""
        try:
            _, selected_text = self._get_selected_text_range(doc)
            return {"success": True, "text": selected_text}
        except Exception as e:
            logger.error(f"Failed to read selected text: {e}")
            return {"success": False, "error": str(e)}

    def replace_selected_text(
        self,
        expected_text: str,
        replacement_text: str,
        doc: Any = None,
    ) -> Dict[str, Any]:
        """Replace the current selection only if it still matches expected_text."""
        try:
            if not isinstance(expected_text, str) or not isinstance(replacement_text, str):
                return {
                    "success": False,
                    "error": "expected_text and replacement_text must be strings",
                }

            text_range, selected_text = self._get_selected_text_range(doc)
            if selected_text != expected_text:
                return {
                    "success": False,
                    "error": "Selected text does not match expected_text; no changes made",
                }

            set_string = getattr(text_range, "setString", None)
            if not callable(set_string):
                return {
                    "success": False,
                    "error": "The selected text cannot be replaced",
                }

            set_string(replacement_text)
            return {
                "success": True,
                "replaced_characters": len(selected_text),
                "inserted_characters": len(replacement_text),
            }
        except Exception as e:
            logger.error(f"Failed to replace selected text: {e}")
            return {"success": False, "error": str(e)}
    
    def get_text_content(self, doc: Any = None) -> Dict[str, Any]:
        """Get text content from a document"""
        try:
            if doc is None:
                doc = self.get_active_document()
            
            if not doc:
                return {"success": False, "error": "No document available"}
            
            if doc.supportsService("com.sun.star.text.TextDocument"):
                text = doc.getText().getString()
                return {"success": True, "content": text, "length": len(text)}
            else:
                return {"success": False, "error": f"Text extraction not supported for {self._get_document_type(doc)}"}
                
        except Exception as e:
            logger.error(f"Failed to get text content: {e}")
            return {"success": False, "error": str(e)}

    def search_document_headings(
        self,
        query: Optional[str] = None,
        document_identifier: Optional[str] = None,
        max_results: int = 100,
    ) -> Dict[str, Any]:
        """List headings in an already-open Writer document, optionally filtered by text."""
        if query is not None and (not isinstance(query, str) or not query):
            return {
                "success": False,
                "error": "query must be a non-empty string when provided",
            }
        if (
            isinstance(max_results, bool)
            or not isinstance(max_results, int)
            or max_results < 1
            or max_results > self.MAX_SEARCH_RESULTS
        ):
            return {
                "success": False,
                "error": f"max_results must be an integer from 1 to {self.MAX_SEARCH_RESULTS}",
            }

        doc, error = self._resolve_search_document(document_identifier)
        if error:
            return {"success": False, "error": error}

        try:
            doc_type = self._get_document_type(doc)
            if doc_type != "writer":
                return {
                    "success": False,
                    "error": "Heading search is only supported for Writer documents",
                }

            folded_query = query.casefold() if query is not None else None
            matches = []
            truncated = False
            for paragraph_index, element, text_value in self._writer_body_paragraphs(doc):
                style = self._property(element, "ParaStyleName")
                outline_level = self._property(element, "OutlineLevel")
                if not self._is_writer_heading(style, outline_level):
                    continue
                if folded_query is not None and folded_query not in text_value.casefold():
                    continue
                if len(matches) >= max_results:
                    truncated = True
                    break

                formatting = {}
                if style is not None:
                    formatting["style"] = self._json_value(style)
                if outline_level is not None:
                    formatting["outline_level"] = self._json_value(outline_level)
                alignment = self._property(element, "ParaAdjust")
                if alignment is not None:
                    formatting["alignment"] = self._json_value(alignment)
                character_defaults = self._formatting_metadata(element)
                if character_defaults:
                    formatting["character_defaults"] = character_defaults

                match = {
                    "element_type": "paragraph",
                    "text": text_value,
                    "location": {
                        "section": "body",
                        "paragraph": paragraph_index,
                    },
                    "formatting": formatting,
                }
                runs = self._text_runs(element)
                if runs:
                    match["runs"] = runs
                matches.append(match)

            return {
                "success": True,
                "document": {
                    "title": self._document_title(doc),
                    "url": self._document_url(doc),
                    "type": doc_type,
                },
                "query": query,
                "matches": matches,
                "count": len(matches),
                "truncated": truncated,
            }
        except Exception as e:
            logger.error(f"Failed to search document headings: {e}")
            return {"success": False, "error": str(e)}

    def replace_document_elements(
        self,
        edits: List[Dict[str, Any]],
        document_identifier: Optional[str] = None,
        dry_run: bool = True,
    ) -> Dict[str, Any]:
        """Replace exact text ranges in body paragraphs after validating the full batch."""
        if not isinstance(edits, list) or not edits:
            return {"success": False, "error": "edits must be a non-empty array"}
        if len(edits) > self.MAX_SEARCH_RESULTS:
            return {
                "success": False,
                "error": f"edits cannot contain more than {self.MAX_SEARCH_RESULTS} items",
            }
        if not isinstance(dry_run, bool):
            return {"success": False, "error": "dry_run must be a boolean"}

        validation_errors = []
        normalized_edits = []
        seen_locations = set()
        required_fields = (
            "location",
            "expected_text",
            "expected_style",
            "search_text",
            "replacement_text",
        )
        for edit_index, edit in enumerate(edits):
            if not isinstance(edit, dict):
                validation_errors.append(
                    {"edit_index": edit_index, "error": "each edit must be an object"}
                )
                continue
            missing = [field for field in required_fields if field not in edit]
            if missing:
                validation_errors.append(
                    {
                        "edit_index": edit_index,
                        "error": f"missing required fields: {', '.join(missing)}",
                    }
                )
                continue

            location = edit["location"]
            if (
                not isinstance(location, dict)
                or location.get("section") != "body"
                or isinstance(location.get("paragraph"), bool)
                or not isinstance(location.get("paragraph"), int)
                or location["paragraph"] < 1
            ):
                validation_errors.append(
                    {
                        "edit_index": edit_index,
                        "error": "location must identify a body paragraph with a positive paragraph number",
                    }
                )
                continue

            string_fields = (
                "expected_text",
                "expected_style",
                "search_text",
                "replacement_text",
            )
            invalid_fields = [
                field for field in string_fields if not isinstance(edit[field], str)
            ]
            if invalid_fields:
                validation_errors.append(
                    {
                        "edit_index": edit_index,
                        "error": f"these fields must be strings: {', '.join(invalid_fields)}",
                    }
                )
                continue
            if not edit["expected_style"]:
                validation_errors.append(
                    {"edit_index": edit_index, "error": "expected_style must not be empty"}
                )
                continue
            if not edit["search_text"]:
                validation_errors.append(
                    {"edit_index": edit_index, "error": "search_text must not be empty"}
                )
                continue
            target_number = location["paragraph"]
            if target_number in seen_locations:
                validation_errors.append(
                    {
                        "edit_index": edit_index,
                        "error": "only one edit per paragraph is allowed in a batch",
                    }
                )
                continue
            seen_locations.add(target_number)

            expected_text = edit["expected_text"]
            search_text = edit["search_text"]
            if expected_text.count(search_text) != 1:
                validation_errors.append(
                    {
                        "edit_index": edit_index,
                        "error": "search_text must occur exactly once in expected_text",
                    }
                )
                continue
            normalized_edits.append(
                {
                    "edit_index": edit_index,
                    "paragraph": target_number,
                    "location": {
                        "section": "body",
                        "paragraph": target_number,
                    },
                    "expected_text": expected_text,
                    "expected_style": edit["expected_style"],
                    "search_text": search_text,
                    "replacement_text": edit["replacement_text"],
                    "offset": expected_text.index(search_text),
                }
            )

        if validation_errors:
            return {
                "success": False,
                "error": "Batch validation failed; no changes made",
                "errors": validation_errors,
            }

        doc, error = self._resolve_search_document(document_identifier)
        if error:
            return {"success": False, "error": error}
        try:
            doc_type = self._get_document_type(doc)
            if doc_type != "writer":
                return {
                    "success": False,
                    "error": "Batch text replacement is only supported for Writer documents",
                }

            paragraphs = {
                paragraph_index: (element, text_value)
                for paragraph_index, element, text_value in self._writer_body_paragraphs(doc)
            }
            prepared_edits = []
            preflight_errors = []
            for edit in normalized_edits:
                edit_index = edit["edit_index"]
                paragraph_entry = paragraphs.get(edit["paragraph"])
                if paragraph_entry is None:
                    preflight_errors.append(
                        {
                            "edit_index": edit_index,
                            "error": "target paragraph no longer exists",
                        }
                    )
                    continue

                element, current_text = paragraph_entry
                if current_text != edit["expected_text"]:
                    preflight_errors.append(
                        {
                            "edit_index": edit_index,
                            "error": "paragraph text no longer matches expected_text",
                        }
                    )
                    continue
                current_style = self._property(element, "ParaStyleName")
                if current_style != edit["expected_style"]:
                    preflight_errors.append(
                        {
                            "edit_index": edit_index,
                            "error": "paragraph style no longer matches expected_style",
                        }
                    )
                    continue

                try:
                    cursor = self._select_writer_substring(
                        element, edit["offset"], edit["search_text"]
                    )
                except Exception as cursor_error:
                    preflight_errors.append(
                        {
                            "edit_index": edit_index,
                            "error": f"could not verify target text range: {cursor_error}",
                        }
                    )
                    continue
                prepared_edits.append(
                    {
                        **edit,
                        "cursor": cursor,
                        "before": current_text,
                        "after": current_text.replace(
                            edit["search_text"], edit["replacement_text"], 1
                        ),
                    }
                )

            if preflight_errors:
                return {
                    "success": False,
                    "error": "Batch preflight failed; no changes made",
                    "errors": preflight_errors,
                }

            if not dry_run:
                for edit in sorted(
                    prepared_edits, key=lambda item: item["paragraph"], reverse=True
                ):
                    cursor = edit["cursor"]
                    if cursor.getString() != edit["search_text"]:
                        return {
                            "success": False,
                            "error": (
                                "A target range changed after preflight; earlier edits "
                                "may already have been applied"
                            ),
                            "partial": any(
                                item.get("applied", False) for item in prepared_edits
                            ),
                        }
                    cursor.setString(edit["replacement_text"])
                    edit["applied"] = True

            changes = [
                {
                    "edit_index": edit["edit_index"],
                    "location": edit["location"],
                    "style": edit["expected_style"],
                    "before": edit["before"],
                    "after": edit["after"],
                    "status": "preview" if dry_run else "applied",
                }
                for edit in sorted(prepared_edits, key=lambda item: item["edit_index"])
            ]
            return {
                "success": True,
                "dry_run": dry_run,
                "document": {
                    "title": self._document_title(doc),
                    "url": self._document_url(doc),
                    "type": doc_type,
                },
                "count": len(changes),
                "changes": changes,
                "saved": False,
            }
        except Exception as e:
            logger.error(f"Failed to replace document elements: {e}")
            return {"success": False, "error": str(e)}

    def _writer_body_paragraphs(self, doc: Any):
        """Yield searchable top-level Writer paragraphs with search-compatible locations."""
        paragraph_index = 0
        for element in self._enumerate_items(doc.getText()):
            if callable(getattr(element, "getCellNames", None)) and callable(
                getattr(element, "getCellByName", None)
            ):
                continue
            text_value = self._range_string(element)
            if text_value is None:
                continue
            paragraph_index += 1
            yield paragraph_index, element, text_value

    @staticmethod
    def _is_writer_heading(style: Any, outline_level: Any) -> bool:
        try:
            if int(outline_level) > 0:
                return True
        except (TypeError, ValueError):
            pass

        style_name = str(style or "").strip().casefold()
        for prefix in ("heading", "titre", "titulo", "título", "überschrift", "rubrik"):
            if style_name.startswith(prefix):
                suffix = style_name[len(prefix):].strip()
                if suffix.isdigit():
                    return True
        return style_name == "title"

    @staticmethod
    def _uno_character_count(value: str) -> int:
        """Return the Unicode character count used by UNO XTextCursor.goRight."""
        return len(value)

    def _select_writer_substring(
        self, paragraph: Any, offset: int, search_text: str
    ) -> Any:
        """Create and verify a UNO cursor selecting exactly one substring."""
        get_text = getattr(paragraph, "getText", None)
        get_start = getattr(paragraph, "getStart", None)
        if not callable(get_text) or not callable(get_start):
            raise ValueError("paragraph does not expose a UNO text range")
        text = get_text()
        create_cursor = getattr(text, "createTextCursorByRange", None)
        if not callable(create_cursor):
            raise ValueError("paragraph text cannot create a cursor by range")

        cursor = create_cursor(get_start())
        go_right = getattr(cursor, "goRight", None)
        get_string = getattr(cursor, "getString", None)
        set_string = getattr(cursor, "setString", None)
        if not callable(go_right) or not callable(get_string) or not callable(set_string):
            raise ValueError("UNO text cursor cannot select and replace text")

        uno_offset = self._uno_character_count(
            self._range_string(paragraph)[:offset]
        )
        uno_length = self._uno_character_count(search_text)
        if uno_offset > 32767 or uno_length > 32767:
            raise ValueError("target range exceeds UNO cursor movement limits")
        if uno_offset and not go_right(uno_offset, False):
            raise ValueError("could not move the cursor to the target offset")
        if not go_right(uno_length, True):
            raise ValueError("could not select the target text")
        if get_string() != search_text:
            raise ValueError("selected text does not match search_text")
        return cursor
    
    def search_document_elements(
        self,
        query: str,
        document_identifier: Optional[str] = None,
        max_results: int = 100,
    ) -> Dict[str, Any]:
        """Search an already-open document and return matching elements and formatting."""
        if not isinstance(query, str) or not query:
            return {"success": False, "error": "query must be a non-empty string"}
        if (
            isinstance(max_results, bool)
            or not isinstance(max_results, int)
            or max_results < 1
            or max_results > self.MAX_SEARCH_RESULTS
        ):
            return {
                "success": False,
                "error": f"max_results must be an integer from 1 to {self.MAX_SEARCH_RESULTS}",
            }

        doc, error = self._resolve_search_document(document_identifier)
        if error:
            return {"success": False, "error": error}

        try:
            doc_type = self._get_document_type(doc)
        except Exception as e:
            return {"success": False, "error": f"Could not identify document type: {e}"}
        matches: List[Dict[str, Any]] = []
        truncated = False
        extra: Dict[str, Any] = {}
        try:
            if doc_type == "writer":
                truncated = self._search_writer_document(
                    doc, query.casefold(), max_results, matches
                )
            elif doc_type == "calc":
                truncated, cells_scanned = self._search_calc_document(
                    doc, query.casefold(), max_results, matches
                )
                extra["cells_scanned"] = cells_scanned
            elif doc_type in ("impress", "draw"):
                truncated = self._search_draw_document(
                    doc, query.casefold(), max_results, matches
                )
            else:
                return {
                    "success": False,
                    "error": f"Search is not supported for document type '{doc_type}'",
                }

            return {
                "success": True,
                "document": {
                    "title": self._document_title(doc),
                    "url": self._document_url(doc),
                    "type": doc_type,
                },
                "query": query,
                "matches": matches,
                "count": len(matches),
                "truncated": truncated,
                **extra,
            }
        except Exception as e:
            logger.error(f"Failed to search document elements: {e}")
            return {"success": False, "error": str(e)}

    def _resolve_search_document(
        self, document_identifier: Optional[str]
    ) -> tuple[Optional[Any], Optional[str]]:
        if document_identifier is None:
            doc = self.get_active_document()
            if doc is None:
                return None, "No active document is available"
            return doc, None

        if not isinstance(document_identifier, str) or not document_identifier:
            return None, "document_identifier must be a non-empty title or URL"

        candidates = []
        for doc in self._get_open_documents():
            if (
                document_identifier == self._document_url(doc)
                or document_identifier == self._document_title(doc)
            ):
                candidates.append(doc)

        if not candidates:
            return (
                None,
                "No open document matches document_identifier; files are not opened by this tool",
            )
        if len(candidates) > 1:
            return (
                None,
                "document_identifier matches multiple open documents; use an exact URL",
            )
        return candidates[0], None

    def _get_open_documents(self) -> List[Any]:
        """Return loaded document components without opening or changing them."""
        documents = []
        try:
            components = self.desktop.getComponents()
            enumeration = components.createEnumeration()
            while enumeration.hasMoreElements():
                documents.append(enumeration.nextElement())
            return documents
        except Exception:
            pass

        try:
            frames = self.desktop.getFrames()
            for index in range(frames.getCount()):
                frame = frames.getByIndex(index)
                controller = frame.getController()
                if controller:
                    doc = controller.getModel()
                    if doc is not None and doc not in documents:
                        documents.append(doc)
        except Exception:
            pass
        return documents

    @staticmethod
    def _document_url(doc: Any) -> str:
        try:
            return str(doc.getURL()) if callable(getattr(doc, "getURL", None)) else ""
        except Exception:
            return ""

    @staticmethod
    def _document_title(doc: Any) -> str:
        try:
            title = getattr(doc, "Title", "")
            return str(title) if title else ""
        except Exception:
            return ""

    @staticmethod
    def _enumerate_items(container: Any):
        """Yield UNO enumeration or indexed-container elements."""
        try:
            create_enumeration = getattr(container, "createEnumeration", None)
            if callable(create_enumeration):
                enumeration = create_enumeration()
                while enumeration.hasMoreElements():
                    yield enumeration.nextElement()
                return
            get_count = getattr(container, "getCount", None)
            get_by_index = getattr(container, "getByIndex", None)
            if callable(get_count) and callable(get_by_index):
                for index in range(get_count()):
                    yield get_by_index(index)
        except Exception:
            return

    @staticmethod
    def _range_string(text_range: Any) -> Optional[str]:
        try:
            get_string = getattr(text_range, "getString", None)
            if callable(get_string):
                value = get_string()
            else:
                value = getattr(text_range, "String", None)
            return value if isinstance(value, str) else None
        except Exception:
            return None

    @staticmethod
    def _property(obj: Any, name: str) -> Any:
        try:
            return getattr(obj, name)
        except Exception:
            return None

    @staticmethod
    def _json_value(value: Any) -> Any:
        if value is None or isinstance(value, (str, int, float, bool)):
            return value
        try:
            enum_value = getattr(value, "value")
            if isinstance(enum_value, (str, int, float, bool)):
                return enum_value
        except Exception:
            pass
        return str(value)

    def _formatting_metadata(self, obj: Any) -> Dict[str, Any]:
        metadata: Dict[str, Any] = {}
        property_names = {
            "font_name": "CharFontName",
            "font_size": "CharHeight",
            "font_color": "CharColor",
            "underline": "CharUnderline",
            "cell_background": "CellBackColor",
            "fill_color": "FillColor",
            "line_color": "LineColor",
            "line_width": "LineWidth",
            "number_format": "NumberFormat",
            "horizontal_alignment": "HoriJustify",
            "vertical_alignment": "VertJustify",
            "text_wrapped": "IsTextWrapped",
        }
        for output_name, property_name in property_names.items():
            value = self._property(obj, property_name)
            if value is not None:
                metadata[output_name] = self._json_value(value)

        weight = self._property(obj, "CharWeight")
        if weight is not None:
            safe_weight = self._json_value(weight)
            metadata["font_weight"] = safe_weight
            try:
                metadata["bold"] = float(weight) >= 150
            except (TypeError, ValueError):
                metadata["bold"] = "BOLD" in str(weight).upper()

        posture = self._property(obj, "CharPosture")
        if posture is not None:
            safe_posture = self._json_value(posture)
            metadata["font_posture"] = safe_posture
            try:
                metadata["italic"] = int(posture) in (2, 5)
            except (TypeError, ValueError):
                metadata["italic"] = "ITALIC" in str(posture).upper()
        return metadata

    def _text_runs(self, text_element: Any) -> List[Dict[str, Any]]:
        runs = []
        for portion in self._enumerate_items(text_element):
            text = self._range_string(portion)
            if not text:
                continue
            run = {"text": text}
            formatting = self._formatting_metadata(portion)
            if formatting:
                run["formatting"] = formatting
            runs.append(run)
        return runs

    def _search_writer_document(
        self,
        doc: Any,
        query: str,
        max_results: int,
        matches: List[Dict[str, Any]],
    ) -> bool:
        return self._search_writer_text(
            doc.getText(), query, max_results, matches, {"section": "body"}
        )

    def _search_writer_text(
        self,
        text: Any,
        query: str,
        max_results: int,
        matches: List[Dict[str, Any]],
        location: Dict[str, Any],
    ) -> bool:
        paragraph_index = 0
        for element in self._enumerate_items(text):
            get_cell_names = getattr(element, "getCellNames", None)
            get_cell_by_name = getattr(element, "getCellByName", None)
            if callable(get_cell_names) and callable(get_cell_by_name):
                table_name = self._property(element, "Name")
                if not table_name:
                    try:
                        table_name = element.getName()
                    except Exception:
                        table_name = "table"
                for cell_name in get_cell_names():
                    try:
                        cell_text = element.getCellByName(cell_name).getText()
                    except Exception:
                        continue
                    table_location = {
                        "section": "table",
                        "table": str(table_name),
                        "cell": str(cell_name),
                    }
                    if self._search_writer_text(
                        cell_text, query, max_results, matches, table_location
                    ):
                        return True
                continue

            text_value = self._range_string(element)
            if text_value is None:
                continue
            paragraph_index += 1
            if query not in text_value.casefold():
                continue
            if len(matches) >= max_results:
                return True

            formatting = self._formatting_metadata(element)
            paragraph_style = self._property(element, "ParaStyleName")
            outline_level = self._property(element, "OutlineLevel")
            alignment = self._property(element, "ParaAdjust")
            paragraph_formatting = {}
            if paragraph_style is not None:
                paragraph_formatting["style"] = self._json_value(paragraph_style)
            if outline_level is not None:
                paragraph_formatting["outline_level"] = self._json_value(outline_level)
            if alignment is not None:
                paragraph_formatting["alignment"] = self._json_value(alignment)
            if formatting:
                paragraph_formatting["character_defaults"] = formatting

            result_location = dict(location)
            result_location["paragraph"] = paragraph_index
            match = {
                "element_type": "paragraph",
                "text": text_value,
                "location": result_location,
                "formatting": paragraph_formatting,
            }
            runs = self._text_runs(element)
            if runs:
                match["runs"] = runs
            matches.append(match)
        return False

    def _search_calc_document(
        self,
        doc: Any,
        query: str,
        max_results: int,
        matches: List[Dict[str, Any]],
    ) -> tuple[bool, int]:
        sheets = doc.getSheets()
        cells_scanned = 0
        for sheet_index in range(sheets.getCount()):
            sheet = sheets.getByIndex(sheet_index)
            sheet_name = str(sheet.getName())
            cursor = sheet.createCursor()
            cursor.gotoStartOfUsedArea(False)
            cursor.gotoEndOfUsedArea(True)
            address = cursor.getRangeAddress()
            start_column = int(address.StartColumn)
            end_column = int(address.EndColumn)
            start_row = int(address.StartRow)
            end_row = int(address.EndRow)

            for row in range(start_row, end_row + 1):
                for column in range(start_column, end_column + 1):
                    if cells_scanned >= self.MAX_CALC_CELLS_TO_SCAN:
                        return True, cells_scanned
                    cells_scanned += 1
                    cell = sheet.getCellByPosition(column, row)
                    displayed_value = self._range_string(cell)
                    if displayed_value is None:
                        displayed_value = ""
                    try:
                        formula_value = str(cell.getFormula())
                    except Exception:
                        formula_value = ""

                    matched_fields = []
                    if query in displayed_value.casefold():
                        matched_fields.append("displayed_value")
                    if (
                        formula_value.startswith("=")
                        and query in formula_value.casefold()
                    ):
                        matched_fields.append("formula")
                    if not matched_fields:
                        continue
                    if len(matches) >= max_results:
                        return True, cells_scanned

                    cell_address = f"{self._calc_column_name(column)}{row + 1}"
                    formatting = self._formatting_metadata(cell)
                    cell_style = self._property(cell, "CellStyle")
                    if cell_style is not None:
                        formatting["style"] = self._json_value(cell_style)
                    matches.append(
                        {
                            "element_type": "cell",
                            "text": displayed_value,
                            "value": displayed_value,
                            "formula": (
                                formula_value
                                if formula_value.startswith("=")
                                else None
                            ),
                            "matched_fields": matched_fields,
                            "location": {
                                "sheet": sheet_name,
                                "cell": cell_address,
                                "sheet_index": sheet_index + 1,
                            },
                            "formatting": formatting,
                        }
                    )
        return False, cells_scanned

    @staticmethod
    def _calc_column_name(column: int) -> str:
        name = ""
        while column >= 0:
            column, remainder = divmod(column, 26)
            name = chr(65 + remainder) + name
            column -= 1
        return name

    def _search_draw_document(
        self,
        doc: Any,
        query: str,
        max_results: int,
        matches: List[Dict[str, Any]],
    ) -> bool:
        pages = doc.getDrawPages()
        for page_index in range(pages.getCount()):
            page = pages.getByIndex(page_index)
            for shape_index in range(page.getCount()):
                shape = page.getByIndex(shape_index)
                try:
                    shape_type = str(shape.getShapeType())
                except Exception:
                    shape_type = ""
                if shape_type.endswith("GroupShape"):
                    if self._search_shape_group(
                        shape,
                        query,
                        max_results,
                        matches,
                        page_index + 1,
                        f"{shape_index + 1}",
                    ):
                        return True
                    continue
                if self._append_shape_match(
                    shape,
                    query,
                    max_results,
                    matches,
                    page_index + 1,
                    str(shape_index + 1),
                ):
                    return True
        return False

    def _search_shape_group(
        self,
        group: Any,
        query: str,
        max_results: int,
        matches: List[Dict[str, Any]],
        page_number: int,
        shape_path: str,
    ) -> bool:
        for child_index in range(group.getCount()):
            child = group.getByIndex(child_index)
            path = f"{shape_path}.{child_index + 1}"
            try:
                shape_type = str(child.getShapeType())
            except Exception:
                shape_type = ""
            if shape_type.endswith("GroupShape"):
                if self._search_shape_group(
                    child, query, max_results, matches, page_number, path
                ):
                    return True
            elif self._append_shape_match(
                child, query, max_results, matches, page_number, path
            ):
                return True
        return False

    def _append_shape_match(
        self,
        shape: Any,
        query: str,
        max_results: int,
        matches: List[Dict[str, Any]],
        page_number: int,
        shape_path: str,
    ) -> bool:
        text_value = self._range_string(shape)
        if not text_value or query not in text_value.casefold():
            return False
        if len(matches) >= max_results:
            return True

        try:
            shape_type = str(shape.getShapeType())
        except Exception:
            shape_type = "unknown"
        shape_name = self._property(shape, "Name")
        result = {
            "element_type": "shape",
            "text": text_value,
            "location": {
                "page": page_number,
                "shape": str(shape_name) if shape_name else shape_path,
                "shape_index": shape_path,
            },
            "formatting": self._formatting_metadata(shape),
            "shape_type": shape_type,
        }
        runs = self._text_runs(shape)
        if runs:
            result["runs"] = runs
        matches.append(result)
        return False

    def _get_document_type(self, doc: Any) -> str:
        """Determine document type"""
        if doc.supportsService("com.sun.star.text.TextDocument"):
            return "writer"
        elif doc.supportsService("com.sun.star.sheet.SpreadsheetDocument"):
            return "calc"
        elif doc.supportsService("com.sun.star.presentation.PresentationDocument"):
            return "impress"
        elif doc.supportsService("com.sun.star.drawing.DrawingDocument"):
            return "draw"
        else:
            return "unknown"
    
    def _has_selection(self, doc: Any) -> bool:
        """Check if document has selected content"""
        try:
            if hasattr(doc, 'getCurrentController'):
                controller = doc.getCurrentController()
                if hasattr(controller, 'getSelection'):
                    selection = controller.getSelection()
                    return selection.getCount() > 0
        except:
            pass
        return False
