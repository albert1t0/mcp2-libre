"""Exercise live heading search and guarded replacement against real LibreOffice UNO.

Run with the Python interpreter that can import LibreOffice's ``uno`` module:
    /usr/bin/python3 tests/integration_live_tools_uno.py

The script starts a separate headless LibreOffice process with a temporary user
profile, creates an unsaved Writer document, and disposes it without saving.
"""

import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "plugin/pythonpath"))

try:
    import uno
    from uno_bridge import UNOBridge
except ImportError as error:
    raise SystemExit(
        "LibreOffice UNO Python modules are unavailable. Run this script with "
        "the system Python that provides the 'uno' module."
    ) from error


def _libreoffice_binary():
    configured_binary = os.environ.get("LIBREOFFICE_BIN")
    if configured_binary:
        resolved_binary = shutil.which(configured_binary)
        if resolved_binary:
            return resolved_binary
        if Path(configured_binary).is_file():
            return configured_binary
        raise SystemExit(f"LIBREOFFICE_BIN does not identify an executable: {configured_binary}")

    binary = shutil.which("libreoffice") or shutil.which("soffice")
    if not binary:
        raise SystemExit("LibreOffice was not found on PATH; set LIBREOFFICE_BIN to its executable")
    return binary


def _reserve_port():
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        return listener.getsockname()[1]


def _connect_to_office(process, port, timeout=30):
    local_context = uno.getComponentContext()
    resolver = local_context.ServiceManager.createInstanceWithContext(
        "com.sun.star.bridge.UnoUrlResolver", local_context
    )
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(
                f"isolated LibreOffice exited with code {process.returncode}"
            )
        try:
            return resolver.resolve(
                f"uno:socket,host=127.0.0.1,port={port};urp;StarOffice.ComponentContext"
            )
        except Exception:
            time.sleep(0.25)
    raise TimeoutError("isolated LibreOffice UNO listener did not become ready")


def _make_test_document(desktop):
    document = desktop.loadComponentFromURL(
        "private:factory/swriter", "_blank", 0, ()
    )
    text = document.getText()
    cursor = text.createTextCursor()
    paragraph_break = uno.getConstantByName(
        "com.sun.star.text.ControlCharacter.PARAGRAPH_BREAK"
    )
    paragraphs = [
        (None, "Integration test preamble"),
        ("Heading 1", "🎯 Integration heading one"),
        ("Heading 2", "Integration heading 🚀 two"),
    ]

    for index, (style, value) in enumerate(paragraphs):
        cursor.gotoEnd(False)
        if index:
            text.insertControlCharacter(cursor, paragraph_break, False)
            cursor.gotoEnd(False)
        if style:
            cursor.ParaStyleName = style
        text.insertString(cursor, value, False)
        cursor.gotoEnd(False)

    return document


def run_integration_test():
    libreoffice_binary = _libreoffice_binary()
    version = subprocess.run(
        [libreoffice_binary, "--version"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()

    with tempfile.TemporaryDirectory(prefix="mcp-libre-live-tools-") as profile:
        port = _reserve_port()
        process = subprocess.Popen(
            [
                libreoffice_binary,
                "--headless",
                "--nologo",
                "--nodefault",
                "--norestore",
                "--nofirststartwizard",
                f"-env:UserInstallation={Path(profile).as_uri()}",
                f"--accept=socket,host=127.0.0.1,port={port};urp;StarOffice.ServiceManager",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        document = None
        desktop = None
        try:
            remote_context = _connect_to_office(process, port)
            desktop = remote_context.ServiceManager.createInstanceWithContext(
                "com.sun.star.frame.Desktop", remote_context
            )
            document = _make_test_document(desktop)

            bridge = UNOBridge.__new__(UNOBridge)
            bridge.desktop = desktop
            bridge.get_active_document = lambda: document

            headings = bridge.search_document_headings()
            assert headings["success"] is True, headings
            assert [heading["text"] for heading in headings["matches"]] == [
                "🎯 Integration heading one",
                "Integration heading 🚀 two",
            ], headings
            assert [
                heading["location"]["paragraph"]
                for heading in headings["matches"]
            ] == [2, 3]

            edits = [
                {
                    "location": heading["location"],
                    "expected_text": heading["text"],
                    "expected_style": heading["formatting"]["style"],
                    "search_text": icon,
                    "replacement_text": "",
                }
                for heading, icon in zip(
                    headings["matches"], ("🎯 ", "🚀 ")
                )
            ]

            text = document.getText()
            original_text = text.getString()
            preview = bridge.replace_document_elements(edits)
            assert preview["success"] is True and preview["dry_run"] is True, preview
            assert text.getString() == original_text, "dry-run changed document text"

            applied = bridge.replace_document_elements(edits, dry_run=False)
            assert applied["success"] is True and applied["count"] == 2, applied
            assert applied["saved"] is False
            updated_headings = bridge.search_document_headings()
            assert [heading["text"] for heading in updated_headings["matches"]] == [
                "Integration heading one",
                "Integration heading two",
            ], updated_headings

            after_apply = text.getString()
            stale_edit = dict(edits[0], expected_text="🎯 Stale heading")
            stale_result = bridge.replace_document_elements(
                [stale_edit], dry_run=False
            )
            assert stale_result["success"] is False, stale_result
            assert text.getString() == after_apply, "stale edit changed document text"
            assert document.isModified(), "integration document was unexpectedly saved"

            return {
                "result": "passed",
                "libreoffice": version,
                "isolated_profile": True,
                "headings_found": len(headings["matches"]),
                "dry_run_preserved_text": True,
                "replacements_applied": applied["count"],
                "stale_batch_rejected_without_mutation": True,
                "document_saved": False,
            }
        finally:
            if document is not None:
                try:
                    document.dispose()
                except Exception:
                    pass
            if desktop is not None:
                try:
                    desktop.terminate()
                except Exception:
                    pass
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)


if __name__ == "__main__":
    print(json.dumps(run_integration_test(), ensure_ascii=False, indent=2))
